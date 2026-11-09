"""仕様どおり応答するローカルモックピア (着信側)。

実ネットワークなしで winny_client.py 全体を検証するために、
CMainControl::mf_CMainControl_0290 (accept) → 0670 と同じ列
(マーカー → ハロー → 再鍵 → タイプ1/2/3) を送り、クライアントの
ハローを検証して受信を再鍵し、タイプ3 を受けたらタイプ4 で
ダミーノードを紹介する。

使い方 (単体デモ):
    .venv/bin/python mock_peer.py [port]
"""

import socket
import struct
import time

from winny_client import ProtocolError, WinnyEndpoint, disp
from winny_codec import (
    RC4,
    build_type3,
    build_type4,
    parse_type3,
    verify_hello_payload,
)

# 紹介するダミーノード (TEST-NET アドレスを使用)
DEFAULT_INTRO_NODES = [
    # (ip, port, bbs_port, is_bbs, line_speed, clusters)
    ("203.0.113.10", 7743, 0, False, 512, (b"anime", b"2026", b"")),
    ("198.51.100.23", 8080, 0, False, 1024, (b"music", b"", b"")),
    ("192.0.2.55", 7743, 0, False, 2048, (b"", b"", b"")),
]

# 遅延紹介するダミーノード (実クライアントの周期ワーク駆動の紹介を再現)
DEFAULT_DELAYED_INTRO_NODES = [
    ("203.0.113.77", 7743, 0, False, 768, (b"late", b"", b"")),
    ("198.51.100.99", 7743, 0, False, 256, (b"", b"", b"")),
]


def build_mock_key_query() -> bytes:
    """キー付きクエリ (タイプ13) のダミー。crawl.parse_query_type13 で
    パースできる形式で、キーヘッダ1件 (ファイル名は §5.2 難読化済み)
    を同梱する。実ノードが空クエリ応答を受けた後に流してくる
    キー情報の再現用。"""
    name_plain = b"mock-key-file.zip"
    total = sum(name_plain) & 0xFFFF
    name_field = (struct.pack("<H", total)
                  + RC4(bytes([total & 0xFF])).crypt(name_plain))
    kh = bytearray()
    kh += socket.inet_aton("203.0.113.7")
    kh += struct.pack("<H", 7743)
    kh += socket.inet_aton("0.0.0.0")
    kh += struct.pack("<H", 0)
    kh += struct.pack("<I", 424242)          # サイズ
    kh += bytes(range(16, 32))               # ハッシュ
    kh.append(len(name_plain))
    kh += name_field
    kh += b"MOCKPOSTER1"                     # ID1 (11バイト)
    kh.append(3)
    kh += b"ID2"
    kh += struct.pack("<H", 7)               # 値1
    kh += struct.pack("<i", 5)               # 参照カウント
    kh += struct.pack("<i", 1700000000)      # time_t
    kh += b"\x00\x00"                        # フラグ
    q = bytearray()
    q.append(13)
    q += bytes([0, 1, 0, 0])                 # unk02=0, unk01=1, unk03=0, BBS=0
    q += struct.pack("<i", 777)
    q.append(4)
    q += b"mock"
    q += b"MOCKSEARCH1"                      # 検索者ID (11バイト)
    q.append(1)                              # 経路1件
    q += socket.inet_aton("192.168.0.2")
    q += struct.pack("<H", 7743)
    q += struct.pack("<H", 1)                # キーヘッダ1件
    q += kh
    return bytes(q)


