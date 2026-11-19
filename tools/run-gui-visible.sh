#!/bin/bash
# Visible GUI boot test for Saman OS (Linux edition).
# Boots build/vmlinuz + build/initrd.img in QEMU, serial log to
# /tmp/gui-live.log, waits for SAMANOS_GUI_OK, takes a screendump to
# /tmp/gui-shot.ppm, then lets the guest power itself off (test mode).
cd ~/workspace/saman-os-linux || exit 1
rm -f /tmp/gui-live.log /tmp/gui-shot.ppm /tmp/gui-mon.sock
~/workspace/tools/qemu-noble/qemu-system-x86_64 -m 1024 -smp 1 -vga std \
  -kernel build/vmlinuz -initrd build/initrd.img \
  -append "console=ttyS0 saman_test=1 panic=-1 video=1024x768" \
  -serial file:/tmp/gui-live.log \
  -monitor unix:/tmp/gui-mon.sock,server,nowait \
  -display none -no-reboot &
QPID=$!
echo "QEMU pid=$QPID, waiting for GUI marker..."
for i in $(seq 1 24); do
  sleep 5
  n=$(wc -l < /tmp/gui-live.log 2>/dev/null || echo 0)
  echo "  ...$((i*5))s: $n log lines so far"
  if grep -q "SAMANOS_GUI_OK\|SAMANOS_GUI_FAIL\|Kernel panic" /tmp/gui-live.log 2>/dev/null; then break; fi
  kill -0 $QPID 2>/dev/null || break
done
if grep -q "SAMANOS_GUI_OK" /tmp/gui-live.log; then echo ">>> SAMANOS_GUI_OK after ~$((i*5))s"; fi
if grep -q "SAMANOS_GUI_FAIL" /tmp/gui-live.log; then echo ">>> SAMANOS_GUI_FAIL"; fi
# let the session settle, then screendump through the QEMU monitor
sleep 8
python3 - <<'EOF'
import socket
try:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(10)
    s.connect('/tmp/gui-mon.sock')
    s.recv(4096)
    s.sendall(b'screendump /tmp/gui-shot.ppm\n')
    s.recv(4096)
    s.close()
    print("screendump done")
except Exception as e:
    print("screendump FAILED:", e)
EOF
# guest powers itself off in test mode; wait for QEMU to exit
for i in $(seq 1 12); do kill -0 $QPID 2>/dev/null || break; sleep 5; done
kill $QPID 2>/dev/null
echo "=== last serial lines ==="
tail -60 /tmp/gui-live.log
