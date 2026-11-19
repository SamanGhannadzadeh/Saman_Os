#!/usr/bin/env python3
"""Fetch the kernel module packages for 7.3.0-10-generic.

The -10 kernel is an stonking-updates kernel: its linux-image came
from the updates pocket, and linux-modules / linux-modules-extra
exist only there (the release pocket tops out at 7.3.0-9). Same
pattern as tools/fetch-gui.py, pointed at stonking-updates.
"""
import lzma, os, re, time, urllib.request

BASE = "http://azure.archive.ubuntu.com/ubuntu"
DIST = "stonking-updates"
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "..", "cache")
TARGETS = [
    "linux-modules-7.3.0-10-generic",
    # 26.10 has no linux-modules-extra; supplements are split out:
    "linux-main-modules-iwlwifi-7.3.0-10-generic",
]

def get(url):
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "saman-os-fetch/1.0"})
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except Exception as e:
            last = e
            print(f"  retry {attempt+1}/5: {url.split('/')[-1]} ({e})", flush=True)
            time.sleep(5 * (attempt + 1))
    raise last

def stanzas(raw):
    text = raw.decode("utf-8", "replace")
    for block in text.split("\n\n"):
        d = {}
        key = None
        for line in block.splitlines():
            if line.startswith(" ") and key:
                d[key] += "\n" + line
            elif ": " in line:
                key, val = line.split(": ", 1)
                d[key] = val
        if d:
            yield d

def parse_dep_field(field):
    if not field:
        return
    for group in field.split(","):
        group = group.strip()
        if not group:
            continue
        first = group.split("|")[0].strip()
        name = re.split(r"\s|\(", first)[0].strip()
        name = name.split(":")[0]
        if name:
            yield name

def main():
    pkgs = {}
    provides = {}
    for comp in ("main", "universe"):
        print(f"fetching {DIST} {comp} Packages.xz ...", flush=True)
        raw = lzma.decompress(get(f"{BASE}/dists/{DIST}/{comp}/binary-amd64/Packages.xz"))
        for p in stanzas(raw):
            name = p.get("Package")
            if not name:
                continue
            if name not in pkgs or p.get("Version", "") > pkgs[name].get("Version", ""):
                pkgs[name] = p
            for prov in p.get("Provides", "").split(","):
                prov = prov.strip().split(" ")[0]
                if prov:
                    provides.setdefault(prov, []).append(name)
    print(f"index ok: {len(pkgs)} packages", flush=True)

    def resolve(name):
        if name in pkgs:
            return pkgs[name]
        cands = provides.get(name, [])
        if cands:
            return pkgs[sorted(cands)[0]]
        return None

    wanted, missing, queue = {}, [], list(TARGETS)
    while queue:
        name = queue.pop(0)
        if name in wanted:
            continue
        p = resolve(name)
        if p is None:
            missing.append(name)
            print(f"NOT FOUND: {name}", flush=True)
            continue
        wanted[p["Package"]] = p
        for field in (p.get("Pre-Depends", ""), p.get("Depends", "")):
            for dep in parse_dep_field(field):
                if dep not in wanted:
                    queue.append(dep)
    print(f"resolved: {len(wanted)} packages; missing: {missing}", flush=True)
    for name in sorted(wanted):
        p = wanted[name]
        dest = os.path.join(CACHE, os.path.basename(p["Filename"]))
        size = int(p["Size"])
        if os.path.exists(dest) and os.path.getsize(dest) == size:
            print(f"cached: {name}", flush=True)
            continue
        print(f"downloading {p['Filename']} ({size/1e6:.1f} MB) ...", flush=True)
        data = get(f"{BASE}/{p['Filename']}")
        assert len(data) == size
        with open(dest, "wb") as f:
            f.write(data)
    with open(os.path.join(CACHE, "modules-packages.txt"), "w") as f:
        for name in sorted(wanted):
            f.write(f"{name} {wanted[name]['Version']}\n")
    print("DONE", flush=True)

if __name__ == "__main__":
    main()
