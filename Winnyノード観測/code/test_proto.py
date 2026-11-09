"""winny_codec / winny_client / mock_peer の自己テスト。

実行: .venv/bin/python test_proto.py
"""

import socket
import struct
import threading
import unittest

from winny_codec import (
    HELLO_KEY,
    RC4,
    build_hello_payload,
    build_type3,
    build_type4,
    cstr_key,
    decode_node_string,
    encode_node_string,
    parse_type3,
    parse_type4,
    rekey_stream_key,
    seed_stream_key,
    verify_hello_payload,
)
from winny_client import WinnyConnection
from mock_peer import DEFAULT_INTRO_NODES, MockPeer


class TestRC4(unittest.TestCase):
    def test_known_vectors(self):
        # Wikipedia / RFC 6229 のテストベクタ
        self.assertEqual(RC4(b"Key").crypt(b"Plaintext").hex().upper(),
                         "BBF316E8D940AF0AD3")
        self.assertEqual(RC4(b"Wiki").crypt(b"pedia").hex().upper(),
                         "1021BF0420")
        self.assertEqual(RC4(b"Secret").crypt(b"Attack at dawn").hex().upper(),
                         "45A01F645FC35B383552544B9BF5")

    def test_streaming_equals_oneshot(self):
        data = bytes(range(256)) * 3
        whole = RC4(b"streamkey").crypt(data)
        rc = RC4(b"streamkey")
        parts = rc.crypt(data[:100]) + rc.crypt(data[100:101]) + rc.crypt(data[101:])
        self.assertEqual(whole, parts)

    def test_clone_peek_does_not_advance(self):
        rc = RC4(b"peek")
        peeked = rc.clone().crypt(b"\x00\x00\x00\x00")
        actual = rc.crypt(b"\x00\x00\x00\x00")
        self.assertEqual(peeked, actual)


class TestCStrKey(unittest.TestCase):
    def test_truncation(self):
        self.assertEqual(cstr_key(b"abcd"), b"abcd")
        self.assertEqual(cstr_key(b"ab\x00cd"), b"ab")
        self.assertEqual(cstr_key(b"\x00ab"), b"\x00")  # C: key[0] を繰り返す
        self.assertEqual(seed_stream_key(b"\x12\x00\x34\x56"), b"\x12")
        self.assertEqual(rekey_stream_key(b"\x12\x34\x56\x78"),
                         bytes([0x12, 0x34 ^ 0x39, 0x56 ^ 0x39, 0x78 ^ 0x39]))
        self.assertEqual(rekey_stream_key(b"\x00\x11\x22\x33"), b"\x00")


class TestNodeString(unittest.TestCase):
    PLAINTEXTS = [
        b"192.168.0.1:7743",
        b"127.0.0.1:0",
        b"example.ddns.jp:12345",
        "ノード:7743".encode("cp932"),
        b"A",
        b"",
    ]

    def test_roundtrip(self):
        for pt in self.PLAINTEXTS:
            enc = encode_node_string(pt)
            self.assertTrue(enc.startswith("@"), enc)
            self.assertEqual(decode_node_string(enc), pt, enc)

    def test_checksum_byte(self):
        pt = b"10.0.0.1:7743"
        enc = encode_node_string(pt)
        self.assertEqual(int(enc[1:3], 16), sum(pt) & 0xFF)

    def test_decode_rejects(self):
        self.assertIsNone(decode_node_string("192.168.0.1:7743"))  # '@' なし
        self.assertIsNone(decode_node_string("@zz"))               # 16進でない
        self.assertIsNone(decode_node_string("@0"))                # 奇数長
        enc = encode_node_string(b"192.168.0.1:7743")
        # チェックサムを別の値に書き換える
        bad_sum = (int(enc[1:3], 16) + 1) & 0xFF
        tampered = "@%02x%s" % (bad_sum, enc[3:])
        self.assertIsNone(decode_node_string(tampered))


class TestHello(unittest.TestCase):
    def test_build_verify(self):
        payload = build_hello_payload()
        self.assertEqual(len(payload), 21)
        self.assertEqual(payload[0], 0)
        self.assertEqual(verify_hello_payload(payload), 12710)

    def _craft(self, version: int, field: bytes) -> bytes:
        plain = struct.pack("<i", version) + field
        return b"\x00" + RC4(HELLO_KEY).crypt(plain)

    def test_version_ranges(self):
        field = b"Winny Ver2.0b1  "
        self.assertEqual(verify_hello_payload(self._craft(12660, field)), 12660)
        self.assertEqual(verify_hello_payload(self._craft(12899, field)), 12899)
        self.assertIsNone(verify_hello_payload(self._craft(12659, field)))
        self.assertIsNone(verify_hello_payload(self._craft(12900, field)))
        self.assertEqual(verify_hello_payload(self._craft(20000, field)), 20000)
        self.assertEqual(verify_hello_payload(self._craft(20999, field)), 20999)
        self.assertIsNone(verify_hello_payload(self._craft(21000, field)))

    def test_bad_magic(self):
        payload = self._craft(12710, b"Winny Ver3.0b1  ")
        self.assertIsNone(verify_hello_payload(payload))

    def test_truncated(self):
        self.assertIsNone(verify_hello_payload(b"\x00" + b"\x00" * 10))
        self.assertIsNone(verify_hello_payload(b""))