class MockPeer:
    def __init__(self, host: str = "127.0.0.1", port: int = 0, *,
                 line_speed: float = 1000.0,
                 intro_nodes=DEFAULT_INTRO_NODES,
                 intro_delay_nodes=None,
                 intro_delay: float = 5.0,
                 send_bad_frame: bool = False,
                 bad_frame_length: int = 0x308A9,
                 bad_frame_delay: float = 1.0,
                 raw_after_bad: bytes = b"",
                 raw_after_bad_delay: float = 1.0,
                 type10_after: float | None = None,
                 require_query_response: bool = False,
                 query_grace: float = 5.0,
                 reply_query_with_keys: bool = False,
                 query_reply_delay: float = 0.3,
                 seed: bytes | None = None,
                 log=print):
        self.host = host
        self.line_speed = line_speed
        self.intro_nodes = intro_nodes
        # 遅延紹介 (実クライアントではノード紹介は周期ワーク駆動のため、
        # ハンドシェイク直後の一括紹介だけでは再現できない)。
        # intro_delay_nodes を渡した場合のみ、タイプ3 受信から
        # intro_delay 秒後に追加のタイプ4 を送る。
        self.intro_delay_nodes = intro_delay_nodes
        self.intro_delay = intro_delay
        # 不正フレーム注入 (実地で観測された「ハンドシェイク後に
        # 異常な長さのフレームが届く」事象の再現)。send_bad_frame が
        # 真の場合、紹介送信から bad_frame_delay 秒後に、上限超の
        # 長さプレフィクスを持つ生バイト列を送信ストリームへ直接
        # 流し込む。raw_after_bad を渡すと、その raw_after_bad_delay
        # 秒後にさらに生バイト列 (フレーム解釈不能な継続データ) を
        # 流し、クローラの raw継続モードを検証できる。
        self.send_bad_frame = send_bad_frame
        self.bad_frame_length = bad_frame_length
        self.bad_frame_delay = bad_frame_delay
        self.raw_after_bad = raw_after_bad
        self.raw_after_bad_delay = raw_after_bad_delay
        # 実ノード模倣 (実地2回目で観測された挙動): ハンドシェイク後に
        # タイプ10 を送り、タイプ13 の応答が返る間だけリンクを維持し、
        # 応答がなければ切断する。type10_after が None なら無効。
        # reply_query_with_keys が真なら、妥当な応答を受けた後に
        # キー付きクエリを1つ流し、相手のキー収集処理を検証できる。
        self.type10_after = type10_after
        self.require_query_response = require_query_response
        self.query_grace = query_grace
        self.reply_query_with_keys = reply_query_with_keys
        self.query_reply_delay = query_reply_delay
        self.seed = seed
        self.log = log
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(1)
        self.port = self.server.getsockname()[1]
        # テスト検証用に受信内容を記録する
        self.received: dict = {
            "marker": False,
            "hello_version": None,
            "type1": None,
            "type2": None,
            "type3": None,
        }
        self.intro_sent = False
        self.delayed_intro_sent = False
        self._delayed_deadline: float | None = None
        self.bad_frame_sent = False
        self.raw_after_bad_sent = False
        self._bad_deadline: float | None = None
        self._raw_deadline: float | None = None
        # 実ノード模倣の状態・検証用記録
        self.frames_received: list = []     # frame_sink 経由の全フレーム
        self.type10_sent_at: float | None = None
        self.type10_received_count = 0      # 相手からのタイプ10の件数
        self.query_response: bytes | None = None   # 受けたタイプ13応答
        self.query_response_valid = False
        self.pruned_no_query = False        # 応答なしで切断したら真
        self.query_reply_sent = False
        self._type10_deadline: float | None = None
        self._query_reply_deadline: float | None = None

    def close(self) -> None:
        try:
            self.server.close()
        except OSError:
            pass

    def serve_once(self, timeout: float = 10.0) -> None:
        """1接続だけ受けて処理する (テストからはスレッドで呼ぶ)。"""
        self.server.settimeout(timeout)
        conn, addr = self.server.accept()
        self.log("accepted connection from %s:%d" % addr)
        ep = WinnyEndpoint(conn, seed=self.seed, log=self.log)
        ep.frame_sink = self.frames_received.append
        try:
            self._handle(ep, timeout)
        finally:
            ep.close()

    def _handle(self, ep: WinnyEndpoint, timeout: float) -> None:
        type3 = build_type3(socket.inet_aton(self.host), self.port,
                            b"mock.local", (b"mock", b"test", b""))
        ep.send_handshake(line_speed=self.line_speed,
                          type2_flags=bytes([0, 0, 0, 0]),
                          type3_payload=type3)
        deadline = time.monotonic() + timeout
        while not ep.closed and time.monotonic() < deadline:
            if (self._delayed_deadline is not None
                    and time.monotonic() >= self._delayed_deadline):
                self._delayed_deadline = None
                self._send_delayed_introductions(ep)
            if (self._bad_deadline is not None
                    and time.monotonic() >= self._bad_deadline):
                self._bad_deadline = None
                self._send_bad_frame(ep)
            if (self._raw_deadline is not None
                    and time.monotonic() >= self._raw_deadline):
                self._raw_deadline = None
                self._send_raw_after_bad(ep)
            if (self._type10_deadline is not None
                    and time.monotonic() >= self._type10_deadline):
                self._type10_deadline = None
                ep.send_frame(b"\x0a")
                self.type10_sent_at = time.monotonic()
                self.log("send: type 10 (real-node mimic)")
            if (self._query_reply_deadline is not None
                    and time.monotonic() >= self._query_reply_deadline):
                self._query_reply_deadline = None
                ep.send_frame(build_mock_key_query())
                self.query_reply_sent = True
                self.log("send: type 13 query with 1 dummy key")
            if (self.require_query_response
                    and self.type10_sent_at is not None
                    and self.query_response is None
                    and time.monotonic()
                    > self.type10_sent_at + self.query_grace):
                self.pruned_no_query = True
                self.log("no type 13 response within grace -> disconnect "
                         "(real-node mimic)")
                break
            try:
                payload = ep.next_frame()
            except ProtocolError as e:
                self.log("protocol error: %s" % e)
                break
            if payload is None:
                if not ep.read_once(timeout=0.5):
                    self.log("client closed connection")
                    break
                continue
            if not self._dispatch(ep, payload):
                break

    def _dispatch(self, ep: WinnyEndpoint, payload: bytes) -> bool:
        if len(payload) == 0:
            return True
        t = payload[0]
        data = payload[1:]
        if t == 0x61:
            self.received["marker"] = True
            self.log("recv: marker 0x61")
            return True
        if t == 0:
            version = verify_hello_payload(payload)
            if version is None:
                self.log("recv: hello verification FAILED -> disconnect")
                return False
            self.received["hello_version"] = version
            self.log("recv: hello ok, client version %d" % version)
            ep.rekey_recv()
            self.log("recv: rekeyed recv stream")
            return True
        if t == 1:
            if len(data) >= 4:
                (speed,) = struct.unpack_from("<f", data, 0)
                self.received["type1"] = speed
                self.log("recv: type 1 line speed %r" % (speed,))
            return True
        if t == 2:
            self.received["type2"] = list(data[:4])
            self.log("recv: type 2 flags %s" % (list(data[:4]),))
            return True
        if t == 3:
            info = parse_type3(data)
            self.received["type3"] = info
            self.log("recv: type 3 client node ip=%s port=%d ddns=%r "
                     "clusters=%s" % (info["ip"], info["port"],
                                      disp(info["ddns"]),
                                      [disp(c) for c in info["clusters"]]))
            self._send_introductions(ep)
            if self.type10_after is not None:
                self._type10_deadline = (time.monotonic()
                                         + self.type10_after)
                self.log("send: type 10 scheduled in %.1fs"
                         % self.type10_after)
            return True
        if t == 10:
            self.type10_received_count += 1
            self.log("recv: type 10 (#%d)" % self.type10_received_count)
            return True
        if t == 13:
            self.query_response = payload
            self.query_response_valid = self._validate_query(payload)
            self.log("recv: type 13 query response (len=%d, valid=%s)"
                     % (len(payload), self.query_response_valid))
            if (self.query_response_valid and self.reply_query_with_keys
                    and not self.query_reply_sent):
                self._query_reply_deadline = (time.monotonic()
                                              + self.query_reply_delay)
            return True
        self.log("recv: type %d len=%d (ignored)" % (t, len(payload)))
        return True

    @staticmethod
    def _validate_query(payload: bytes) -> bool:
        """受けたタイプ13応答の妥当性検証。crawl のパーサが使えれば
        それで検証し、使えなければ最低限の構造チェックで代替する。"""
        try:
            from crawl import parse_query_type13
            q = parse_query_type13(payload)
            return (q["flags"]["with_keys"] and q["search"] == ""
                    and len(q["keys"]) == 0 and q["trailing_bytes"] == 0)
        except Exception:
            return len(payload) >= 24 and payload[0] == 13

    def _send_introductions(self, ep: WinnyEndpoint) -> None:
        for ip, port, bbs_port, is_bbs, speed, clusters in self.intro_nodes:
            ep.send_frame(build_type4(socket.inet_aton(ip), port, bbs_port,
                                      is_bbs, speed, clusters))
            self.log("send: type 4 node %s:%d" % (ip, port))
        # クライアントの「その他タイプは記録して読み飛ばす」経路の検証用に
        # タイプ31 (用途未確定、実クライアントでも送られることがある) を1つ送る
        ep.send_frame(b"\x1f")
        self.log("send: type 31 (probe for skip path)")
        self.intro_sent = True
        if self.intro_delay_nodes is not None:
            self._delayed_deadline = time.monotonic() + self.intro_delay
            self.log("send: delayed introductions scheduled in %.1fs"
                     % self.intro_delay)
        if self.send_bad_frame:
            self._bad_deadline = time.monotonic() + self.bad_frame_delay
            self.log("send: bad frame scheduled in %.1fs"
                     % self.bad_frame_delay)

    def _send_bad_frame(self, ep: WinnyEndpoint) -> None:
        # フレーミングを経由せず、送信ストリームへ生の暗号化バイトを
        # 流す。先頭4バイトが異常な長さプレフィクスになる。
        body = struct.pack("<i", self.bad_frame_length) + b"BADFRAMEBODY" * 4
        ep.sock.sendall(ep._send_rc4.crypt(body))
        self.log("send: BAD FRAME (declared length %d, %d bytes on wire)"
                 % (self.bad_frame_length, len(body)))
        self.bad_frame_sent = True
        if self.raw_after_bad:
            self._raw_deadline = (time.monotonic()
                                  + self.raw_after_bad_delay)
            self.log("send: raw continuation bytes scheduled in %.1fs"
                     % self.raw_after_bad_delay)

    def _send_raw_after_bad(self, ep: WinnyEndpoint) -> None:
        ep.sock.sendall(ep._send_rc4.crypt(self.raw_after_bad))
        self.log("send: raw bytes after bad frame (%d bytes)"
                 % len(self.raw_after_bad))
        self.raw_after_bad_sent = True

    def _send_delayed_introductions(self, ep: WinnyEndpoint) -> None:
        for ip, port, bbs_port, is_bbs, speed, clusters in \
                (self.intro_delay_nodes or []):
            ep.send_frame(build_type4(socket.inet_aton(ip), port, bbs_port,
                                      is_bbs, speed, clusters))
            self.log("send: type 4 node %s:%d (delayed)" % (ip, port))
        self.delayed_intro_sent = True


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Winny mock peer (proto)")
    p.add_argument("port", type=int, nargs="?", default=7743)
    p.add_argument("--timeout", type=float, default=30.0)
    args = p.parse_args()
    peer = MockPeer(port=args.port, log=lambda m: print("[mock] " + m))
    print("[mock] listening on 127.0.0.1:%d" % peer.port)
    try:
        peer.serve_once(timeout=args.timeout)
    finally:
        peer.close()


if __name__ == "__main__":
    main()
