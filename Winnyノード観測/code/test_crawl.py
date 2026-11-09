"""crawl.py (フェーズ3クローラ) の自己テスト。

実行: .venv/bin/python test_crawl.py
既存の test_proto.py (15件) とは独立に追加した分。
"""

import os
import socket
import struct
import tempfile
import threading
import unittest

from winny_codec import RC4, build_empty_query_payload
from crawl import decode_key_filename, parse_query_type13, run_crawl
from mock_peer import MockPeer
from winny_client import WinnyConnection


# ------------------------------------------------------- ヘルパー

def make_obfuscated_name(plain: bytes) -> bytes:
    """§5.2 の暗号化方向 (CKey::mf_CKey_0280 の暗号化側) で
    ファイル名フィールドを作る。"""
    total = sum(plain)
    body = RC4(bytes([total & 0xFF])).crypt(plain)
    return struct.pack("<H", total & 0xFFFF) + body


def build_key_header(name_plain: bytes, *, size=123456,
                     ip1="203.0.113.7", port1=7743, refs=42) -> bytes:
    out = bytearray()
    out += socket.inet_aton(ip1)
    out += struct.pack("<H", port1)
    out += b"\x00" * 4
    out += struct.pack("<H", 0)
    out += struct.pack("<I", size)
    out += bytes(range(16))                     # ハッシュ
    out.append(len(name_plain))
    out += make_obfuscated_name(name_plain)
    out += b"POSTERID123"[:11].ljust(11, b"\x00")
    id2 = b"ID2"
    out.append(len(id2))
    out += id2
    out += struct.pack("<H", 7)                 # 値1
    out += struct.pack("<i", refs)              # 参照カウント
    out += struct.pack("<i", 1700000000)        # time_t
    out += b"\x00\x00"                          # フラグ
    return bytes(out)


def build_query(keys=(), search=b"test", route=()) -> bytes:
    out = bytearray()
    out.append(13)
    out += bytes([0, 1 if keys else 0, 0, 0])   # フラグA/B/C/BBS
    out += struct.pack("<i", 12345)
    out.append(len(search))
    out += search
    out += b"SEARCHERID1"[:11].ljust(11, b"\x00")
    out.append(len(route))
    for ip, port in route:
        out += socket.inet_aton(ip)
        out += struct.pack("<H", port)
    out += struct.pack("<H", len(keys))
    for kh in keys:
        out += kh
    return bytes(out)


# ------------------------------------------------------- 単体テスト

class TestKeyFilename(unittest.TestCase):
    def test_plain_state(self):
        field = b"\x00\x00" + b"plain name.txt"
        self.assertEqual(decode_key_filename(field), b"plain name.txt")

    def test_obfuscated_roundtrip(self):
        name = "テストファイル.mkv".encode("cp932")
        field = make_obfuscated_name(name)
        self.assertNotEqual(field[2:], name)  # 実際に暗号化されている
        self.assertEqual(decode_key_filename(field), name)

    def test_tampered_returns_none(self):
        field = bytearray(make_obfuscated_name(b"movie.avi"))
        field[5] ^= 0xFF
        self.assertIsNone(decode_key_filename(bytes(field)))

    def test_too_short(self):
        self.assertIsNone(decode_key_filename(b"\x01"))
        self.assertIsNone(decode_key_filename(b""))


class TestParseQuery(unittest.TestCase):
    def test_query_with_key(self):
        name = "テストデータ.zip".encode("cp932")
        kh = build_key_header(name, size=987654321, refs=42)
        payload = build_query(keys=[kh], search=b"data",
                              route=[("198.51.100.1", 7743)])
        q = parse_query_type13(payload)
        self.assertTrue(q["flags"]["with_keys"])
        self.assertEqual(q["search"], "data")
        self.assertEqual(q["route"], [{"ip": "198.51.100.1", "port": 7743}])
        self.assertEqual(len(q["keys"]), 1)
        k = q["keys"][0]
        self.assertEqual(k["filename"], "テストデータ.zip")
        self.assertTrue(k["filename_ok"])
        self.assertEqual(k["size"], 987654321)
        self.assertEqual(k["refs"], 42)
        self.assertEqual(k["ip1"], "203.0.113.7")
        self.assertEqual(k["port1"], 7743)
        self.assertEqual(k["hash"], bytes(range(16)).hex())
        self.assertEqual(q["trailing_bytes"], 0)

    def test_query_no_keys(self):
        q = parse_query_type13(build_query(keys=(), search=b""))
        self.assertEqual(q["keys"], [])
        self.assertEqual(q["search"], "")

    def test_not_type13(self):
        with self.assertRaises(ValueError):
            parse_query_type13(b"\x0c" + b"\x00" * 20)

    def test_truncated(self):
        payload = build_query(keys=[build_key_header(b"a.bin")])
        with self.assertRaises(ValueError):
            parse_query_type13(payload[:len(payload) - 5])
        with self.assertRaises(ValueError):
            parse_query_type13(payload[:10])


# ------------------------------------------------------- E2E スモーク

