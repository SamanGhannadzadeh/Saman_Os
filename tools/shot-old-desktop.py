#!/usr/bin/env python3
"""Boot the last from-scratch Saman OS ISO in QEMU and screendump its
graphical desktop (the design being ported to the Linux edition)."""
import socket, subprocess, sys, time, os

ISO = os.path.expanduser("~/workspace/saman-os/build/saman-os.iso")
MON = "/tmp/saman-mon.sock"
PPM = "/tmp/saman-shot.ppm"
for p in (MON, PPM):
    if os.path.exists(p):
        os.unlink(p)

q = subprocess.Popen([
    "qemu-system-x86_64", "-m", "256",
    "-cdrom", ISO, "-boot", "d",
    "-display", "none",
    "-monitor", f"unix:{MON},server,nowait",
    "-serial", "file:/tmp/saman-serial.log",
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

try:
    # wait for the monitor socket, then give the OS time to reach the desktop
    for _ in range(50):
        if os.path.exists(MON):
            break
        time.sleep(0.2)
    time.sleep(18)
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(MON)
    s.settimeout(5)
    try:
        s.recv(4096)
    except socket.timeout:
        pass
    s.sendall(f"screendump {PPM}\n".encode())
    time.sleep(2)
    s.sendall(b"quit\n")
    s.close()
finally:
    try:
        q.wait(timeout=10)
    except subprocess.TimeoutExpired:
        q.kill()

print("PPM exists:", os.path.exists(PPM), os.path.getsize(PPM) if os.path.exists(PPM) else 0)
