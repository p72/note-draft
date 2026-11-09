# -*- coding: utf-8 -*-
"""Winny 長時間接続クローラ (フェーズ3)。

候補ノードからハンドシェイク成功ノード (エントリ) を探して長時間
(デフォルト10分) 接続を維持し、届くフレームをすべて
「経過秒・タイプ・長さ」で記録する。タイプ4 (ノード紹介) は
重複を除いて蓄積し、タイプ13 (クエリ) は PROTOCOL.md §6 の
CKeyHeader 形式で best-effort パースしてキー情報として記録する
(ファイル名は §5.2 の難読化解除まで試みる)。
メイン観測の後は、紹介されたノードへ深さ1のスノーボールを行う。

観測専用: ファイル実体の送受信なし、自前のキー情報は持たない・
送らない (受信したものの記録のみ)。自ノードは Port0 として
申告する (タイプ2 フラグ[1]=1。タイプ3 のポート欄は実クライアント
同様に受付ポート設定値を書く。PROTOCOL.md §6.2)。

v3.2: 実クライアントのリンク保持動作を再現する。
- タイプ10 (ペイロード 0x0A のみ) を受けたら、0850 -> 1110/1120
  -> 1130 -> 1090 の生成経路どおりの「空クエリ」 (タイプ13、
  検索条件なし・キーヘッダ 0 件) をその相手へ返す (§6.1)。
- こちらからもタイプ10 を周期送信する (実クライアントの
  mf_CMainControl_0830 と同じ30秒周期)。
パース不能なフレームは raw として記録して継続し、切断しない。

成果物 (このスクリプトと同じフォルダ、または out_dir に保存):
  result_crawl.txt : 全ログ
  nodes.json       : エントリ / peer 情報 / 紹介ノード一覧 /
                     キー情報 / 切断理由 / スノーボール結果
  stream_dump.bin  : エントリ接続の復号済み受信ストリーム全体
                     (フレーム長プレフィクス込み、逐次保存)

フレーム長異常 (ProtocolError) が発生した場合は切断せず
「raw継続モード」に入り、残りの観測時間いっぱい復号済み
バイト列をそのまま stream_dump.bin へ追記し続ける。異常発生
位置 (ストリーム先頭からのオフセット) と異常箇所の前後
256バイトの hex ダンプは result_crawl.txt に残す。

使い方:
  python crawl.py [--duration 600] [--snowball-max 10]
                  [--snowball-observe 20]
"""

import argparse
import ipaddress
import json
import os
import socket
import struct
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from winny_codec import (RC4, build_empty_query_payload, decode_node_string,
                         dotted, parse_type4)
from winny_client import DISCONNECT_TYPES, ProtocolError, WinnyConnection, disp

HERE = os.path.dirname(os.path.abspath(__file__))
MAX_CANDIDATE_TRIES = 40


# ------------------------------------------------------- 候補ノード

def parse_candidates(text: str) -> list:
    """Noderef テキストから公開 (host, port) 候補を抽出する。

    bootstrap.py の candidates と同じ規則: "@" 形式は復号し、
    プライベート/ループバック/リンクローカルは除外、重複は除く。
    """
    seen = set()
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        host = port = None
        if line.startswith("@"):
            plain = decode_node_string(line)
            if plain is None:
                continue
            parts = plain.decode("ascii", "replace").split(":")
            if len(parts) >= 2:
                host, port = parts[0], parts[1]
        else:
            parts = line.split(":")
            if len(parts) >= 2:
                host, port = parts[0], parts[1]
        if not host or not port:
            continue
        try:
            ip = ipaddress.ip_address(host)
            port = int(port)
        except ValueError:
            if host and port.isdigit():
                out.append((host, int(port)))
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            continue
        key = (host, port)
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def load_candidates(log) -> tuple:
    """noderef_extra.txt を最優先、なければ noderef_fallback.txt。

    戻り値: (候補リスト, 出典ファイル名 or None)。
    """
    for name in ("noderef_extra.txt", "noderef_fallback.txt"):
        path = os.path.join(HERE, name)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8", errors="replace") as f:
            cands = parse_candidates(f.read())
        if cands:
            log("candidates: %d public entries from %s" % (len(cands), name))
            return cands, name
        log("%s exists but yielded no public candidates" % name)
    log("no usable noderef file found")
    return [], None


# ------------------------------------------- タイプ13 / CKeyHeader