class TestCrawlSmoke(unittest.TestCase):
    def test_delayed_introductions_and_snowball(self):
        # スノーボール先モック B (通常の紹介3件を返す)
        peer_b = MockPeer(port=0, log=lambda m: None)
        thread_b = threading.Thread(target=peer_b.serve_once,
                                    kwargs={"timeout": 30}, daemon=True)
        thread_b.start()
        # エントリ側モック A: 直後に3件、5秒後に B と TEST-NET を1件ずつ
        delayed = [
            ("127.0.0.1", peer_b.port, 0, False, 100, (b"bee", b"", b"")),
            ("203.0.113.99", 7743, 0, False, 100, (b"", b"", b"")),
        ]
        peer_a = MockPeer(port=0, intro_delay_nodes=delayed,
                          intro_delay=5.0, log=lambda m: None)
        thread_a = threading.Thread(target=peer_a.serve_once,
                                    kwargs={"timeout": 30}, daemon=True)
        thread_a.start()
        try:
            with tempfile.TemporaryDirectory() as td:
                result, _lines = run_crawl(
                    duration=8.0, snowball_max=10, snowball_observe=4.0,
                    candidates=[("127.0.0.1", peer_a.port)],
                    out_dir=td, handshake_timeout=5.0,
                    snowball_connect_timeout=1.5,
                    skip_non_public=False, echo=False)
                self.assertTrue(os.path.exists(
                    os.path.join(td, "nodes.json")))
                self.assertTrue(os.path.exists(
                    os.path.join(td, "result_crawl.txt")))
        finally:
            thread_a.join(timeout=35)
            thread_b.join(timeout=35)
            peer_a.close()
            peer_b.close()

        self.assertIsNotNone(result["entry"])
        self.assertEqual(result["entry"]["port"], peer_a.port)
        self.assertEqual(result["peer_version"], 12710)
        # 紹介は第1バッチ3件 + 遅延バッチ2件 = 5件 (重複なし)
        intro = result["introduced_nodes"]
        self.assertEqual(len(intro), 5, intro)
        # 遅延バッチは第1バッチより有意に遅れて届いている
        firsts = sorted(n["first_seen_elapsed"] for n in intro)
        self.assertGreaterEqual(firsts[-1] - firsts[0], 3.5, firsts)
        # メイン観測は時間いっぱいまで維持された
        self.assertEqual(result["disconnect"]["reason"],
                         "observed_full_duration")
        # スノーボール: B が生存し、B からの紹介も3件取れている
        b_rec = [r for r in result["snowball"] if r["port"] == peer_b.port]
        self.assertEqual(len(b_rec), 1, result["snowball"])
        self.assertTrue(b_rec[0]["alive"], b_rec[0])
        self.assertEqual(len(b_rec[0]["introduced"]), 3)
        # モック側でも遅延送信が実際に行われた
        self.assertTrue(peer_a.delayed_intro_sent)


# ------------------------------------------------------- raw継続モード

