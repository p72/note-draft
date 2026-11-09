"""Winny 2 (b7.1) プロトコル用コーデック。

根拠: ~/workspace/winny-research/src/71/ の再構成ソースと
~/workspace/winny-research/PROTOCOL.md。

内容:
- RC4 (CRC4.cpp 準拠の標準 RC4)
- C 文字列意味論の鍵切り詰め (鍵バイト列中の 0x00 で打ち切り)
- 初期ノード文字列 ("@" 形式) のエンコード/デコード (CKey::mf_CKey_0270)
- ハロー (タイプ0) の構築と検証 (CMainControl::mf_CMainControl_0670 / 0780)
- シード鍵 / 再鍵の導出 (CHost::mf_CHost_0030 / 0060, 0670, 0780)
- タイプ3 (自ノード情報) / タイプ4 (ノード紹介) の構築とパース
- タイプ13 空クエリ (タイプ10 応答) の構築 (CQuery::mf_CQuery_0070 準拠)
"""

import struct

# ---------------------------------------------------------------- RC4

class RC4:
    """CRC4.cpp と等価な標準 RC4 ストリーム暗号 (状態保持型)。"""

    def __init__(self, key: bytes):
        if len(key) == 0:
            # C 実装では strlen(key)==0 のとき鍵バイト key[0] (=0x00) を
            # 繰り返し読むため、実効鍵は 0x00 1バイトと等価。
            key = b"\x00"
        s = list(range(256))
        j = 0
        klen = len(key)
        for i in range(256):
            j = (j + s[i] + key[i % klen]) & 0xFF
            s[i], s[j] = s[j], s[i]
        self._s = s
        self._i = 0
        self._j = 0

    def crypt(self, data: bytes) -> bytes:
        """現在の状態から続きを暗号化/復号する (XOR なので対称)。"""
        s = self._s
        i = self._i
        j = self._j
        out = bytearray(len(data))
        for n, b in enumerate(data):
            i = (i + 1) & 0xFF
            j = (j + s[i]) & 0xFF
            s[i], s[j] = s[j], s[i]
            out[n] = b ^ s[(s[i] + s[j]) & 0xFF]
        self._i = i
        self._j = j
        return bytes(out)

    def clone(self) -> "RC4":
        """状態のコピー (フレーム長の試行復号用、CHost::mf_CHost_0090 相当)。"""
        other = RC4.__new__(RC4)
        other._s = list(self._s)
        other._i = self._i
        other._j = self._j
        return other

    @staticmethod
    def oneshot(key: bytes, data: bytes) -> bytes:
        return RC4(key).crypt(data)


def cstr_key(material: bytes) -> bytes:
    """鍵バイト列を C 文字列として解釈する (最初の 0x00 で打ち切り)。

    setupkey / CHost::mf_CHost_0030 / 0060 はすべて strlen 意味論。
    切り詰めた結果が空になる場合は key[0]==0x00 が繰り返される
    C 実装の挙動に合わせ、0x00 1バイトを鍵とする。
    """
    idx = material.find(b"\x00")
    if idx >= 0:
        material = material[:idx]
    if len(material) == 0:
        return b"\x00"
    return material


# ------------------------------------------------------- ノード文字列

NODE_TEMPLATE = b"opiewf6ascxlv"


def _node_codec_key(checksum: int) -> bytes:
    """テンプレートの先頭1バイトをチェックサムに置換した鍵。

    CKey::mf_CKey_0270: テンプレート長が 1 でない場合に key[0] を置換する。
    置換後の文字列も setupkey の strlen 意味論を受ける。
    """
    return cstr_key(bytes([checksum]) + NODE_TEMPLATE[1:])


def encode_node_string(plaintext: bytes) -> str:
    """平文 "ホスト名:ポート" を "@" 形式文字列にエンコードする。"""
    checksum = sum(plaintext) & 0xFF
    cipher = RC4(_node_codec_key(checksum)).crypt(plaintext)
    return "@%02x%s" % (checksum, cipher.hex())


