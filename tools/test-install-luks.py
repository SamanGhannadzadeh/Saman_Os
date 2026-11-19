#!/usr/bin/env python3
"""Encrypted (LUKS2) install test: same skeleton as test-install.py,
but Phase A installs with SAMAN_ENCRYPT=1 + a test passphrase, and
Phase B boots the disk, answers the loader's passphrase prompt over
the serial console (one wrong try first, then the right one) and
expects SAMANOS_ROOT_OK for /dev/mapper/samanos-root."""
import os, socket, subprocess, sys, time

ROOT = os.path.expanduser("~/workspace/saman-os-linux")
QEMU = os.path.expanduser("~/workspace/tools/qemu-noble/qemu-system-x86_64")
DISK = os.path.join(ROOT, "work/test-luks-disk.img")
VARS = os.path.join(ROOT, "work/test-luks-vars.fd")
SER = "/tmp/luks-ser.sock"
MON = "/tmp/luks-mon.sock"
LOG_A = os.path.join(ROOT, "work/test-luks-serial.log")
LOG_B = os.path.join(ROOT, "work/test-luks-boot.log")
PASS = "saman-luks-test"


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
    print("== phase A: live boot + LUKS install ==", flush=True)
    with open(DISK, "wb") as f:
        f.truncate(10 * 1024 * 1024 * 1024)
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
        if not ser.read_until("login:", 900):
            print("FAIL: no serial login prompt"); return False
        ser.send("saman")
        end = time.time() + 60
        state = None
        while time.time() < end:
            if ser.read_until("Password:", 2):
                state = "password"; break
            if b"saman@samanos" in ser.buf or b"-bash-" in ser.buf:
                state = "shell"; break
        if state == "password":
            ser.send("saman")
            if not ser.read_until("saman@samanos", 60):
                print("FAIL: login did not reach a shell"); return False
        elif state != "shell":
            print("FAIL: no shell"); return False
        print("logged in; running encrypted installer", flush=True)
        ser.send("echo saman | sudo -S sh -c 'SAMAN_INSTALL_YES=1 SAMAN_ENCRYPT=1 "
                 f"SAMAN_LUKS_PASSPHRASE={PASS} saman-install /dev/vda' 2>&1 | tee /tmp/install-luks.log")
        if not ser.read_until("SAMAN_INSTALL_OK", 1800):
            print("FAIL: SAMAN_INSTALL_OK not seen"); return False
        print("encrypted installer OK", flush=True)
        ser.send("sync; echo saman | sudo -S poweroff")
        time.sleep(10)
        return True
    finally:
        try: monitor("quit")
        except Exception: pass
        time.sleep(2)
        proc.terminate()


def phase_b():
    print("== phase B: boot encrypted disk, unlock over serial ==", flush=True)
    for p in (SER, MON):
        if os.path.exists(p):
            os.remove(p)
    proc = subprocess.Popen(qemu_base() + [
        "-drive", f"file={DISK},format=raw,if=virtio", "-boot", "order=c",
        "-serial", f"unix:{SER},server,nowait",
        "-monitor", f"unix:{MON},server,nowait"])
    try:
        ser = Serial(LOG_B)
        if not ser.read_until("enter passphrase", 900):
            print("FAIL: no passphrase prompt from the loader"); return False
        print("passphrase prompt seen; sending a WRONG one first", flush=True)
        ser.send("wrong-pass-123")
        time.sleep(8)
        # loader retries (up to 3): a fresh prompt appears
        ser.buf = b""
        if not ser.read_until("enter passphrase", 120):
            print("FAIL: no retry prompt after wrong passphrase"); return False
        print("retry prompt seen; sending the correct passphrase", flush=True)
        ser.send(PASS)
        if not ser.read_until("SAMANOS_ROOT_OK dev=/dev/mapper/samanos-root", 600):
            print("FAIL: SAMANOS_ROOT_OK for the mapper not seen"); return False
        print("LUKS unlock + root OK", flush=True)
        time.sleep(120)
        return True
    finally:
        try: monitor("quit")
        except Exception: pass
        time.sleep(2)
        proc.terminate()


if __name__ == "__main__":
    a = phase_a()
    b = phase_b() if a else False
    print("LUKS_INSTALL_TEST:", "PASS" if (a and b) else "FAIL")
    sys.exit(0 if (a and b) else 1)