def _need(buf: bytes, pos: int, n: int, what: str) -> None:
    if pos + n > len(buf):
        raise ValueError("truncated: %s at %d (need %d, have %d)"
                         % (what, pos, n, len(buf) - pos))


def decode_key_filename(field: bytes):
    """CKeyHeader 内のファイル名フィールド (§5.2 形式) を復号する。

    形式は「2バイトヘッダ + 本体」。ヘッダ (uint16 LE) は本体平文の
    バイト合計。ヘッダが 0 でない場合は難読化状態で、本体は
    「チェックサム下位1バイトを1文字鍵とする RC4」で暗号化されて
    いる (CKey::mf_CKey_0280)。復号後に本体バイト合計の下位
    16ビットがチェックサムと一致すれば成功し平文を返し、
    一致しなければ None を返す。ヘッダが 0 の場合は平文状態
    なので本体をそのまま返す。
    """
    if len(field) < 2:
        return None
    (checksum,) = struct.unpack_from("<H", field, 0)
    body = bytes(field[2:])
    if checksum == 0:
        return body
    plain = RC4(bytes([field[0]])).crypt(body)
    if (sum(plain) & 0xFFFF) != checksum:
        return None
    return plain


def parse_key_header(buf: bytes, pos: int) -> tuple:
    """CKeyHeader 1件をパースする (§6 / CQuery::mf_CQuery_0080 準拠)。

    戻り値: (レコード dict, 次のオフセット)。切り詰め時は ValueError。
    """
    _need(buf, pos, 12, "keyheader locations")
    ip1 = dotted(buf[pos:pos + 4])
    (port1,) = struct.unpack_from("<H", buf, pos + 4)
    pos += 6
    ip2 = dotted(buf[pos:pos + 4])
    (port2,) = struct.unpack_from("<H", buf, pos + 4)
    pos += 6
    _need(buf, pos, 4 + 16 + 1, "keyheader size/hash/namelen")
    (size,) = struct.unpack_from("<I", buf, pos)
    pos += 4
    hash16 = bytes(buf[pos:pos + 16])
    pos += 16
    name_len = buf[pos]
    pos += 1
    _need(buf, pos, name_len + 2, "keyheader filename")
    name_field = bytes(buf[pos:pos + name_len + 2])
    pos += name_len + 2
    _need(buf, pos, 11 + 1, "keyheader id1/id2len")
    id1 = bytes(buf[pos:pos + 11]).split(b"\x00")[0]
    pos += 11
    id2_len_raw = buf[pos]
    pos += 1
    id2_len = min(id2_len_raw, 11)  # 0080 は読み取りを 11 で打ち切る
    _need(buf, pos, id2_len + 2 + 4 + 4 + 2, "keyheader tail")
    id2 = bytes(buf[pos:pos + id2_len]).split(b"\x00")[0]
    pos += id2_len
    (value1,) = struct.unpack_from("<H", buf, pos)
    pos += 2
    (refs,) = struct.unpack_from("<i", buf, pos)
    pos += 4
    (timestamp,) = struct.unpack_from("<i", buf, pos)
    pos += 4
    flags = bytes(buf[pos:pos + 2])
    pos += 2
    name = decode_key_filename(name_field)
    return {
        "ip1": ip1, "port1": port1,
        "ip2": ip2, "port2": port2,
        "size": size,
        "hash": hash16.hex(),
        "filename": disp(name) if name is not None else None,
        "filename_ok": name is not None,
        "id1": disp(id1),
        "id2": disp(id2),
        "value1": value1,
        "refs": refs,
        "time": timestamp,
        "flags": flags.hex(),
    }, pos