class TestRawContinuation(unittest.TestCase):
    def test_bad_frame_switches_to_raw_mode(self):
        marker = b"RAW-CONTINUATION-MARKER" * 3
        peer = MockPeer(port=0, send_bad_frame=True,
                        bad_frame_length=0x308A9, bad_frame_delay=1.0,
                        raw_after_bad=marker, raw_after_bad_delay=1.0,
                        log=lambda m: None)
        thread = threading.Thread(target=peer.serve_once,
                                  kwargs={"timeout": 25}, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as td:
                result, _lines = run_crawl(
                    duration=7.0, snowball_max=0, snowball_observe=1.0,
                    candidates=[("127.0.0.1", peer.port)],
                    out_dir=td, handshake_timeout=5.0,
                    skip_non_public=False, echo=False)
                dump_path = os.path.join(td, "stream_dump.bin")
                self.assertTrue(os.path.exists(dump_path))
                with open(dump_path, "rb") as f:
                    blob = f.read()
                with open(os.path.join(td, "result_crawl.txt"),
                          encoding="utf-8") as f:
                    log_text = f.read()
        finally:
            thread.join(timeout=30)
            peer.close()

        self.assertTrue(peer.bad_frame_sent)
        self.assertTrue(peer.raw_after_bad_sent)
        # 異常の前までは通常どおり処理できている
        self.assertEqual(result["peer_version"], 12710)
        self.assertEqual(len(result["introduced_nodes"]), 3)
        # 切断理由は raw継続モードで、異常位置と長さが記録される
        disc = result["disconnect"]
        self.assertEqual(disc["reason"], "framing_error_raw_continued")
        self.assertEqual(disc["invalid_frame_length"], 0x308A9)
        offset = disc["stream_offset"]
        self.assertGreater(offset, 0)
        # 異常の後に送られたバイトが切断されずダンプに残っている
        self.assertGreater(blob.find(marker), offset)
        # nodes.json 側のダンプ記録が実ファイルと一致する
        self.assertEqual(result["stream_dump"]["file"], "stream_dump.bin")
        self.assertEqual(result["stream_dump"]["bytes"], len(blob))
        # result_crawl.txt に hex ダンプが残っている
        self.assertIn("framing error at stream offset %d" % offset,
                      log_text)


# ------------------------------------------- タイプ10応答 (v3.2)

class TestEmptyQueryCodec(unittest.TestCase):
    def test_layout_30_bytes(self):
        payload = build_empty_query_payload(
            down=False, serial=0,
            self_ip=socket.inet_aton("127.0.0.1"), self_port=7743)
        # §6.1 の確定レイアウト: 13 | 00 01 00 00 | int32 0 | 検索長0
        # | 検索者ID 11バイト0 | 経路数1 | 127.0.0.1 + 7743(LE) | キー数0
        self.assertEqual(payload, bytes.fromhex(
            "0d" "00" "01" "00" "00"
            "00000000" "00" + "00" * 11 + "01"
            "7f000001" "3f1e" "0000"))
        self.assertEqual(len(payload), 30)

    def test_down_form_sets_unk03(self):
        payload = build_empty_query_payload(
            down=True, serial=0,
            self_ip=socket.inet_aton("127.0.0.1"), self_port=7743)
        self.assertEqual(payload[3], 1)   # m_flg_unk03 (1120 形式)

    def test_roundtrip_parse(self):
        payload = build_empty_query_payload(
            down=False, serial=0,
            self_ip=socket.inet_aton("127.0.0.1"), self_port=7743)
        q = parse_query_type13(payload)
        self.assertFalse(q["flags"]["responded"])
        self.assertTrue(q["flags"]["with_keys"])   # unk01 (発信元形式)
        self.assertFalse(q["flags"]["port0"])      # unk03 (1110 形式)
        self.assertEqual(q["value"], 0)
        self.assertEqual(q["search"], "")
        self.assertEqual(q["searcher_id"], "")
        self.assertEqual(q["route"], [{"ip": "127.0.0.1", "port": 7743}])
        self.assertEqual(q["keys"], [])
        self.assertEqual(q["trailing_bytes"], 0)


class TestType10Response(unittest.TestCase):
    def test_responds_link_maintained_keys_collected(self):
        peer = MockPeer(port=0, type10_after=1.0,
                        require_query_response=True, query_grace=4.0,
                        reply_query_with_keys=True,
                        log=lambda m: None)
        thread = threading.Thread(target=peer.serve_once,
                                  kwargs={"timeout": 30}, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as td:
                result, _lines = run_crawl(
                    duration=8.0, snowball_max=0, snowball_observe=1.0,
                    candidates=[("127.0.0.1", peer.port)],
                    out_dir=td, handshake_timeout=5.0,
                    type10_period=3.0,
                    skip_non_public=False, echo=False)
        finally:
            thread.join(timeout=35)
            peer.close()

        self.assertIsNotNone(result["entry"])
        # クローラはタイプ10へ空クエリで応答した (モック側で検証済み)
        self.assertIsNotNone(peer.query_response)
        self.assertTrue(peer.query_response_valid)
        self.assertFalse(peer.pruned_no_query)
        q = parse_query_type13(peer.query_response)
        # 相手速度1000 > 自分100 → 上り接続 → 1110形式 (unk03=0)
        self.assertFalse(q["flags"]["port0"])
        self.assertTrue(q["flags"]["with_keys"])
        self.assertEqual(q["search"], "")
        self.assertEqual(q["route"], [{"ip": "127.0.0.1", "port": 7743}])
        self.assertEqual(q["keys"], [])
        # 応答したのでリンクは観測時間いっぱい維持された
        self.assertEqual(result["disconnect"]["reason"],
                         "observed_full_duration")
        self.assertGreaterEqual(len(result["query_responses"]), 1)
        self.assertEqual(result["query_responses"][0]["form"], "1110")
        # 周期タイプ10 がモックへ届いた
        self.assertGreaterEqual(result["type10_sent"], 1)
        self.assertGreaterEqual(peer.type10_received_count, 1)
        # 応答後に流れてきたキー付きクエリをキー収集処理できた
        self.assertTrue(peer.query_reply_sent)
        self.assertEqual(len(result["keys"]), 1)
        self.assertEqual(result["keys"][0]["filename"],
                         "mock-key-file.zip")
        self.assertEqual(result["keys"][0]["size"], 424242)

    def test_no_response_gets_pruned(self):
        # 素の WinnyConnection はタイプ10へ応答しない (応答は
        # CrawlingConnection の責務) → モックは猶予後に切断する
        peer = MockPeer(port=0, type10_after=0.5,
                        require_query_response=True, query_grace=2.0,
                        log=lambda m: None)
        thread = threading.Thread(target=peer.serve_once,
                                  kwargs={"timeout": 15}, daemon=True)
        thread.start()
        conn = WinnyConnection("127.0.0.1", peer.port,
                               log=lambda m: None)
        try:
            conn.connect()
            import time as _time
            started = _time.monotonic()
            conn.run(duration=8.0)
            elapsed = _time.monotonic() - started
        finally:
            thread.join(timeout=20)
            peer.close()
        self.assertTrue(peer.pruned_no_query)
        self.assertIsNone(peer.query_response)
        # 8秒の観測上限より前に相手から切断された
        self.assertLess(elapsed, 8.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
