"""Winny 2 (b7.1) 観測専用クライアント。

PROTOCOL.md の接続シーケンスを実装する:
シード平文前置 → 0x61 マーカー → ハロー → 再鍵 → タイプ1/2/3 送信、
受信側はフレーム単位で復号し、タイプ3/4 をパースして記録する。
コンテンツ転送系 (タイプ11/21 等) は一切送信しない。自ノードは
Port0 (ポート未開放) として申告する: タイプ2 フラグ[1]=1 が
その申告であり、タイプ3 のポート欄には実クライアント同様に
受付ポート設定値 (m_port_accept_ 相当) を書く (0670 / §6.2)。
待ち受けは一切しないので到達可能性はない。

mock_peer.py からも使えるよう、送受信ストリーム基盤を
WinnyEndpoint として切り出してある。
"""

import os
import socket
import struct
import time

from winny_codec import (
    RC4,
    build_hello_payload,
    build_type3,
    parse_type3,
    parse_type4,
    rekey_stream_key,
    seed_stream_key,
    verify_hello_payload,
)

MAX_FRAME = 0x20000  # 0780 が mf_CHost_0150 に渡す上限
# m_port_accept_ 相当の申告値。実クライアントでは ini の AcceptPort
# (未設定時は 1024..32766 のランダム) で、0 になることはない
# (CMainControl.cpp の設定読み込み)。当実装では代表値として
# Winny の著名な既定ポート 7743 を固定で使う (§6.2)。
DEFAULT_ACCEPT_PORT = 7743
DISCONNECT_TYPES = {t: bytes([t]).decode("ascii") for t in (0x21, 0x22, 0x23, 0x25)}


class ProtocolError(Exception):
    pass


def disp(b: bytes) -> str:
    """表示用にバイト列を文字列化 (Shift_JIS 想定、失敗時は repr)。"""
    try:
        return b.decode("cp932")
    except UnicodeDecodeError:
        return repr(b)


