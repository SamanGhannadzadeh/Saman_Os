#!/bin/bash
# Visible product boot test: loader initramfs + disk image in QEMU.
# Waits for the root switch and the graphical target on the serial
# log, takes screendumps, and leaves the guest running until the
# wait budget ends (the caller kills QEMU).
cd ~/workspace/saman-os-linux || exit 1
rm -f /tmp/product-live.log /tmp/product-shot.ppm /tmp/product-mon.sock
MEM="${SAMAN_QEMU_MEM:-2560}"
~/workspace/tools/qemu-noble/qemu-system-x86_64 -m "$MEM" -smp 2 -vga std \
  -kernel build/vmlinuz -initrd build/product-initrd.img \
  -append "console=ttyS0 console=tty0 panic=-1" \
  -drive file=build/saman-os-disk.img,format=raw,if=virtio \
  -serial file:/tmp/product-live.log \
  -monitor unix:/tmp/product-mon.sock,server,nowait \
  -display none -no-reboot &
QPID=$!
echo "QEMU pid=$QPID mem=${MEM}M, waiting for product boot..."
dump_shot() {
python3 - <<'EOF'
import socket, time
try:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(10)
    s.connect('/tmp/product-mon.sock')
    s.recv(4096)
    s.sendall(b'screendump /tmp/product-shot.ppm\n')
    time.sleep(1)
    s.recv(4096)
    s.close()
    print("screendump ok")
except Exception as e:
    print("screendump FAILED:", e)
EOF
}
SEEN_ROOT=0; SEEN_GRAPH=0
for i in $(seq 1 90); do
  sleep 10
  n=$(wc -l < /tmp/product-live.log 2>/dev/null || echo 0)
  echo "  ...$((i*10))s: $n log lines"
  if [ "$SEEN_ROOT" = 0 ] && grep -q "SAMANOS_ROOT_OK" /tmp/product-live.log 2>/dev/null; then
    echo ">>> ROOT SWITCHED at ~$((i*10))s"; SEEN_ROOT=1
  fi
  if grep -q "SAMANOS_ROOT_FAIL" /tmp/product-live.log 2>/dev/null; then
    echo ">>> ROOT SWITCH FAILED"; break
  fi
  if grep -q "Reached target graphical.target\|graphical interface" /tmp/product-live.log 2>/dev/null; then
    echo ">>> GRAPHICAL TARGET at ~$((i*10))s"; SEEN_GRAPH=1
    sleep 30
    dump_shot
    break
  fi
  kill -0 $QPID 2>/dev/null || { echo "QEMU exited early"; break; }
done
[ "$SEEN_GRAPH" = 0 ] && dump_shot
ls -la /tmp/product-shot.ppm 2>/dev/null || echo "NO PPM FILE"
echo "=== last serial lines ==="
tail -40 /tmp/product-live.log
kill $QPID 2>/dev/null
