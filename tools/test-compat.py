#!/usr/bin/env python3
"""Hardware/graphics compatibility matrix for the Saman OS live ISO.

Boots the ISO under a set of QEMU machine profiles (graphics adapters,
machine types, low resources, storage and network variants) and checks
that each reaches the live desktop marker on the serial console and
paints a non-blank screen.

Usage: python3 tools/test-compat.py [iso] [profile,profile,...]
Results land in work/compat-results.md; serial logs in work/compat-<p>.log
"""
import os, socket, subprocess, sys, time

ROOT = os.path.expanduser("~/workspace/saman-os-linux")
QEMU = os.path.expanduser("~/workspace/tools/qemu-noble/qemu-system-x86_64")
ISO = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build/saman-os-live.iso")

PROFILES = {
    "gfx-std":     ["-vga", "std"],
    "gfx-virtio":  ["-device", "virtio-vga"],
    "gfx-qxl":     ["-device", "qxl-vga"],
    "gfx-vmware":  ["-device", "vmware-svga"],
    "gfx-bochs":   ["-device", "bochs-display"],
    "hw-q35":      ["-machine", "q35", "-vga", "std"],
    "hw-low":      ["-m", "1024", "-smp", "1", "-vga", "std"],
    "hw-sata":     ["-machine", "q35", "-vga", "std",
                    "-device", "ahci,id=ahci0", "-device", "ide-cd,drive=cd0,bus=ahci0.0",
                    "-drive", "id=cd0,if=none,media=cdrom,readonly=on"],
    "net-virtio":  ["-vga", "std", "-device", "virtio-net-pci,netdev=n0"],
    "net-rtl8139": ["-vga", "std", "-device", "rtl8139,netdev=n0"],
}
ORDER = list(PROFILES)
if len(sys.argv) > 2:
    ORDER = [p for p in sys.argv[2].split(",") if p in PROFILES]


def run_profile(name, extra):
    ser = f"/tmp/compat-{name}-ser.sock"
    mon = f"/tmp/compat-{name}-mon.sock"
    for p in (ser, mon):
        try:
            os.unlink(p)
        except OSError:
            pass
    args = [QEMU, "-m", "2048", "-smp", "2", "-boot", "d",
            "-display", "none", "-no-reboot",
            "-serial", f"unix:{ser},server,nowait",
            "-monitor", f"unix:{mon},server,nowait",
            "-netdev", "user,id=n0"]
    if name == "hw-sata":
        args += extra  # carries its own cdrom drive wiring
    else:
        args += ["-cdrom", ISO]
        args += extra if extra else ["-vga", "std"]
        if "netdev=n0" not in " ".join(extra):
            args += ["-device", "e1000,netdev=n0"]
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    logpath = os.path.join(ROOT, f"work/compat-{name}.log")
    tr = open(logpath, "wb")
    buf = b""
    ok = False
    s = None
    for _ in range(60):
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(ser)
            break
        except OSError:
            time.sleep(1)
    if s:
        s.settimeout(1)
        end = time.time() + 420
        while time.time() < end:
            if b"SAMANOS_LIVE_OK" in buf:
                ok = True
                break
            try:
                d = s.recv(4096)
                if d:
                    buf += d
                    tr.write(d)
                    tr.flush()
            except socket.timeout:
                pass
    shot = ""
    colors = 0
    if ok:
        try:
            m = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            m.connect(mon)
            m.recv(4096)
            shot = f"/tmp/compat-{name}.ppm"
            m.sendall(f"screendump {shot}\n".encode())
            time.sleep(2)
            m.close()
            with open(shot, "rb") as f:
                data = f.read()
            # crude "desktop painted" check: many distinct byte values
            colors = len(set(data[1000:200000]))
        except OSError:
            pass
    try:
        m = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        m.connect(mon)
        m.recv(4096)
        m.sendall(b"quit\n")
        m.close()
    except OSError:
        pass
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()
    tr.close()
    return ok, colors, logpath


def main():
    rows = []
    for name in ORDER:
        print(f"== {name} ...", flush=True)
        ok, colors, logpath = run_profile(name, PROFILES[name])
        verdict = "PASS" if (ok and colors > 40) else ("BOOT-OK/SCREEN?" if ok else "FAIL")
        print(f"   {verdict} (live_ok={ok}, screen_colors={colors})")
        rows.append((name, verdict, ok, colors))
    out = ["# Compatibility matrix — " + time.strftime("%Y-%m-%d %H:%M"),
           f"ISO: `{ISO}`", "",
           "| profile | result | live marker | screen colors |",
           "|---|---|---|---|"]
    for name, verdict, ok, colors in rows:
        out.append(f"| {name} | {verdict} | {'yes' if ok else 'no'} | {colors} |")
    with open(os.path.join(ROOT, "work/compat-results.md"), "w") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