class WinnyEndpoint:
    """1接続分の送受信ストリーム状態 (CHost 相当) とハンドシェイク送信。"""

    def __init__(self, sock: socket.socket, *, seed: bytes | None = None,
                 log=print):
        self.sock = sock
        self.log = log
        self.seed = bytes(seed) if seed is not None else os.urandom(4)
        assert len(self.seed) == 4
        self._send_rc4 = RC4(seed_stream_key(self.seed))
        self._send_started = False
        self._recv_buf = bytearray()
        self._recv_rc4: RC4 | None = None
        self.peer_seed: bytes | None = None
        self.peer_hello_version: int | None = None
        self.closed = False
        # 復号済み受信バイト列 (フレーム単位 + raw継続分) を逐次受け取る
        # フック。None なら何もしない (通常の観測/モック動作に影響なし)。
        self.frame_sink = None
        # 直近に拒否した異常フレーム長 (ProtocolError 発生時に設定)
        self.last_bad_length: int | None = None

    # ---------------------------------------------------------- 送信側

    def send_frame(self, payload: bytes) -> None:
        frame = struct.pack("<i", len(payload)) + payload
        out = self._send_rc4.crypt(frame)
        if not self._send_started:
            # 最初の送信時のみ平文前置: ランダム2バイト + 自シード4バイト
            # (CHost::mf_CHost_0160)
            prefix = os.urandom(2) + self.seed
            self.sock.sendall(prefix + out)
            self._send_started = True
        else:
            self.sock.sendall(out)

    def rekey_send(self) -> None:
        self._send_rc4 = RC4(rekey_stream_key(self.seed))

    def send_handshake(self, *, line_speed: float, type2_flags: bytes,
                       type3_payload: bytes) -> None:
        """0670 の列: マーカー → ハロー → 再鍵 → タイプ1 → タイプ2 → タイプ3。"""
        self.send_frame(b"\x61")
        self.log("send: marker 0x61")
        self.send_frame(build_hello_payload())
        self.log("send: hello (type 0, version 12710)")
        self.rekey_send()
        self.log("send: rekeyed send stream (seed[1..3] ^ 0x39)")
        self.send_frame(b"\x01" + struct.pack("<f", line_speed))
        self.log("send: type 1 line speed %r" % (line_speed,))
        assert len(type2_flags) == 4
        self.send_frame(b"\x02" + bytes(type2_flags))
        self.log("send: type 2 flags %s" % (list(type2_flags),))
        self.send_frame(type3_payload)
        self.log("send: type 3 self node info")

    # ---------------------------------------------------------- 受信側

    def _ensure_recv_key(self) -> bool:
        if self._recv_rc4 is not None:
            return True
        if len(self._recv_buf) < 6:
            return False
        # 先頭2バイトは読み捨て、[2:6) が相手シード (0360)
        self.peer_seed = bytes(self._recv_buf[2:6])
        del self._recv_buf[:6]
        self._recv_rc4 = RC4(seed_stream_key(self.peer_seed))
        self.log("recv: peer seed %s" % self.peer_seed.hex())
        return True

    def feed(self, chunk: bytes) -> None:
        self._recv_buf += chunk

    def next_frame(self) -> bytes | None:
        """復号済みペイロードを1フレーム分返す。未完成なら None。

        0120 (試行復号で長さ判定) → 0150 (本復号で切り出し) の意味論を再現し、
        ハロー境界での再鍵が後続フレームに正しく効くようにしている。
        """
        if not self._ensure_recv_key():
            return None
        if len(self._recv_buf) < 4:
            return None
        peek = self._recv_rc4.clone().crypt(bytes(self._recv_buf[:4]))
        (length,) = struct.unpack("<i", peek)
        if length < 0 or length >= MAX_FRAME:
            self.last_bad_length = length
            raise ProtocolError("invalid frame length %d" % length)
        if len(self._recv_buf) < 4 + length:
            return None
        raw = bytes(self._recv_buf[:4 + length])
        del self._recv_buf[:4 + length]
        plain = self._recv_rc4.crypt(raw)
        if self.frame_sink is not None:
            self.frame_sink(plain)
        return plain[4:]

    def rekey_recv(self) -> None:
        self._recv_rc4 = RC4(rekey_stream_key(self.peer_seed))

    def read_raw_decrypted(self, timeout: float = 0.5) -> bytes | None:
        """raw継続モード用: フレーム解釈を一切せず、受信バイト列を
        現在の受信ストリーム鍵のまま復号して返す。

        next_frame() が ProtocolError を投げた位置から呼ぶ前提
        (試行復号は clone 経由なので鍵位置は異常フレームの先頭に
        残っている)。復号したバイトは frame_sink にも渡す。
        EOF なら None、タイムアウトで新規データが無ければ b""。
        """
        if not self._ensure_recv_key():
            if not self.read_once(timeout=timeout):
                return None
            if not self._ensure_recv_key():
                return b""
        out = bytearray()
        if self._recv_buf:
            out += self._recv_rc4.crypt(bytes(self._recv_buf))
            self._recv_buf.clear()
        if not out:
            if not self.read_once(timeout=timeout):
                return None
            if self._recv_buf:
                out += self._recv_rc4.crypt(bytes(self._recv_buf))
                self._recv_buf.clear()
        data = bytes(out)
        if data and self.frame_sink is not None:
            self.frame_sink(data)
        return data

    def read_once(self, timeout: float = 0.5) -> bool:
        """ソケットから1回読み、バッファに足す。EOF なら False。"""
        self.sock.settimeout(timeout)
        try:
            chunk = self.sock.recv(65536)
        except socket.timeout:
            return True
        except OSError:
            self.closed = True
            return False
        if not chunk:
            self.closed = True
            return False
        self.feed(chunk)
        return True

    def close(self) -> None:
        self.closed = True
        try:
            self.sock.close()
        except OSError:
            pass


