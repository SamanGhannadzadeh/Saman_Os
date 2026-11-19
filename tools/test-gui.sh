#!/bin/bash
# Boot Saman OS 2.0 (GUI) in QEMU, wait for SAMANOS_GUI_OK on the serial
# log, take a framebuffer screenshot, report. Gate for step 2.
set -u
cd "$(dirname "$0")/.."
LOG=docs/BOOT-LOG-linux-2.0.txt
SHOT=/tmp/samanos-shot.png
MON=/tmp/samanos-mon.sock
rm -f "$LOG" "$SHOT" "$MON"
qemu-system-x86_64 \
  -kernel build/vmlinuz -initrd build/initrd.img \
  -append "console=ttyS0 saman_test=1 panic=-1 video=1024x768" \
  -m 1536 -smp 2 -vga std -display none \
  -monitor "unix:$MON,server,nowait" \
  -serial "file:$LOG" \
  -pidfile /tmp/samanos-qemu.pid -daemonize
QPID=$(cat /tmp/samanos-qemu.pid)
echo "qemu pid=$QPID"
# poll the serial log for the gate marker (max 240s)
OK=""
for i in $(seq 1 120); do
  sleep 2
  if grep -q SAMANOS_GUI_OK "$LOG" 2>/dev/null; then OK=1; break; fi
  if grep -q SAMANOS_GUI_FAIL "$LOG" 2>/dev/null; then OK=0; break; fi
  kill -0 "$QPID" 2>/dev/null || { echo "QEMU exited early"; break; }
done
if [ "$OK" = "1" ]; then
  echo "GATE MARKER: SAMANOS_GUI_OK"
  sleep 1
  printf 'screendump %s png\n' "$SHOT" | socat - "unix-connect:$MON" >/dev/null 2>&1
  sleep 1
  ls -lh "$SHOT" 2>/dev/null || echo "SCREENSHOT FAILED"
elif [ "$OK" = "0" ]; then
  echo "GATE MARKER: SAMANOS_GUI_FAIL"
else
  echo "TIMEOUT/NO MARKER"
fi
# wait for the guest to power off by itself (init powers off 8s after OK)
for i in $(seq 1 15); do kill -0 "$QPID" 2>/dev/null || break; sleep 2; done
if kill -0 "$QPID" 2>/dev/null; then kill "$QPID" 2>/dev/null; echo "killed lingering qemu"; else echo "qemu exited cleanly"; fi
grep -E "SAMANOS_GUI|kernel=|fb0|keyboard=" "$LOG" | tail -5
echo "serial log: $LOG"
echo "screenshot: $SHOT"