def decode_node_string(text: str) -> bytes | None:
    """"@" 形式文字列をデコードする。検証失敗時は None。

    検証条件 (PROTOCOL.md §7.2):
    復号バイト合計 mod 256 == チェックサム かつ 全バイト >= 0x20。
    """
    if not text.startswith("@"):
        return None
    hexpart = text[1:]
    if len(hexpart) == 0 or len(hexpart) % 2 != 0:
        return None
    try:
        raw = bytes.fromhex(hexpart)
    except ValueError:
        return None
    if len(raw) < 1:
        return None
    checksum = raw[0]
    plain = RC4(_node_codec_key(checksum)).crypt(raw[1:])
    if (sum(plain) & 0xFF) != checksum:
        return None
    if any(b < 0x20 for b in plain):
        return None
    return plain


# ------------------------------------------------------------- ハロー

HELLO_KEY = b"98789asj"
HELLO_VERSION = 12710  # b7.1
# 0670 の sprintf リテラルは "Winny Ver2.0b1    " (末尾スペース4つ) だが、
# ワイヤに載るのはペイロード offset 4..20 の 16 バイトのみで、
# 実質 "Winny Ver2.0b1" + スペース2つ になる。
HELLO_STRING_FIELD = b"Winny Ver2.0b1  "
HELLO_MAGIC = b"Winny Ver2.0"  # 検証は先頭12バイト一致 (0780)


def build_hello_payload(version: int = HELLO_VERSION) -> bytes:
    """タイプ0 ペイロード全体 (タイプバイト 0x00 + 二重暗号化された20バイト)。"""
    plain = struct.pack("<i", version) + HELLO_STRING_FIELD
    assert len(plain) == 20
    return b"\x00" + RC4(HELLO_KEY).crypt(plain)


def verify_hello_payload(payload: bytes) -> int | None:
    """受信したタイプ0 ペイロードを検証し、相手バージョンを返す。

    受け入れ条件 (0780): 固定鍵で復号後、バージョンが
    [12660, 12900) ∪ [20000, 21000) かつ magic 12バイト一致。
    失敗時は None。
    """
    if len(payload) < 21 or payload[0] != 0:
        return None
    plain = RC4(HELLO_KEY).crypt(payload[1:21])
    (version,) = struct.unpack_from("<i", plain, 0)
    if plain[4:16] != HELLO_MAGIC:
        return None
    if 12660 <= version < 12900 or 20000 <= version < 21000:
        return version
    return None


# ------------------------------------------------------ シードと鍵導出

def seed_stream_key(seed: bytes) -> bytes:
    """接続初期のストリーム鍵: シード4バイトを C 文字列として解釈。"""
    return cstr_key(bytes(seed[:4]))


def rekey_stream_key(seed: bytes) -> bytes:
    """ハロー後の再鍵: [seed0, seed1^0x39, seed2^0x39, seed3^0x39] を C 文字列解釈。"""
    s = bytes(seed[:4])
    return cstr_key(bytes([s[0], s[1] ^ 0x39, s[2] ^ 0x39, s[3] ^ 0x39]))


# ------------------------------------------------- タイプ3 / タイプ4

def dotted(ip_bytes: bytes) -> str:
    return ".".join(str(b) for b in ip_bytes[:4])


def build_type3(ip: bytes, port: int, ddns: bytes,
                clusters: tuple[bytes, bytes, bytes]) -> bytes:
    """タイプ3 ペイロード (タイプバイト含む)。レイアウトは 0670 準拠。"""
    data = bytearray()
    data += bytes(ip[:4])
    data += struct.pack("<i", port)
    # offset 8: DDNS長, 9..11: クラスタ長。文字列本体は offset 12 から。
    data += bytes([len(ddns) & 0xFF])
    data += bytes(min(len(c), 100) for c in clusters)
    data += ddns
    for c in clusters:
        data += c[:100]
    return b"\x03" + bytes(data)