class TestType34(unittest.TestCase):
    def test_type3_roundtrip(self):
        payload = build_type3(socket.inet_aton("10.1.2.3"), 7743,
                              b"my.ddns", (b"aa", b"", b"ccc"))
        info = parse_type3(payload[1:])
        self.assertEqual(info["ip"], "10.1.2.3")
        self.assertEqual(info["port"], 7743)
        self.assertEqual(info["ddns"], b"my.ddns")
        self.assertEqual(info["clusters"], [b"aa", b"", b"ccc"])

    def test_type4_roundtrip(self):
        payload = build_type4(socket.inet_aton("203.0.113.10"), 7743, 0,
                              False, 512, (b"anime", b"2026", b""))
        info = parse_type4(payload[1:])
        self.assertEqual(info["ip"], "203.0.113.10")
        self.assertEqual(info["port"], 7743)
        self.assertEqual(info["bbs_port"], 0)
        self.assertFalse(info["is_bbs"])
        self.assertEqual(info["line_speed"], 512)
        self.assertEqual(info["clusters"], [b"anime", b"2026", b""])


class TestEndToEnd(unittest.TestCase):
    def run_e2e(self, client_seed=None, mock_seed=None):
        logs: list[str] = []
        peer = MockPeer(port=0, seed=mock_seed,
                        log=lambda m: logs.append("[mock] " + m))
        thread = threading.Thread(target=peer.serve_once,
                                  kwargs={"timeout": 8}, daemon=True)
        thread.start()
        conn = WinnyConnection(
            "127.0.0.1", peer.port, seed=client_seed,
            clusters=(b"test", b"", b""),
            log=lambda m: logs.append("[client] " + m))
        try:
            conn.connect()
            conn.run(duration=2.0)
        finally:
            thread.join(timeout=9)
            peer.close()
        return peer, conn, logs

    def assert_e2e_ok(self, peer, conn, logs):
        # モック側: クライアントのハンドシェイクを全部受け取れたか
        self.assertTrue(peer.received["marker"])
        self.assertEqual(peer.received["hello_version"], 12710)
        self.assertAlmostEqual(peer.received["type1"], 100.0, places=3)
        self.assertEqual(peer.received["type2"], [0, 1, 0, 0])  # Port0 申告
        self.assertIsNotNone(peer.received["type3"])
        # タイプ3 のポート欄は m_port_accept_ 相当の申告値 (0670)。
        # Port0 性はタイプ2 [1] で申告され、ポート欄は 0 にならない
        # (0 のままだと相手の 1140 が接続20秒超で切断する。§6.2)
        from winny_client import DEFAULT_ACCEPT_PORT
        self.assertEqual(peer.received["type3"]["port"],
                         DEFAULT_ACCEPT_PORT)
        self.assertEqual(peer.received["type3"]["clusters"][0], b"test")
        self.assertTrue(peer.intro_sent)
        # クライアント側: モックのハロー検証・タイプ3・タイプ4 が取れたか
        self.assertEqual(conn.peer_hello_version, 12710)
        self.assertIsNotNone(conn.peer_node)
        self.assertEqual(conn.peer_node["port"], peer.port)
        self.assertEqual(conn.peer_node["clusters"][0], b"mock")
        self.assertEqual(len(conn.nodes), len(DEFAULT_INTRO_NODES))
        for got, want in zip(conn.nodes, DEFAULT_INTRO_NODES):
            ip, port, bbs_port, is_bbs, speed, clusters = want
            self.assertEqual(got["ip"], ip)
            self.assertEqual(got["port"], port)
            self.assertEqual(got["line_speed"], speed)
            self.assertEqual(got["clusters"], list(clusters))
        # タイプ31 を「記録して読み飛ばす」経路を通ったか
        self.assertTrue(any("type 31" in line for line in logs), logs)

    def test_e2e_random_seeds(self):
        peer, conn, logs = self.run_e2e()
        self.assert_e2e_ok(peer, conn, logs)

    def test_e2e_zero_byte_seeds(self):
        # シード中の 0x00 で鍵が打ち切られるケース (C 文字列意味論)
        peer, conn, logs = self.run_e2e(client_seed=b"\x41\x00\x42\x43",
                                        mock_seed=b"\x00\x11\x22\x33")
        self.assert_e2e_ok(peer, conn, logs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
