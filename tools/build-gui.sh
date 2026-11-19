#!/bin/bash
# Build the Saman OS (Linux-based) graphical rootfs + initramfs.
# Base: Ubuntu 26.10 "stonking", kernel 7.3.0-10-generic (Saman's order:
# always the newest stable release; re-checked at the start of step 2).
# Extracts every .deb listed in cache/gui-packages.txt (written by
# tools/fetch-gui.py) with dpkg-deb -x -- no system apt, no host install.
# Then overlays rootfs/ (init, session, configs) and packs build/initrd.img.
set -e
umask 022
cd "$(dirname "$0")/.."
ROOT="$PWD"

KDEB="cache/linux-image-unsigned-7.3.0-10-generic_7.3.0-10.10_amd64.deb"
[ -f "$KDEB" ] || { echo "MISSING $KDEB -- run tools/fetch-gui.py first"; exit 1; }
[ -f cache/gui-packages.txt ] || { echo "MISSING cache/gui-packages.txt"; exit 1; }

mkdir -p work/rootfs build
# --- extract kernel + busybox for the boot files ---
mkdir -p work/kx73 work/bx73
[ -f work/kx73/boot/vmlinuz-7.3.0-10-generic ] || dpkg-deb -x "$KDEB" work/kx73
BBDEB=$(ls cache/busybox-static_*_amd64.deb | sort -V | tail -1)
[ -f work/bx73/usr/bin/busybox ] || [ -f work/bx73/usr/bin/busybox-static ] || dpkg-deb -x "$BBDEB" work/bx73
# stonking's busybox-static ships /usr/bin/busybox-static (noble: /usr/bin/busybox)
if [ -f work/bx73/usr/bin/busybox ]; then BB="$ROOT/work/bx73/usr/bin/busybox";
elif [ -f work/bx73/usr/bin/busybox-static ]; then BB="$ROOT/work/bx73/usr/bin/busybox-static";
else echo "MISSING busybox binary in $BBDEB"; exit 1; fi
cp work/kx73/boot/vmlinuz-7.3.0-10-generic build/vmlinuz

# --- assemble the real rootfs from the cached .debs ---
rm -rf work/rootfs
mkdir -p work/rootfs
while read -r name ver; do
  deb=$(ls cache/${name}_*.deb 2>/dev/null | sort -V | tail -1)
  if [ -z "$deb" ]; then echo "WARN: no .deb cached for $name"; continue; fi
  dpkg-deb -x "$deb" work/rootfs
done < cache/gui-packages.txt
echo "extracted $(wc -l < cache/gui-packages.txt) packages into work/rootfs"

# --- merged-/usr links (Ubuntu layout): dpkg-deb -x does not create
# them, and without /lib64 -> usr/lib64 the dynamic loader
# (/lib64/ld-linux-x86-64.so.2) is missing, so every dynamic binary
# (Xorg, xinit, ...) fails as "not found". Found by the stopped
# background run's GAP-REPORT, verified live in /tmp/gui-live.log. ---
if [ -d work/rootfs/lib ] && [ ! -L work/rootfs/lib ]; then
  # keep anything a package really put under /lib (rare on usrmerge)
  (cd work/rootfs/lib && tar cf - .) | (cd work/rootfs/usr/lib && tar xf -)
  rm -rf work/rootfs/lib
fi
ln -s usr/lib work/rootfs/lib
ln -s usr/lib64 work/rootfs/lib64
mkdir -p work/rootfs/usr/lib64
ln -sf ../lib/x86_64-linux-gnu/ld-linux-x86-64.so.2 work/rootfs/usr/lib64/ld-linux-x86-64.so.2

# --- trim: the fbdev desktop never loads Mesa/Gallium/GL (no GPU in QEMU)
# or Ghostscript; those files are ~0.22 GB of dead weight and the 200 MB
# initramfs could not even unpack in 1 GB of guest RAM (write error).
# Verified: no DT_NEEDED of Xorg/openbox/tint2/xterm/feh/fbdev_drv.so
# references libLLVM, libgallium, libgs or libspectre (only Mesa's own
# libEGL_mesa/libGLX_mesa do, and fbdev never loads them).
rm -f work/rootfs/usr/lib/x86_64-linux-gnu/libLLVM.so.* \
      work/rootfs/usr/lib/x86_64-linux-gnu/libgallium-*.so \
      work/rootfs/usr/lib/x86_64-linux-gnu/libgs.so.* \
      work/rootfs/usr/lib/x86_64-linux-gnu/libspectre.so.*
rm -rf work/rootfs/usr/lib/x86_64-linux-gnu/dri \
       work/rootfs/usr/share/doc work/rootfs/usr/share/man
