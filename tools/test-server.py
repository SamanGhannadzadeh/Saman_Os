#!/usr/bin/env python3
"""Saman OS Server edition live test.

Boots build/saman-os-server.iso in QEMU (BIOS) with user networking:
  host 18080 -> guest 8080 (panel), host 15354 -> guest 53 (DNS/TCP).
Pass conditions:
  * serial shows SAMANOS_LIVE_OK
  * panel login page answers on http://127.0.0.1:18080/
  * the DNS canary answers NXDOMAIN over the forwarded port
    (proves the preinstalled SmartDNS is live; it is answered
    locally, so it works even in this sandbox with no upstream)
  * console screendump saved for a visual check
"""
import socket
import subprocess
import sys
import time
import urllib.request

ISO = "build/saman-os-server.iso"
SERIAL_LOG = "work/test-server-serial.log"
SHOT = "/tmp/server-shot.ppm"
BUDGET = 600


def main() -> int:
    qemu = subprocess.Popen(
        [
            "/home/hatch/workspace/tools/qemu-noble/qemu-system-x86_64",
            "-m", "2048", "-smp", "2", "-vga", "std",
            "-cdrom", ISO, "-boot", "d",
            "-display", "none",
            "-serial", f"file:{SERIAL_LOG}",
            "-monitor", f"unix:/tmp/server-mon.sock,server,nowait",
            "-netdev", "user,id=n0,hostfwd=tcp::18080-:8080,hostfwd=tcp::15354-:53",
            "-device", "e1000,netdev=n0",
        ],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    ok_live = ok_panel = ok_dns = False
    t0 = time.time()
    try:
        while time.time() - t0 < BUDGET:
            try:
                log = open(SERIAL_LOG, "rb").read().decode("utf-8", "replace")
            except OSError:
                log = ""
            if "SAMANOS_LIVE_OK" in log:
                ok_live = True
            if ok_live and not ok_panel:
                try:
                    with urllib.request.urlopen("http://127.0.0.1:18080/", timeout=4) as r:
                        ok_panel = b"Ofogheamn" in r.read()
                except Exception:
                    pass
            if ok_live and not ok_dns:
                out = subprocess.run(
                    ["dig", "+tcp", "+time=3", "+tries=1", "@127.0.0.1", "-p", "15354",
                     "use-application-dns.net", "A"],
                    capture_output=True, text=True, timeout=10)
                ok_dns = "status: NXDOMAIN" in out.stdout
            if ok_live and ok_panel and ok_dns:
                break
            time.sleep(5)
        # console screenshot via the monitor
        try:
            s = socket.socket(socket.AF_UNIX)
            s.connect("/tmp/server-mon.sock")
            s.sendall(f"screendump {SHOT}\n".encode())
            time.sleep(1)
            s.close()
        except Exception as exc:
            print("screendump failed:", exc)
    finally:
        qemu.terminate()
    print(f"LIVE_OK={ok_live} PANEL={ok_panel} DNS_CANARY_NXDOMAIN={ok_dns}")
    print("SERVER_TEST:", "PASS" if (ok_live and ok_panel and ok_dns) else "FAIL")
    return 0 if (ok_live and ok_panel and ok_dns) else 1


if __name__ == "__main__":
    sys.exit(main())