def parse_type3(data: bytes) -> dict:
    """タイプ3 のデータ部 (タイプバイトの後) をパースする。"""
    if len(data) < 12:
        raise ValueError("type3 data too short: %d" % len(data))
    ip = data[0:4]
    (port,) = struct.unpack_from("<i", data, 4)
    ddns_len = data[8]
    cluster_lens = [data[9], data[10], data[11]]
    pos = 12
    ddns = data[pos:pos + ddns_len]
    pos += ddns_len
    clusters = []
    for ln in cluster_lens:
        clusters.append(data[pos:pos + ln])
        pos += ln
    return {
        "ip": dotted(ip),
        "ip_bytes": bytes(ip),
        "port": port,
        "ddns": ddns,
        "clusters": clusters,
    }


def build_type4(ip: bytes, port: int, bbs_port: int, is_bbs: bool,
                line_speed: int,
                clusters: tuple[bytes, bytes, bytes]) -> bytes:
    """タイプ4 ペイロード (タイプバイト含む)。レイアウトは 1000 準拠。"""
    data = bytearray()
    data += bytes(ip[:4])
    data += struct.pack("<i", port)
    data += struct.pack("<i", bbs_port)
    data += bytes([1 if is_bbs else 0])
    data += struct.pack("<i", line_speed)
    if is_bbs:
        data += b"\x00\x00\x00"
        clusters = (b"", b"", b"")
    else:
        data += bytes(min(len(c), 100) for c in clusters)
    for c in clusters:
        data += c[:100]
    return b"\x04" + bytes(data)


def parse_type4(data: bytes) -> dict:
    """タイプ4 のデータ部をパースする (1010 準拠)。"""
    if len(data) < 20:
        raise ValueError("type4 data too short: %d" % len(data))
    ip = data[0:4]
    (port,) = struct.unpack_from("<i", data, 4)
    (bbs_port,) = struct.unpack_from("<i", data, 8)
    is_bbs = data[12] != 0
    (line_speed,) = struct.unpack_from("<i", data, 13)
    cluster_lens = [data[17], data[18], data[19]]
    pos = 20
    clusters = []
    for ln in cluster_lens:
        clusters.append(data[pos:pos + ln])
        pos += ln
    return {
        "ip": dotted(ip),
        "ip_bytes": bytes(ip),
        "port": port,
        "bbs_port": bbs_port,
        "is_bbs": is_bbs,
        "line_speed": line_speed,
        "clusters": clusters,
    }


# ------------------------------------------- タイプ13 (空クエリ)

def build_empty_query_payload(*, down: bool, serial: int, self_ip: bytes,
                              self_port: int) -> bytes:
    """タイプ10 応答として生成される「空クエリ」のペイロード (30バイト)。

    生成経路 (PROTOCOL.md §6.1):
      0780 (タイプ10, len==1) -> 0850 -> 1110 (上り) / 1120 (下り)
      -> 1130 (クエリ生成: mf_CQuery_0000 + 発信元=自ノード設定)
      -> 1090 (経路に自ノードを積んで検索リンクへ送信)。
    直列化は CQuery::mf_CQuery_0070 準拠:
      [13][unk02=0][unk01=1][unk03=1110時0/1120時1][BBS=0]
      int32 シリアル (0850 経路では検索カウンタ m_int_unk41 由来で、
      UI検索等をしたことのないノードでは常に 0)
      検索文字列長 0 / 検索者ID "" (11バイト 0 埋め)
      経路ホスト数 1 (1090 が積む自ノード: IP + ポート uint16)
      キーヘッダ数 0 (キーを持たないノードでは何も同梱されない)
    """
    out = bytearray()
    out.append(13)
    out.append(0)                       # m_flg_unk02 (応答済み) = false
    out.append(1)                       # m_flg_unk01 (発信元形式) = true
    out.append(1 if down else 0)        # m_flg_unk03: 1110=false / 1120=true
    out.append(0)                       # BBS クエリでない
    out += struct.pack("<i", serial)
    out.append(0)                       # 検索文字列長 0
    out += b"\x00" * 11                 # 検索者 ID ""
    out.append(1)                       # 経路ホスト数 1 (自ノード)
    out += bytes(self_ip[:4])
    out += struct.pack("<H", self_port)
    out += struct.pack("<H", 0)         # キーヘッダ数 0
    assert len(out) == 30
    return bytes(out)
