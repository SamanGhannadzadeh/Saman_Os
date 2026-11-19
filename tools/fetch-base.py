#!/usr/bin/env python3
"""Fetch base packages for Saman OS (Linux-based) from the NEWEST stable
Ubuntu release on the mirror (Saman's order: always the latest versions —
a general-purpose distro like Ubuntu). Currently resolves to stonking
(26.10); release + -updates indexes are both read and the newest kernel
wins. Uses urllib (proven route on this VM) + ambient egress proxy env."""
import lzma, os, re, urllib.request

BASE = "http://azure.archive.ubuntu.com/ubuntu"
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "..", "cache")
os.makedirs(CACHE, exist_ok=True)
RELEASES = ["stonking"]  # newest stable on the mirror; tenacious is devel

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "saman-os-fetch/2.0"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()

def stanzas(raw):
    for block in raw.decode("utf-8", "replace").split("\n\n"):
        d, key = {}, None
        for line in block.splitlines():
            if line.startswith(" ") and key:
                d[key] += "\n" + line
            elif ": " in line:
                key, val = line.split(": ", 1)
                d[key] = val
        if d:
            yield d

def vkey(v):
    return [int(x) if x.isdigit() else 0 for x in re.split(r"[^0-9]+", v)]

def main():
    pkgs = []
    for rel in RELEASES:
        for suite in (rel, rel + "-updates"):
            print(f"fetching {suite} main Packages.xz ...", flush=True)
            raw = lzma.decompress(get(f"{BASE}/dists/{suite}/main/binary-amd64/Packages.xz"))
            got = list(stanzas(raw))
            print(f"  {suite}: {len(got)} packages", flush=True)
            pkgs += got

    def pick(pattern):
        cands = [p for p in pkgs if re.fullmatch(pattern, p.get("Package", ""))]
        cands.sort(key=lambda p: vkey(p.get("Version", "")))
        if not cands:
            print(f"NOT FOUND: {pattern}", flush=True)
            return None
        p = cands[-1]
        print(f"{p['Package']} {p['Version']} -> {p['Filename']}", flush=True)
        return p

    targets = [pick(r"linux-image-unsigned-\d+\.\d+\.0-\d+-generic"),
               pick(r"busybox-static")]
    for p in targets:
        if not p:
            continue
        dest = os.path.join(CACHE, os.path.basename(p["Filename"]))
        if os.path.exists(dest) and os.path.getsize(dest) == int(p["Size"]):
            print(f"cached: {dest}", flush=True)
            continue
        print(f"downloading {p['Filename']} ({int(p['Size'])/1e6:.1f} MB) ...", flush=True)
        data = get(f"{BASE}/{p['Filename']}")
        assert len(data) == int(p["Size"]), (len(data), p["Size"])
        with open(dest, "wb") as f:
            f.write(data)
        print(f"saved: {dest}", flush=True)
    print("DONE", flush=True)

if __name__ == "__main__":
    main()