def parse_query_type13(payload: bytes) -> dict:
    """タイプ13 ペイロード全体 (タイプバイト含む) をパースする (§6)。

    切り詰めや不整合があれば ValueError。呼び出し側は raw として
    記録して継続すること。
    """
    if not payload or payload[0] != 13:
        raise ValueError("not a type 13 payload")
    pos = 1
    _need(payload, pos, 4, "query flags")
    flags = {
        "responded": payload[pos] != 0,
        "with_keys": payload[pos + 1] != 0,
        "port0": payload[pos + 2] != 0,
        "bbs": payload[pos + 3] != 0,
    }
    pos += 4
    _need(payload, pos, 4 + 1, "query value/searchlen")
    (value,) = struct.unpack_from("<i", payload, pos)
    pos += 4
    slen = payload[pos]
    pos += 1
    _need(payload, pos, slen + 11 + 1, "query search/id/routecount")
    search = disp(bytes(payload[pos:pos + slen]))
    pos += slen
    searcher_id = disp(bytes(payload[pos:pos + 11]).split(b"\x00")[0])
    pos += 11
    hcount = payload[pos]
    pos += 1
    route = []
    for _ in range(hcount):
        _need(payload, pos, 6, "route host")
        ip = dotted(payload[pos:pos + 4])
        (port,) = struct.unpack_from("<H", payload, pos + 4)
        pos += 6
        route.append({"ip": ip, "port": port})
    _need(payload, pos, 2, "key count")
    (kcount,) = struct.unpack_from("<H", payload, pos)
    pos += 2
    keys = []
    for _ in range(kcount):
        kh, pos = parse_key_header(payload, pos)
        keys.append(kh)
    return {
        "flags": flags,
        "value": value,
        "search": search,
        "searcher_id": searcher_id,
        "route": route,
        "keys": keys,
        "trailing_bytes": len(payload) - pos,
    }


# ------------------------------------------------------- 観測接続

def _jsonable_node(info):
    """parse_type3 / parse_type4 の結果を JSON 化できる形にする。"""
    if info is None:
        return None
    out = {"ip": info["ip"], "port": info["port"],
           "clusters": [disp(c) for c in info.get("clusters", [])]}
    if "ddns" in info:
        out["ddns"] = disp(info["ddns"])
    if "bbs_port" in info:
        out["bbs_port"] = info["bbs_port"]
        out["is_bbs"] = info["is_bbs"]
        out["line_speed"] = info["line_speed"]
    return out


