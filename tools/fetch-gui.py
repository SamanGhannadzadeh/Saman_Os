#!/usr/bin/env python3
"""Fetch the Ubuntu stonking (26.10) packages Saman OS (Linux-based) needs for step 2
(graphical desktop): Xorg + fbdev, evdev/libinput, openbox, tint2, xterm,
Persian font + locale support, udev.

Same proven pattern as tools/fetch-base.py: urllib through the ambient
egress proxy, Packages.xz index, dpkg-deb -x extraction (no system apt).
Resolves Depends/Pre-Depends recursively over main + universe.
"""
import io, lzma, os, re, sys, time, urllib.request

BASE = "http://azure.archive.ubuntu.com/ubuntu"
# Saman's order 13 Nov 2026 ~13:07: always use the NEWEST stable release.
# Base is Ubuntu 26.10 "stonking" + kernel 7.3.0-10-generic (checked this run).
DIST = "stonking"
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "..", "cache")
os.makedirs(CACHE, exist_ok=True)

# Explicit top-level targets for the graphical desktop.
TARGETS = [
    "linux-image-unsigned-7.3.0-10-generic",
    "busybox-static",
    "xserver-xorg-core",
    "xserver-xorg-video-fbdev",
    "xserver-xorg-input-evdev",
    "xserver-xorg-input-libinput",
    "xinit",
    "openbox",
    "tint2",
    "feh",
    "xterm",
    "x11-xserver-utils",
    "x11-xkb-utils",
    "xkb-data",
    "fonts-vazirmatn",
    "fonts-dejavu-core",
    "locales",
    "libc-bin",
    "udev",
    "apt",
    "ubuntu-keyring",
]

# Virtual-package preferences (dep name -> real package to prefer).
VIRTUAL_PREF = {
    "awk": "mawk",
    "default-mta": None,          # not needed, drop
    "lsb-base": "lsb-base",
}

def get(url):
    # The egress proxy occasionally answers 502/503/504; retry a few times.
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
    """Yield dep names from a Depends/Pre-Depends field (first alt only)."""
    if not field:
        return
    for group in field.split(","):
        group = group.strip()
        if not group:
            continue
        first = group.split("|")[0].strip()
        name = re.split(r"\s|\(", first)[0].strip()
        name = name.split(":")[0]  # drop :amd64 qualifiers
        if name:
            yield name

def main():
    pkgs = {}       # name -> stanza (highest version)
    provides = {}   # virtual name -> [real names]
    for comp in ("main", "universe"):
        print(f"fetching {DIST} {comp} Packages.xz ...", flush=True)
        raw = lzma.decompress(get(f"{BASE}/dists/{DIST}/{comp}/binary-amd64/Packages.xz"))
        n = 0
        for p in stanzas(raw):
            n += 1
            name = p.get("Package")
            if not name:
                continue
            if name not in pkgs or p.get("Version", "") > pkgs[name].get("Version", ""):
                pkgs[name] = p
            for prov in p.get("Provides", "").split(","):
                prov = prov.strip().split(" ")[0]
                if prov:
                    provides.setdefault(prov, []).append(name)
        print(f"  {comp}: {n} stanzas", flush=True)
    print(f"index ok: {len(pkgs)} packages", flush=True)

    def resolve(name):
        if name in pkgs:
            return pkgs[name]
        if name in VIRTUAL_PREF:
            pref = VIRTUAL_PREF[name]
            if pref is None:
                return None
            return pkgs.get(pref)
        cands = provides.get(name, [])
        if cands:
            # Prefer a non-virtual, already-common provider.
            return pkgs[sorted(cands)[0]]
        return None

    wanted = {}
    missing = []
    queue = list(TARGETS)
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

    print(f"resolved: {len(wanted)} packages", flush=True)
    if missing:
        print(f"missing: {missing}", flush=True)

    total = 0
    for name in sorted(wanted):
        p = wanted[name]
        dest = os.path.join(CACHE, os.path.basename(p["Filename"]))
        size = int(p["Size"])
        total += size
        if os.path.exists(dest) and os.path.getsize(dest) == size:
            print(f"cached: {name} {p['Version']}", flush=True)
            continue
        print(f"downloading {p['Filename']} ({size/1e6:.1f} MB) ...", flush=True)
        data = get(f"{BASE}/{p['Filename']}")
        assert len(data) == size, (len(data), size)
        with open(dest, "wb") as f:
            f.write(data)
        print(f"saved: {dest}", flush=True)
    print(f"TOTAL download size: {total/1e6:.1f} MB", flush=True)
    with open(os.path.join(CACHE, "gui-packages.txt"), "w") as f:
        for name in sorted(wanted):
            f.write(f"{name} {wanted[name]['Version']}\n")
    print("DONE", flush=True)

if __name__ == "__main__":
    main()