# verify every NEEDED lib of the GUI binaries still exists in the rootfs
for b in usr/lib/xorg/Xorg usr/bin/openbox usr/bin/tint2 usr/bin/xterm usr/bin/feh usr/lib/xorg/modules/drivers/fbdev_drv.so; do
  for lib in $(readelf -d "work/rootfs/$b" 2>/dev/null | sed -n 's/.*NEEDED.*\[\(.*\)\]/\1/p'); do
    if [ ! -e "work/rootfs/usr/lib/x86_64-linux-gnu/$lib" ] && [ ! -e "work/rootfs/lib/x86_64-linux-gnu/$lib" ] && [ ! -e "work/rootfs/usr/lib/$lib" ]; then
      echo "TRIM-CHECK FAIL: $b needs missing $lib"; exit 1
    fi
  done
done
echo "trim-check ok"

# --- busybox applets + base dirs ---
mkdir -p work/rootfs/{bin,sbin,proc,sys,dev,root,etc,tmp,var/log,var/tmp,run}
cp "$BB" work/rootfs/bin/busybox
chmod 755 work/rootfs/bin/busybox
(cd work/rootfs/bin && for a in sh mount umount hostname uname clear poweroff reboot cat ls echo grep sleep mknod ln; do [ -e "$a" ] || ln -sf busybox "$a"; done)
(cd work/rootfs/sbin && for a in poweroff reboot halt; do [ -e "$a" ] || ln -sf ../bin/busybox "$a"; done)

# --- dpkg status DB + apt sources: the rootfs must be a real distro
# rootfs, not just extracted files. Build /var/lib/dpkg/status from the
# control files of every cached .deb, and point apt at the same mirror
# the .debs came from (azure.archive.ubuntu.com, stonking). ---
mkdir -p work/rootfs/var/lib/dpkg work/rootfs/etc/apt/sources.list.d work/rootfs/etc/apt/trusted.gpg.d
: > work/rootfs/var/lib/dpkg/status
mkdir -p work/ctrl
while read -r name ver; do
  deb=$(ls cache/${name}_*.deb 2>/dev/null | sort -V | tail -1)
  [ -n "$deb" ] || continue
  rm -rf work/ctrl/*; dpkg-deb -e "$deb" work/ctrl 2>/dev/null || continue
  [ -f work/ctrl/control ] || continue
  { echo "Status: install ok installed"; cat work/ctrl/control; echo; } >> work/rootfs/var/lib/dpkg/status
done < cache/gui-packages.txt
touch work/rootfs/var/lib/dpkg/available
cat > work/rootfs/etc/apt/sources.list.d/ubuntu.sources <<'EOF'
Types: deb
URIs: http://azure.archive.ubuntu.com/ubuntu
Suites: stonking stonking-updates stonking-security
Components: main universe restricted multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
EOF
ln -sf /usr/share/keyrings/ubuntu-archive-keyring.gpg work/rootfs/etc/apt/trusted.gpg.d/ubuntu-archive-keyring.gpg 2>/dev/null || true
echo "dpkg status entries: $(grep -c '^Package: ' work/rootfs/var/lib/dpkg/status)"

# --- overlay: init, session, configs (rootfs/ is the source of truth) ---
cp -a rootfs/. work/rootfs/
chmod +x work/rootfs/init work/rootfs/usr/local/bin/* 2>/dev/null || true

# this glibc's localedef cannot read .gz charmaps; ship plain ones so
# the boot-time locale fallback works (primary locale is pre-generated
# in the overlay under usr/lib/locale/)
for cm in UTF-8 ANSI_X3.4-1968; do
  if [ -f "work/rootfs/usr/share/i18n/charmaps/$cm.gz" ] && [ ! -f "work/rootfs/usr/share/i18n/charmaps/$cm" ]; then
    zcat "work/rootfs/usr/share/i18n/charmaps/$cm.gz" > "work/rootfs/usr/share/i18n/charmaps/$cm"
  fi
done

# --- version / branding ---
printf 'Saman OS 2.0 (Linux-based)\nID=samanos\nVERSION_ID=2.0\nBASE=ubuntu-26.10-stonking\nKERNEL=7.3.0-10-generic\n' > work/rootfs/etc/saman-release
printf '\n  Saman OS 2.0 - welcome\n\n' > work/rootfs/etc/motd
# minimal passwd/group so Xorg/libc lookups succeed
printf 'root:x:0:0:root:/root:/bin/sh\n' > work/rootfs/etc/passwd
printf 'root:x:0:\n' > work/rootfs/etc/group
printf 'samanos\n' > work/rootfs/etc/hostname

# --- pack initramfs (newc cpio, gzipped) ---
rm -f build/initrd.img
(cd work/rootfs && find . | "$BB" cpio -o -H newc 2>/dev/null) | gzip -9 > build/initrd.img
ls -lh build/
echo "BUILD_GUI_OK"