class WinnyConnection(WinnyEndpoint):
    """観測専用クライアント (発信側)。Port0 として申告する。"""

    def __init__(self, host: str, port: int, *,
                 self_ip: str = "127.0.0.1",
                 accept_port: int = DEFAULT_ACCEPT_PORT,
                 line_speed: float = 100.0,
                 ddns: bytes = b"",
                 clusters: tuple[bytes, bytes, bytes] = (b"", b"", b""),
                 seed: bytes | None = None, log=print):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        super().__init__(sock, seed=seed, log=log)
        self.host = host
        self.port = port
        self.self_ip = self_ip
        self.accept_port = accept_port
        self.line_speed = line_speed
        self.ddns = ddns
        self.clusters = clusters
        self.peer_node: dict | None = None
        self.nodes: list[dict] = []
        # 接続方向判定 (0790) 用に相手の申告を保持する
        self.peer_line_speed: float | None = None   # タイプ1 の生値
        self.peer_int_line_speed: int | None = None  # SetLineSpeed 後の int
        self.peer_port0: bool | None = None          # タイプ2 [1] 由来

    def connect(self) -> None:
        self.sock.connect((self.host, self.port))
        self.log("connected to %s:%d" % (self.host, self.port))
        type3 = build_type3(
            socket.inet_aton(self.self_ip), self.accept_port,
            self.ddns, self.clusters)
        # タイプ2: [0]=検索リンク, [1]=Port0フラグ, [2]=未確定フラグ, [3]=BBSフラグ
        self.send_handshake(line_speed=self.line_speed,
                            type2_flags=bytes([0, 1, 0, 0]),
                            type3_payload=type3)

    def peer_is_up_connection(self) -> bool:
        """相手が「上り接続」かどうか (mf_CMainControl_0790 の判定)。

        - 相手が Port0 (タイプ2 [1]) なら無条件に下り接続扱い。
        - そうでなければ速度比 (相手 int 速度 / 自 int 速度) で判定:
          > 1.5 なら上り、< 2/3 なら下り、帯域内は現状維持。
          新規接続の初期値は「下りでない」 (CHost 初期値) なので
          帯域内・速度不明時は上りとして扱う。
        """
        if self.peer_port0:
            return False
        if self.peer_int_line_speed is None:
            return True
        own = int(self.line_speed)
        if own <= 0:
            return True
        ratio = self.peer_int_line_speed / own
        if ratio > 1.5:
            return True
        if ratio < 2.0 / 3.0:
            return False
        return True

    # ------------------------------------------------------ ディスパッチ

    def process_frame(self, payload: bytes) -> bool:
        """1フレーム処理する。接続を閉じるべき場合は False。"""
        if len(payload) == 0:
            self.log("recv: empty frame (ignored)")
            return True
        t = payload[0]
        data = payload[1:]
        if t == 0:
            version = verify_hello_payload(payload)
            if version is None:
                self.log("recv: hello verification FAILED -> disconnect")
                return False
            self.peer_hello_version = version
            self.log("recv: hello ok, peer version %d" % version)
            self.rekey_recv()
            self.log("recv: rekeyed recv stream (peer seed[1..3] ^ 0x39)")
            return True
        if t == 1:
            if len(data) >= 4:
                (speed,) = struct.unpack_from("<f", data, 0)
                self.peer_line_speed = speed
                # 0780 は SetLineSpeed((int)float) で int 化して保持する
                self.peer_int_line_speed = int(speed)
                self.log("recv: type 1 line speed %r" % (speed,))
            else:
                self.log("recv: type 1 (short, len=%d)" % len(payload))
            return True
        if t == 2:
            if len(data) >= 2:
                # data[1] != 0 が相手の Port0 フラグ (0790 の判定材料)
                self.peer_port0 = data[1] != 0
            self.log("recv: type 2 flags %s" % (list(data[:4]),))
            return True
        if t == 3:
            try:
                info = parse_type3(data)
            except ValueError as e:
                self.log("recv: type 3 parse error: %s" % e)
                return True
            self.peer_node = info
            if self.peer_port0 is None:
                self.peer_port0 = info["port"] == 0
            self.log("recv: type 3 peer node ip=%s port=%d ddns=%r "
                     "clusters=%s" % (info["ip"], info["port"],
                                      disp(info["ddns"]),
                                      [disp(c) for c in info["clusters"]]))
            return True
        if t == 4:
            try:
                info = parse_type4(data)
            except ValueError as e:
                self.log("recv: type 4 parse error: %s" % e)
                return True
            self.nodes.append(info)
            self.log("recv: type 4 node ip=%s port=%d bbs_port=%d bbs=%s "
                     "speed=%d clusters=%s"
                     % (info["ip"], info["port"], info["bbs_port"],
                        info["is_bbs"], info["line_speed"],
                        [disp(c) for c in info["clusters"]]))
            return True
        if t == 5:
            if len(data) >= 4:
                (bbs_port,) = struct.unpack_from("<i", data, 0)
                self.log("recv: type 5 bbs port %d" % bbs_port)
            else:
                self.log("recv: type 5 (short, len=%d)" % len(payload))
            return True
        if t == 0x20:
            self.log("recv: ACK (' ')")
            return True
        if t in DISCONNECT_TYPES:
            self.log("recv: disconnect notice %s -> close"
                     % DISCONNECT_TYPES[t])
            return False
        if 0x60 <= t <= 0x63:
            self.log("recv: marker 0x%02x (ignored)" % t)
            return True
        self.log("recv: type %d len=%d (recorded & skipped)"
                 % (t, len(payload)))
        return True

    def run(self, duration: float = 5.0) -> None:
        """duration 秒間、受信とディスパッチを続ける。"""
        deadline = time.monotonic() + duration
        while not self.closed and time.monotonic() < deadline:
            try:
                payload = self.next_frame()
            except ProtocolError as e:
                self.log("protocol error: %s -> disconnect" % e)
                break
            if payload is None:
                if not self.read_once(timeout=0.5):
                    self.log("connection closed by peer")
                    break
                continue
            if not self.process_frame(payload):
                break
        self.close()


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Winny observing client (proto)")
    p.add_argument("host")
    p.add_argument("port", type=int)
    p.add_argument("--duration", type=float, default=5.0)
    args = p.parse_args()
    conn = WinnyConnection(args.host, args.port,
                           log=lambda m: print("[client] " + m))
    conn.connect()
    conn.run(args.duration)
    print("[client] peer node: %r" % (conn.peer_node,))
    print("[client] introduced nodes: %d" % len(conn.nodes))


if __name__ == "__main__":
    main()