class CrawlingConnection(WinnyConnection):
    """フレーム記録・タイプ4 蓄積・タイプ13 パースを追加した観測接続。

    WinnyConnection のディスパッチはそのまま使い、process_frame の
    前段で記録だけを行う (観測専用の原則は親クラスと同じ)。
    """

    def __init__(self, *args, clock_start=None, stream_dump_path=None,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.t0 = clock_start if clock_start is not None else time.monotonic()
        self.frames = []            # {"elapsed", "type", "len"}
        self.keys = []              # パースできた CKeyHeader (+elapsed)
        self.type13_unparsed = 0    # パース不能だったタイプ13の件数
        self.query_responses = []   # タイプ10 応答として送った空クエリ
        self.type10_sent = 0        # 周期送信したタイプ10の件数
        self.disconnect_notice = None
        self.last_frame_at = None   # t0 基準の経過秒
        self._intro_seen = {}       # (ip, port) -> 紹介レコード
        # 復号済み受信ストリームの逐次ダンプ (stream_dump_path 指定時)
        self.stream_dump_path = stream_dump_path
        self.stream_bytes = 0       # ダンプ済み総バイト数
        self.framing_error = None   # {"offset", "invalid_length", "detail"}
        self._dump_file = None
        if stream_dump_path is not None:
            self._dump_file = open(stream_dump_path, "wb")
            self.frame_sink = self._write_dump

    def _write_dump(self, data: bytes) -> None:
        if self._dump_file is not None:
            self._dump_file.write(data)
            self._dump_file.flush()
        self.stream_bytes += len(data)

    def note_framing_error(self, err) -> dict:
        """フレーム長異常を記録する。オフセットは異常フレーム先頭の
        ストリーム位置 (= ダンプ済みバイト数)。"""
        self.framing_error = {
            "offset": self.stream_bytes,
            "invalid_length": self.last_bad_length,
            "detail": str(err),
        }
        return self.framing_error

    def close(self) -> None:
        if self._dump_file is not None:
            try:
                self._dump_file.close()
            except OSError:
                pass
            self._dump_file = None
        super().close()

    def elapsed(self) -> float:
        return time.monotonic() - self.t0

    @property
    def introduced(self) -> list:
        """重複を除いた紹介ノード一覧 (first-seen 順)。"""
        return list(self._intro_seen.values())

    def process_frame(self, payload: bytes) -> bool:
        t = payload[0] if payload else -1
        now = self.elapsed()
        self.frames.append({"elapsed": round(now, 3), "type": t,
                            "len": len(payload)})
        self.last_frame_at = now
        if t in DISCONNECT_TYPES:
            self.disconnect_notice = t
        if t == 4:
            self._note_intro(payload, now)
        if t == 13:
            self._handle_type13(payload, now)
        if t == 10 and len(payload) == 1:
            self._respond_to_type10(now)
        return super().process_frame(payload)

    def _respond_to_type10(self, now: float) -> None:
        """タイプ10 への応答: 空クエリ (タイプ13) を相手へ返す。

        0780 は len==1 のタイプ10 で 0850 を呼び、0850 は接続方向で
        1110 (上り) / 1120 (下り) を選ぶ。相手が上り接続なら
        unk03=0 の 1110 形式、下りなら unk03=1 の 1120 形式。
        シリアルは 0850 経路では検索カウンタ由来で、当クローラは
        UI 検索等を一切しないため実クライアントでも常に 0 (§6.1)。
        応答はあくまで生成経路の再現であり、自前のキーは持たない
        のでキーヘッダは 0 件のまま。
        """
        up = self.peer_is_up_connection()
        payload = build_empty_query_payload(
            down=not up, serial=0,
            self_ip=socket.inet_aton(self.self_ip),
            self_port=self.accept_port)
        try:
            self.send_frame(payload)
        except OSError as e:
            self.log("send: type 13 empty query FAILED (%s)" % e)
            return
        form = "1110" if up else "1120"
        self.query_responses.append({
            "elapsed": round(now, 3), "form": form,
            "payload_hex": payload.hex()})
        self.log("send: type 13 empty query (%s form, unk03=%d) "
                 "in response to type 10" % (form, 0 if up else 1))

    def send_type10(self) -> None:
        """タイプ10 を1つ送る (0830 の周期送信の再現)。"""
        try:
            self.send_frame(b"\x0a")
        except OSError as e:
            self.log("send: type 10 FAILED (%s)" % e)
            return
        self.type10_sent += 1
        self.log("send: type 10 (periodic, #%d)" % self.type10_sent)

    def _note_intro(self, payload: bytes, now: float) -> None:
        try:
            info = parse_type4(payload[1:])
        except ValueError:
            return
        key = (info["ip"], info["port"])
        if key not in self._intro_seen:
            rec = _jsonable_node(info)
            rec["entry"] = "%s:%d" % (info["ip"], info["port"])
            rec["first_seen_elapsed"] = round(now, 3)
            self._intro_seen[key] = rec

    def _handle_type13(self, payload: bytes, now: float) -> None:
        try:
            q = parse_query_type13(payload)
        except ValueError as e:
            self.type13_unparsed += 1
            self.log("recv: type 13 parse FAILED (%s); raw head=%s"
                     % (e, payload[:48].hex()))
            return
        active_flags = [k for k, v in q["flags"].items() if v]
        self.log("recv: type 13 query search=%r keys=%d route=%d flags=%s"
                 % (q["search"], len(q["keys"]), len(q["route"]),
                    active_flags))
        for kh in q["keys"]:
            rec = dict(kh)
            rec["elapsed"] = round(now, 3)
            rec["query_search"] = q["search"]
            self.keys.append(rec)
            self.log("  key: file=%r size=%d hash=%s.. at=%s:%d refs=%d"
                     % (kh["filename"], kh["size"], kh["hash"][:16],
                        kh["ip1"], kh["port1"], kh["refs"]))


# ------------------------------------------------------- 受信ポンプ

def _pump_raw_until(conn: CrawlingConnection, deadline: float) -> None:
    """raw継続モード: deadline まで復号済みバイト列をダンプし続ける。

    フレーム解釈は一切しない。バイトは read_raw_decrypted 経由で
    frame_sink (= stream_dump.bin) へ流れ、conn.stream_bytes が進む。
    """
    while not conn.closed and time.monotonic() < deadline:
        if conn.read_raw_decrypted(timeout=0.5) is None:
            conn.log("raw continuation: peer EOF")
            return


def _pump_until(conn: CrawlingConnection, deadline: float,
                stop_pred=None, raw_on_error: bool = False,
                tick=None) -> dict:
    """deadline まで (または stop_pred が真になるまで) 受信を回す。

    戻り値は終了理由 dict {"reason", "detail"}。reason は
    condition_met / deadline / peer_eof / peer_disconnect_notice /
    protocol_error / frame_handler_close のいずれか。
    raw_on_error が真でダンプ有効な接続では、フレーム長異常時に
    切断せず raw継続モードへ移行し、reason は
    framing_error_raw_continued になる (dict に stream_offset /
    invalid_length も入る)。
    tick が渡された場合はループ反復ごとに呼ぶ (周期送信などの
    ハウスキーピング用。tick 側で間引きすること)。
    """
    while not conn.closed and time.monotonic() < deadline:
        if stop_pred is not None and stop_pred(conn):
            return {"reason": "condition_met", "detail": ""}
        if tick is not None:
            tick()
        try:
            payload = conn.next_frame()
        except ProtocolError as e:
            if raw_on_error and conn.stream_dump_path is not None:
                fe = conn.note_framing_error(e)
                conn.log("protocol error: %s at stream offset %d "
                         "-> RAW CONTINUATION MODE (no disconnect)"
                         % (e, fe["offset"]))
                _pump_raw_until(conn, deadline)
                return {"reason": "framing_error_raw_continued",
                        "detail": str(e),
                        "stream_offset": fe["offset"],
                        "invalid_length": fe["invalid_length"]}
            conn.log("protocol error: %s -> disconnect" % e)
            return {"reason": "protocol_error", "detail": str(e)}
        if payload is None:
            if not conn.read_once(timeout=0.5):
                return {"reason": "peer_eof",
                        "detail": "connection closed by peer (EOF/socket)"}
            continue
        if not conn.process_frame(payload):
            if conn.disconnect_notice is not None:
                return {"reason": "peer_disconnect_notice",
                        "detail": "type 0x%02x" % conn.disconnect_notice}
            return {"reason": "frame_handler_close",
                    "detail": "process_frame returned False (hello failure?)"}
    if stop_pred is not None and stop_pred(conn):
        return {"reason": "condition_met", "detail": ""}
    if conn.closed:
        return {"reason": "peer_eof", "detail": "socket closed"}
    return {"reason": "deadline", "detail": "window elapsed"}


def _format_hexdump(data: bytes, base_offset: int) -> list:
    """data を16バイト/行の hex ダンプ行にする (base_offset は先頭位置)。"""
    out = []
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        hexs = " ".join("%02x" % b for b in chunk)
        text = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        out.append("%08x  %-47s  %s" % (base_offset + i, hexs, text))
    return out


def _log_framing_hexdump(conn: CrawlingConnection, dump_path: str,
                         log) -> None:
    """異常箇所の前後256バイトを stream_dump.bin から読み、hex ダンプ
    としてログに残す (result_crawl.txt へ転記される)。"""
    fe = conn.framing_error
    try:
        with open(dump_path, "rb") as f:
            blob = f.read()
    except OSError as e:
        log("framing error hex dump: cannot read %s (%s)" % (dump_path, e))
        return
    start = max(0, fe["offset"] - 256)
    end = min(len(blob), fe["offset"] + 256)
    log("framing error at stream offset %d (invalid length %s); "
        "hex dump [%d, %d) of %d dumped bytes:"
        % (fe["offset"], fe["invalid_length"], start, end, len(blob)))
    for hl in _format_hexdump(blob[start:end], start):
        log("  " + hl)


def _handshake_done(conn: CrawlingConnection) -> bool:
    return (conn.peer_hello_version is not None
            and conn.peer_node is not None)


# ------------------------------------------------------- スノーボール

def probe_node(host: str, port: int, *, budget: float, log, clock,
               connect_timeout: float = 5.0) -> dict:
    """1ノード分のハンドシェイク+観測 (合計 budget 秒まで)。"""
    rec = {"host": host, "port": port, "alive": False, "peer": None,
           "peer_version": None, "introduced": [], "keys": [],
           "query_responses": 0, "end": None, "error": None}
    started = time.monotonic()
    conn = CrawlingConnection(host, port, clock_start=clock, log=log)
    try:
        conn.sock.settimeout(connect_timeout)
        conn.connect()
    except OSError as e:
        rec["error"] = "%s: %s" % (type(e).__name__, e)
        log("snowball %s:%d connect failed: %s" % (host, port, rec["error"]))
        conn.close()
        return rec
    deadline = started + budget
    _pump_until(conn, deadline, _handshake_done)
    if _handshake_done(conn):
        rec["alive"] = True
        rec["peer"] = _jsonable_node(conn.peer_node)
        rec["peer_version"] = conn.peer_hello_version
        endinfo = _pump_until(conn, deadline, None)
        rec["end"] = endinfo
        log("snowball %s:%d ALIVE (version %s), introduced %d, keys %d, "
            "ended: %s" % (host, port, rec["peer_version"],
                           len(conn.introduced), len(conn.keys),
                           endinfo["reason"]))
    else:
        rec["end"] = {"reason": "handshake_incomplete", "detail": ""}
        log("snowball %s:%d handshake incomplete" % (host, port))
    rec["introduced"] = conn.introduced
    rec["keys"] = conn.keys
    rec["query_responses"] = len(conn.query_responses)
    conn.close()
    return rec


def _is_public(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return True  # ホスト名は名前解決に任せる
    return not (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast)


def snowball(entry_conn: CrawlingConnection, entry_addr: tuple, *,
             max_nodes: int, observe_seconds: float, log, clock,
             skip_non_public: bool = True,
             connect_timeout: float = 5.0) -> list:
    """紹介ノードへ深さ1のスノーボール (first-seen 順、最大 max_nodes 件)。"""
    results = []
    for rec in entry_conn.introduced:
        if len(results) >= max_nodes:
            break
        host, port = rec["ip"], rec["port"]
        out = {"host": host, "port": port, "alive": False, "peer": None,
               "peer_version": None, "introduced": [], "keys": [],
               "query_responses": 0,
               "end": None, "error": None, "skipped": None}
        if (host, port) == entry_addr:
            out["skipped"] = "entry node itself"
        elif port == 0:
            out["skipped"] = "port 0"
        elif skip_non_public and not _is_public(host):
            out["skipped"] = "non-public address"
        if out["skipped"] is not None:
            log("snowball %s:%d skipped (%s)" % (host, port, out["skipped"]))
            results.append(out)
            continue
        results.append(probe_node(host, port, budget=observe_seconds,
                                  log=log, clock=clock,
                                  connect_timeout=connect_timeout))
    return results


# ------------------------------------------------------- メイン

def run_crawl(*, duration: float = 600.0, snowball_max: int = 10,
              snowball_observe: float = 20.0, candidates=None,
              candidate_source: str = "argument", out_dir=None,
              handshake_timeout: float = 15.0, connect_timeout: float = 10.0,
              snowball_connect_timeout: float = 5.0,
              type10_period: float = 30.0,
              skip_non_public: bool = True, echo: bool = True) -> tuple:
    """クロール1回分を実行し、(result dict, ログ行リスト) を返す。

    out_dir (既定はこのスクリプトのフォルダ) に result_crawl.txt と
    nodes.json を書く。
    """
    if out_dir is None:
        out_dir = HERE
    clock = time.monotonic()
    lines = []

    def log(msg):
        line = "[+%9.2fs] %s" % (time.monotonic() - clock, msg)
        if echo:
            print(line, flush=True)
        lines.append(line)

    result = {
        "started_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "observe_seconds": duration,
        "entry": None,
        "peer": None,
        "peer_version": None,
        "attempts": [],
        "frames": [],
        "introduced_nodes": [],
        "keys": [],
        "type13_unparsed": 0,
        "query_responses": [],
        "type10_sent": 0,
        "disconnect": None,
        "stream_dump": {"file": None, "bytes": 0},
        "snowball": [],
    }
    dump_path = os.path.join(out_dir, "stream_dump.bin")

    if candidates is None:
        candidates, candidate_source = load_candidates(log)
    else:
        log("candidates: %d entries (source: %s)"
            % (len(candidates), candidate_source))

    entry_conn = None
    entry_addr = None
    for host, port in candidates[:MAX_CANDIDATE_TRIES]:
        log("--- try entry %s:%d" % (host, port))
        conn = CrawlingConnection(host, port, clock_start=clock, log=log,
                                  stream_dump_path=dump_path)
        try:
            conn.sock.settimeout(connect_timeout)
            conn.connect()
        except OSError as e:
            err = "%s: %s" % (type(e).__name__, e)
            log("connect failed: %s" % err)
            result["attempts"].append({"host": host, "port": port,
                                       "error": err})
            conn.close()
            continue
        _pump_until(conn, time.monotonic() + handshake_timeout,
                    _handshake_done)
        if _handshake_done(conn):
            entry_conn = conn
            entry_addr = (host, port)
            result["entry"] = {"host": host, "port": port,
                               "source": candidate_source}
            log("ENTRY ESTABLISHED %s:%d (peer version %s)"
                % (host, port, conn.peer_hello_version))
            log("self declaration: ip=%s accept_port=%d "
                "(no listener; Port0 via type2 flag[1]=1)"
                % (conn.self_ip, conn.accept_port))
            break
        log("handshake not completed with %s:%d" % (host, port))
        result["attempts"].append({"host": host, "port": port,
                                   "error": "handshake incomplete"})
        conn.close()

    if entry_conn is None:
        log("no entry node found")
    else:
        log("observing entry for %.0fs ..." % duration)
        # タイプ10 の周期送信 (0830 は実クライアントの起動後経過で
        # 30秒毎。当実装では接続 (観測開始) 起点の30秒毎とし、
        # 位相の差は §6.1 に明記)。type10_period <= 0 で無効化。
        tick = None
        if type10_period and type10_period > 0:
            tick_state = {"next_at": time.monotonic() + type10_period}

            def tick():
                now_m = time.monotonic()
                if now_m >= tick_state["next_at"]:
                    tick_state["next_at"] += type10_period
                    entry_conn.send_type10()

        endinfo = _pump_until(entry_conn,
                              time.monotonic() + duration, None,
                              raw_on_error=True, tick=tick)
        reason = endinfo["reason"]
        if reason == "deadline":
            reason = "observed_full_duration"
        idle = None
        if entry_conn.last_frame_at is not None:
            idle = round(entry_conn.elapsed() - entry_conn.last_frame_at, 2)
        result["disconnect"] = {
            "reason": reason,
            "detail": endinfo["detail"],
            "at_elapsed": round(entry_conn.elapsed(), 2),
            "idle_before_close_seconds": idle,
            "notice": entry_conn.disconnect_notice,
        }
        if "stream_offset" in endinfo:
            result["disconnect"]["stream_offset"] = endinfo["stream_offset"]
            result["disconnect"]["invalid_frame_length"] = \
                endinfo["invalid_length"]
        log("main observation ended: reason=%s detail=%s idle=%s"
            % (reason, endinfo["detail"], idle))
        result["frames"] = entry_conn.frames
        result["peer"] = _jsonable_node(entry_conn.peer_node)
        result["peer_version"] = entry_conn.peer_hello_version
        result["introduced_nodes"] = entry_conn.introduced
        result["keys"] = entry_conn.keys
        result["type13_unparsed"] = entry_conn.type13_unparsed
        result["query_responses"] = entry_conn.query_responses
        result["type10_sent"] = entry_conn.type10_sent
        entry_conn.close()
        if entry_conn.framing_error is not None:
            _log_framing_hexdump(entry_conn, dump_path, log)

        log("snowball: %d introduced nodes, probing up to %d ..."
            % (len(result["introduced_nodes"]), snowball_max))
        result["snowball"] = snowball(
            entry_conn, entry_addr, max_nodes=snowball_max,
            observe_seconds=snowball_observe, log=log, clock=clock,
            skip_non_public=skip_non_public,
            connect_timeout=snowball_connect_timeout)
        alive = sum(1 for r in result["snowball"] if r["alive"])
        log("snowball done: %d/%d alive" % (alive, len(result["snowball"])))

    log("summary: entry=%s introduced=%d keys=%d snowball=%d"
        % (result["entry"], len(result["introduced_nodes"]),
           len(result["keys"]), len(result["snowball"])))

    if os.path.exists(dump_path):
        result["stream_dump"] = {
            "file": os.path.basename(dump_path),
            "bytes": os.path.getsize(dump_path),
        }

    with open(os.path.join(out_dir, "result_crawl.txt"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(out_dir, "nodes.json"), "w",
              encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log("saved: result_crawl.txt / nodes.json / stream_dump.bin in %s"
        % out_dir)
    return result, lines


def main() -> None:
    p = argparse.ArgumentParser(
        description="Winny long-observation crawler (phase 3)")
    p.add_argument("--duration", type=float, default=600.0,
                   help="entry observation seconds (default 600)")
    p.add_argument("--snowball-max", type=int, default=10,
                   help="max introduced nodes to probe (default 10)")
    p.add_argument("--snowball-observe", type=float, default=20.0,
                   help="per-node snowball budget seconds (default 20)")
    p.add_argument("--type10-period", type=float, default=30.0,
                   help="periodic type-10 interval seconds (default 30, "
                        "0 disables)")
    args = p.parse_args()
    run_crawl(duration=args.duration, snowball_max=args.snowball_max,
              snowball_observe=args.snowball_observe,
              type10_period=args.type10_period)


if __name__ == "__main__":
    main()
