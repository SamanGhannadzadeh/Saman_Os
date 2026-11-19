#!/bin/bash
# Visible live-ISO boot test in QEMU. Default: BIOS boot from the
# ISO. SAMAN_UEFI=1 boots via OVMF (pflash) instead. Waits for the
# live marker + graphical target on the serial log, screendumps.
cd ~/workspace/saman-os-linux || exit 1
rm -f /tmp/iso-live.log /tmp/iso-shot.ppm /tmp/iso-mon.sock
MEM="${SAMAN_QEMU_MEM:-2048}"
UEFI_ARGS=()
BOOTDEV="d"
if [ "${SAMAN_UEFI:-0}" = "1" ]; then
  cp /usr/share/OVMF/OVMF_VARS_4M.fd /tmp/ovmf-vars.fd
  UEFI_ARGS=(-drive "if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd"
             -drive "if=pflash,format=raw,file=/tmp/ovmf-vars.fd")
  echo "UEFI (OVMF) boot"
fi
~/workspace/tools/qemu-noble/qemu-system-x86_64 -m "$MEM" -smp 2 -vga std \
  "${UEFI_ARGS[@]}" \
  -cdrom build/saman-os-live.iso -boot "$BOOTDEV" \
  -serial file:/tmp/iso-live.log \
  -monitor unix:/tmp/iso-mon.sock,server,nowait \
  -display none -no-reboot &
QPID=$!
echo "QEMU pid=$QPID mem=${MEM}M, waiting for live boot..."
dump_shot() {
python3 - <<'EOF'
import socket, time
try:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(10)
    s.connect('/tmp/iso-mon.sock')
    s.recv(4096)
    s.sendall(b'screendump /tmp/iso-shot.ppm\n')
    time.sleep(1)
    s.recv(4096)
    s.close()
    print("screendump ok")
except Exception as e:
    print("screendump FAILED:", e)
EOF
}
SEEN_LIVE=0; SEEN_GRAPH=0
for i in $(seq 1 90); do
  sleep 10
  n=$(wc -l < /tmp/iso-live.log 2>/dev/null || echo 0)
  echo "  ...$((i*10))s: $n log lines"
  if [ "$SEEN_LIVE" = 0 ] && grep -q "SAMANOS_LIVE_OK" /tmp/iso-live.log 2>/dev/null; then
    echo ">>> LIVE ROOT READY at ~$((i*10))s"; SEEN_LIVE=1
  fi
  if grep -q "SAMANOS_LIVE_FAIL" /tmp/iso-live.log 2>/dev/null; then
    echo ">>> LIVE BOOT FAILED"; break
  fi
  if grep -q "Reached target graphical.target\|graphical interface" /tmp/iso-live.log 2>/dev/null; then
    echo ">>> GRAPHICAL TARGET at ~$((i*10))s"; SEEN_GRAPH=1
    sleep 30
    dump_shot
    break
  fi
  kill -0 $QPID 2>/dev/null || { echo "QEMU exited early"; break; }
done
[ "$SEEN_GRAPH" = 0 ] && dump_shot
ls -la /tmp/iso-shot.ppm 2>/dev/null || echo "NO PPM FILE"
echo "=== last serial lines ==="
tail -40 /tmp/iso-live.log
kill $QPID 2>/dev/null
