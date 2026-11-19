#!/bin/bash
# Assemble a PROPERLY bootable hybrid ISO from work/iso-staging.
#
# Why this exists (2026-11-19): grub-mkrescue from the extracted
# iso-root tool tree silently produces ISOs with NO El Torito boot
# record at all (verified byte-level: sector 17 empty, no boot
# images) — the 22:18 and 23:0x builds were both unbootable.
# This script builds the boot images by hand with grub-mkimage
# and lays them down with xorrisofs, then VERIFIES the result:
# it fails loudly unless the El Torito record is present.
set -e
umask 022
cd "$(dirname "$0")/.."
ROOT="$PWD"
ISO_ROOT="${ISO_ROOT:-$HOME/workspace/tools/iso-root}"
export PATH="$ISO_ROOT/usr/bin:$PATH"
export LD_LIBRARY_PATH="$ISO_ROOT/usr/lib/x86_64-linux-gnu"
G="$ISO_ROOT/usr/lib/grub"
STAGE=work/iso-staging
OUT="${1:-build/saman-os-live.iso}"

[ -f "$STAGE/casper/filesystem.squashfs" ] || {
  echo "staging tree missing — run tools/build-iso.sh packing first"
  exit 1; }

# GRUB module trees ride inside the ISO (both GRUBs load their
# .mod files from /boot/grub at runtime).
mkdir -p "$STAGE/boot/grub/i386-pc" "$STAGE/boot/grub/x86_64-efi"
cp "$G/i386-pc/"*.mod "$G/i386-pc/"*.lst \
   "$STAGE/boot/grub/i386-pc/" 2>/dev/null || true
cp "$G/x86_64-efi/"*.mod "$G/x86_64-efi/"*.lst \
   "$STAGE/boot/grub/x86_64-efi/" 2>/dev/null || true
[ -f "$ISO_ROOT/usr/share/grub/unicode.pf2" ] && \
  cp "$ISO_ROOT/usr/share/grub/unicode.pf2" "$STAGE/boot/grub/"

# BIOS boot image: cdboot.img + core.img.
grub-mkimage -d "$G/i386-pc" -O i386-pc -o /tmp/saman-core.img \
  -p /boot/grub biosdisk iso9660 part_gpt part_msdos normal \
  configfile linux search search_fs_uuid search_fs_file \
  search_label loopback echo test gfxterm
cat "$G/i386-pc/cdboot.img" /tmp/saman-core.img \
  > "$STAGE/boot/grub/i386-pc/eltorito.img"

# UEFI boot image: BOOTX64.EFI inside a FAT El Torito image.
grub-mkimage -d "$G/x86_64-efi" -O x86_64-efi \
  -o /tmp/BOOTX64.EFI -p /boot/grub part_gpt part_msdos fat \
  iso9660 normal configfile linux search search_fs_uuid \
  search_fs_file search_label loopback echo test all_video gfxterm
rm -f /tmp/saman-efi.img
mformat -i /tmp/saman-efi.img -C -F -T 32768 -h 64 -s 32 ::
mmd -i /tmp/saman-efi.img ::/EFI ::/EFI/BOOT
mcopy -i /tmp/saman-efi.img /tmp/BOOTX64.EFI ::/EFI/BOOT/BOOTX64.EFI
cp /tmp/saman-efi.img "$STAGE/boot/grub/efi.img"

mkdir -p "$(dirname "$OUT")"
xorrisofs -o "$OUT" -V SAMANOS_LIVE \
  -isohybrid-mbr "$G/i386-pc/boot_hybrid.img" \
  -b boot/grub/i386-pc/eltorito.img -no-emul-boot \
  -boot-load-size 4 -boot-info-table --grub2-boot-info \
  -eltorito-alt-boot -e boot/grub/efi.img -no-emul-boot \
  -isohybrid-gpt-basdat \
  "$STAGE"

# Verification gate: the El Torito boot record MUST be there.
python3 - "$OUT" <<'EOF'
import sys
d = open(sys.argv[1], "rb")
d.seek(34816)
brvd = d.read(2048)
ok = brvd[0] == 0 and brvd[7:30] == b"EL TORITO SPECIFICATION"
print("El Torito boot record:", "PRESENT" if ok else "MISSING")
sys.exit(0 if ok else 1)
EOF
python3 -c "import os,sys; print(f'ISO size: {os.path.getsize(sys.argv[1])/1e9:.3f} GB')" "$OUT"
echo "BOOTABLE_ISO_OK"
