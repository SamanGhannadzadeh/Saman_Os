#!/usr/bin/env python3
"""Create a single-file .torrent for an ISO (pure stdlib).

Usage: make-torrent.py <file> [comment]
Writes <file>.torrent next to the file and prints the magnet link.
Public trackers only; the file itself is also seeded later via the
GitHub Release asset + the archive.org item (both carry the same
SHA-256, printed by the caller into SHA256SUMS.txt).
"""
import hashlib
import os
import sys
import urllib.parse

TRACKERS = [
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.stealth.si:80/announce",
    "udp://tracker.torrent.eu.org:451/announce",
    "udp://exodus.desync.com:6969/announce",
    "https://tracker.opentrackr.org:443/announce",
]
PIECE = 2 * 1024 * 1024  # 2 MiB


def benc(x):
    if isinstance(x, int):
        return b"i" + str(x).encode() + b"e"
    if isinstance(x, bytes):
        return str(len(x)).encode() + b":" + x
    if isinstance(x, str):
        return benc(x.encode())
    if isinstance(x, list):
        return b"l" + b"".join(benc(i) for i in x) + b"e"
    if isinstance(x, dict):
        out = b"d"
        for k in sorted(x, key=lambda k: k if isinstance(k, bytes)
                        else k.encode()):
            out += benc(k) + benc(x[k])
        return out + b"e"
    raise TypeError(type(x))


def main():
    path = sys.argv[1]
    comment = sys.argv[2] if len(sys.argv) > 2 else "Saman OS"
    size = os.path.getsize(path)
    pieces = b""
    with open(path, "rb") as f:
        while True:
            chunk = f.read(PIECE)
            if not chunk:
                break
            pieces += hashlib.sha1(chunk).digest()
    info = {
        "name": os.path.basename(path),
        "piece length": PIECE,
        "length": size,
        "pieces": pieces,
    }
    torrent = {
        "announce": TRACKERS[0],
        "announce-list": [[t] for t in TRACKERS],
        "comment": comment,
        "created by": "Saman OS build tools",
        "info": info,
    }
    data = benc(torrent)
    out = path + ".torrent"
    with open(out, "wb") as f:
        f.write(data)
    infohash = hashlib.sha1(benc(info)).hexdigest()
    magnet = "magnet:?xt=urn:btih:%s&dn=%s%s" % (
        infohash,
        urllib.parse.quote(os.path.basename(path)),
        "".join("&tr=" + urllib.parse.quote(t) for t in TRACKERS))
    print("torrent:", out)
    print("magnet:", magnet)


if __name__ == "__main__":
    main()
