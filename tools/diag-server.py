#!/usr/bin/env python3
"""Boot the server ISO, log in on serial, dump service diagnostics."""
import os, socket, subprocess, sys, time

ROOT = os.path.expanduser("~/workspace/saman-os-linux")
QEMU = os.path.expanduser("~/workspace/tools/qemu-noble/qemu-system-x86_64")
SER = "/tmp/diag-ser.sock"
MON = "/tmp/diag-mon.sock"
LOG = os.path.join(ROOT, "work/diag-server.log")

for p in (SER, MON):
    try:
        os.unlink(p)
    except OSError:
        pass

proc = subprocess.Popen([
    QEMU, "-m", "2048", "-smp", "2", "-vga", "std",
    "-cdrom", os.path.join(ROOT, "build/saman-os-server.iso"),
    "-boot", "d", "-display", "none", "-no-reboot",
    "-serial", f"unix:{SER},server,nowait",
    "-monitor", f"unix:{MON},server,nowait",
    "-netdev", "user,id=n0", "-device", "e1000,netdev=n0",
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

tr = open(LOG, "wb")
buf = b""
s = None
for _ in range(60):
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(SER)
        break
    except OSError:
        time.sleep(1)
s.settimeout(1)

def read_until(needles, timeout):
    global buf
    end = time.time() + timeout
    while time.time() < end:
        for n in needles:
            if n.encode() in buf:
                return n
        try:
            d = s.recv(4096)
            if d:
                buf += d
                tr.write(d)
                tr.flush()
        except socket.timeout:
            pass
    return None

def send(line):
    s.sendall((line + "\n").encode())
    time.sleep(0.4)

try:
    hit = read_until(["login:", "-bash-", "saman@samanos"], 420)
    print("login-stage:", hit)
    if hit == "login:":
        send("saman")
        hit2 = read_until(["Password:", "-bash-", "saman@samanos"], 30)
        print("after-user:", hit2)
        if hit2 == "Password:":
            send("saman")
            read_until(["-bash-", "saman@samanos", "Login incorrect"], 30)
    time.sleep(2)
    buf = b""
    send("export PAGER=cat SYSTEMD_PAGER=cat TERM=dumb")
    time.sleep(1)
    send("echo DIAG_BEGIN; systemctl --failed --no-pager --no-legend; echo ---ACT; "
         "systemctl is-active ofogheamn-dns ofogheamn-panel ofogheamn-proxy ofogheamn-wg; echo ---JRN; "
         "journalctl -b --no-pager -u ofogheamn-dns -u ofogheamn-panel -u ofogheamn-proxy -u ssh 2>/dev/null | tail -35; echo ---NET; "
         "ip -brief a; ss -lntu | head -12; echo DIAG_$((6*7))_END")
    ok = read_until(["DIAG_42_END"], 150)
    print("diag:", "OK" if ok else "TIMEOUT")
finally:
    try:
        m = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        m.connect(MON)
        m.recv(4096)
        m.sendall(b"quit\n")
        m.close()
    except OSError:
        pass
    proc.wait(timeout=30)
    tr.close()
print("transcript:", LOG)
