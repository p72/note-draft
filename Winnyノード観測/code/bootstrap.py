# -*- coding: utf-8 -*-
"""Winny observation bootstrap (Windows package).

1. Fetch a fresh Noderef.txt from winny.4th.jp (fallback: bundled 2022 list).
2. Decode node strings, skip private IPs, try candidates in order.
3. On the first successful handshake, observe node introductions and
   write everything to result.txt next to this script.
Observation only: this client never sends or receives file content.
"""
import ipaddress
import os
import socket
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
socket.setdefaulttimeout(8)

from winny_codec import decode_node_string
from winny_client import WinnyConnection

HERE = os.path.dirname(os.path.abspath(__file__))
NODEREF_URLS = [
    "http://winny.4th.jp/Noderef.txt",
    "https://winny.4th.jp/Noderef.txt",
]
MAX_TRIES = 40
OBSERVE_SECONDS = 30


def log(msg):
    print(msg, flush=True)


def fetch_noderef():
    for url in NODEREF_URLS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = r.read()
            text = data.decode("utf-8", "replace")
            if "@" in text:
                log(f"fetched fresh Noderef from {url} ({len(text)} bytes)")
                return text, url
        except Exception as e:
            log(f"fetch failed {url}: {e}")
    path = os.path.join(HERE, "noderef_fallback.txt")
    if not os.path.exists(path):
        raise SystemExit(
            "Noderef fetch failed and noderef_fallback.txt not found. "
            "Place a Noderef.txt (node strings) next to this script.")
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    log("using bundled fallback Noderef (2022 snapshot; most entries likely dead)")
    return text, "fallback"


def candidates(text):
    seen = set()
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        host = port = None
        if line.startswith("@"):
            try:
                plain = decode_node_string(line).decode("ascii", "replace")
            except Exception:
                continue
            parts = plain.split(":")
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


def main():
    lines = []

    def record(msg):
        log(msg)
        lines.append(msg)

    text, source = fetch_noderef()
    cands = candidates(text)
    extra_path = os.path.join(HERE, "noderef_extra.txt")
    if os.path.exists(extra_path):
        with open(extra_path, encoding="utf-8", errors="replace") as f:
            extra = candidates(f.read())
        if extra:
            seen = set(cands)
            front = [c for c in extra if c not in seen]
            cands = front + cands
            record(f"extra candidates from noderef_extra.txt: {len(front)} (tried first)")
    record(f"noderef source: {source}, public candidates: {len(cands)}")
    tried = 0
    for host, port in cands:
        if tried >= MAX_TRIES:
            break
        tried += 1
        record(f"--- try {tried}: {host}:{port}")
        conn = None
        try:
            conn = WinnyConnection(host, port, log=lambda m: record("[c] " + m))
            conn.connect()
            conn.run(duration=3)
            if conn.peer_node is not None:
                record(f"SUCCESS handshake with {host}:{port}")
                record(f"peer node: {conn.peer_node!r}")
                record(f"observing {OBSERVE_SECONDS}s for introductions...")
                conn.run(duration=OBSERVE_SECONDS)
                record(f"introduced nodes: {len(conn.nodes)}")
                for n in conn.nodes:
                    record(f"  node: {n!r}")
                break
            else:
                record("no valid Winny hello (not a Winny node / dead)")
        except Exception as e:
            record(f"failed: {type(e).__name__}: {e}")
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
    else:
        record("no candidate completed the handshake")
    out = os.path.join(HERE, "result.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    log(f"saved: {out}")


if __name__ == "__main__":
    main()
