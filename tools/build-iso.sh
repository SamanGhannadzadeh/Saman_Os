#!/bin/bash
# Build the Saman OS live ISO (step 3): the product rootfs packed as
# a squashfs on a hybrid ISO (GRUB for BIOS + UEFI via grub-mkrescue),
# booted by the product loader in live mode (boot=live).
set -e
umask 022
cd "$(dirname "$0")/.."
ROOT="$PWD"

[ -d work/disk-rootfs ] || { echo "run tools/build-product.sh first"; exit 1; }

# Fresh loader initrd (now with the live-mode module closure).
python3 tools/make-loader.py

STAGE=work/iso-staging
rm -rf "$STAGE"
mkdir -p "$STAGE/casper" "$STAGE/boot/grub"

echo "packing squashfs (product rootfs -> casper/filesystem.squashfs)..."
mksquashfs work/disk-rootfs "$STAGE/casper/filesystem.squashfs" \
  -comp gzip -noappend -no-progress -quiet
cp build/vmlinuz "$STAGE/casper/vmlinuz"
cp build/product-initrd.img "$STAGE/casper/initrd.img"
du -sh "$STAGE/casper/filesystem.squashfs" | awk '{print "squashfs: " $1}'

cat > "$STAGE/boot/grub/grub.cfg" <<'EOF'
set timeout=5
set default=0

menuentry "Saman OS - Live" {
    linux /casper/vmlinuz boot=live console=tty0 console=ttyS0 quiet splash
    initrd /casper/initrd.img
}
menuentry "Saman OS - Live (safe graphics)" {
    linux /casper/vmlinuz boot=live console=tty0 console=ttyS0 nomodeset
    initrd /casper/initrd.img
}
EOF

mkdir -p build
grub-mkrescue -o build/saman-os-live.iso "$STAGE" 2>&1 | tail -2
ls -la build/saman-os-live.iso
python3 -c "import os; print(f'ISO size: {os.path.getsize(\"build/saman-os-live.iso\")/1e9:.3f} GB')"
echo "BUILD_ISO_OK"
