#!/usr/bin/env python3
"""End-to-end install test (QEMU):
  Phase A: boot the TEST live ISO (serial getty enabled) with a blank
           8 GB virtio disk, log in on the serial console and run
           `saman-install /dev/vda` non-interactively.
  Phase B: boot the installed disk alone under OVMF and check the
           loader root marker + take a desktop screendump.
Transcripts land in work/test-install-*.log; the phase-B screendump
is /tmp/installed-shot.ppm.
"""
import os, socket, subprocess, sys, time

ROOT = os.path.expanduser("~/workspace/saman-os-linux")
QEMU = os.path.expanduser("~/workspace/tools/qemu-noble/qemu-system-x86_64")
DISK = os.path.join(ROOT, "work/test-install-disk.img")
VARS = os.path.join(ROOT, "work/test-ovmf-vars.fd")
SER = "/tmp/inst-ser.sock"
MON = "/tmp/inst-mon.sock"
LOG_A = os.path.join(ROOT, "work/test-install-serial.log")
LOG_B = os.path.join(ROOT, "work/test-installed-boot.log")


def qemu_base():
    return [QEMU, "-m", "2048", "-smp", "2", "-vga", "std",
            "-drive", "if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd",
            "-drive", f"if=pflash,format=raw,file={VARS}",
            "-display", "none", "-no-reboot"]


def monitor(cmd):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(15)
    s.connect(MON)
    s.recv(4096)
    s.sendall((cmd + "\n").encode())
    time.sleep(1)
    s.recv(4096)
    s.close()


class Serial:
    def __init__(self, transcript_path):
        self.buf = b""
        self.tr = open(transcript_path, "wb")
        for _ in range(60):
            try:
                self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.s.connect(SER)
                break
            except OSError:
                time.sleep(1)
        self.s.settimeout(1)

    def read_until(self, needle, timeout):
        end = time.time() + timeout
        while time.time() < end:
            if needle.encode() in self.buf:
                return True
            try:
                data = self.s.recv(4096)
                if data:
                    self.buf += data
                    self.tr.write(data)
                    self.tr.flush()
            except socket.timeout:
                pass
        return needle.encode() in self.buf

    def send(self, text):
        self.s.sendall((text + "\n").encode())
        time.sleep(0.5)


def phase_a():
    print("== phase A: live boot + install ==", flush=True)
    with open(DISK, "wb") as f:
        f.truncate(8 * 1024 * 1024 * 1024)
    if os.path.exists(VARS):
        os.remove(VARS)
    subprocess.run(["cp", "/usr/share/OVMF/OVMF_VARS_4M.fd", VARS], check=True)
    for p in (SER, MON):
        if os.path.exists(p):
            os.remove(p)
    proc = subprocess.Popen(qemu_base() + [
        "-drive", f"file={DISK},format=raw,if=virtio",
        "-cdrom", os.path.join(ROOT, "build/saman-os-live.iso"), "-boot", "d",
        "-serial", f"unix:{SER},server,nowait",
        "-monitor", f"unix:{MON},server,nowait"])
    try:
        ser = Serial(LOG_A)
        if not ser.read_until("SAMANOS_LIVE_OK", 600):
            print("FAIL: live marker not seen"); return False
        print("live root up; waiting for login prompt", flush=True)
        if not ser.read_until("login:", 900):
            print("FAIL: no serial login prompt"); return False
        ser.send("saman")
        # The live session may or may not challenge for a password
        # (observed 2026-11-19: a shell with no Password: prompt at
        # all). Accept either path; diagnose the account in-guest.
        end = time.time() + 60
        state = None
        while time.time() < end:
            if ser.read_until("Password:", 2):
                state = "password"
                break
            if b"saman@samanos" in ser.buf or b"-bash-" in ser.buf:
                state = "shell"
                break
        if state == "password":
            ser.send("saman")
            if not ser.read_until("saman@samanos", 60):
                print("FAIL: login did not reach a shell"); return False
        elif state != "shell":
            print("FAIL: neither password prompt nor shell;",
                  "buffer tail:", ser.buf[-300:]); return False
        print(f"logged in (path: {state}); running installer", flush=True)
        ser.send("passwd -S saman; sudo -n true 2>/dev/null && echo SUDO_NOPASS || echo SUDO_NEEDS_PASS")
        ser.send("echo saman | sudo -S sh -c 'SAMAN_INSTALL_YES=1 saman-install /dev/vda' 2>&1 | tee /tmp/install.log")
        if not ser.read_until("SAMAN_INSTALL_OK", 1500):
            print("FAIL: SAMAN_INSTALL_OK not seen"); return False
        print("installer OK", flush=True)
        ser.send("sync; echo saman | sudo -S poweroff")
        time.sleep(10)
        return True
    finally:
        try:
            monitor("quit")
        except Exception:
            pass
        time.sleep(2)
        proc.terminate()


def phase_b():
    print("== phase B: boot the installed disk (UEFI) ==", flush=True)
    for p in (SER, MON):
        if os.path.exists(p):
            os.remove(p)
    if os.path.exists(LOG_B):
        os.remove(LOG_B)
    proc = subprocess.Popen(qemu_base() + [
        "-drive", f"file={DISK},format=raw,if=virtio", "-boot", "order=c",
        "-serial", f"file:{LOG_B}",
        "-monitor", f"unix:{MON},server,nowait"])
    ok = False
    try:
        for _ in range(90):
            time.sleep(10)
            if os.path.exists(LOG_B):
                data = open(LOG_B, "rb").read()
                if b"SAMANOS_ROOT_OK" in data:
                    print("root marker seen:", [l for l in data.decode(errors="replace").splitlines()
                                                if "SAMANOS_ROOT_OK" in l], flush=True)
                    ok = True
                    break
                if b"SAMANOS_ROOT_FAIL" in data:
                    print("FAIL: loader could not find the root"); break
        if ok:
            print("waiting for the desktop to settle", flush=True)
            time.sleep(240)
            monitor("screendump /tmp/installed-shot.ppm")
            print("screendump taken", flush=True)
        return ok
    finally:
        try:
            monitor("quit")
        except Exception:
            pass
        time.sleep(2)
        proc.terminate()


if __name__ == "__main__":
    a = phase_a()
    b = phase_b() if a else False
    print("INSTALL_TEST:", "PASS" if (a and b) else "FAIL")
    sys.exit(0 if (a and b) else 1)
