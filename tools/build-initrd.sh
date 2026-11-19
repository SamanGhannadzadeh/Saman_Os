#!/bin/bash
# Build the Saman OS (Linux-based) kernel + initramfs from the cached .debs.
set -e
cd "$(dirname "$0")/.."
ROOT="$PWD"

mkdir -p work/kx work/bx build
[ -f work/kx/boot/vmlinuz-7.3.0-10-generic ] || dpkg-deb -x cache/linux-image-unsigned-7.3.0-10-generic_7.3.0-10.10_amd64.deb work/kx
[ -f work/bx/usr/bin/busybox ] || dpkg-deb -x cache/busybox-static_1.36.1-6ubuntu3_amd64.deb work/bx
cp work/kx/boot/vmlinuz-7.3.0-10-generic build/vmlinuz
BB="$ROOT/work/bx/usr/bin/busybox"

# --- assemble initramfs tree ---
rm -rf work/initrd
mkdir -p work/initrd/{bin,sbin,proc,sys,dev,root,etc}
cp "$BB" work/initrd/bin/busybox
cp rootfs/init work/initrd/init
chmod +x work/initrd/init
printf 'Saman OS 1.0 (Linux-based)\nID=samanos\nVERSION_ID=1.0\nKERNEL=7.3.0-10-generic\nBASE=Ubuntu 26.10 (stonking)\n' > work/initrd/etc/saman-release
printf '\n  Saman OS 1.0 - welcome\n\n' > work/initrd/etc/motd
(cd work/initrd && ./bin/busybox --install -s bin >/dev/null 2>&1 || true)
# busybox --install needs to run with target paths; do it via chroot-free trick:
(cd work/initrd/bin && for a in sh mount hostname uname clear poweroff cat ls echo grep; do ln -sf busybox "$a"; done)

# --- pack (newc cpio, gzipped) ---
(cd work/initrd && find . | "$BB" cpio -o -H newc 2>/dev/null) | gzip -9 > build/initrd.img
ls -l build/
echo "BUILD_OK"
