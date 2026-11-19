#!/bin/bash
# Build the Saman OS product rootfs on a disk image (step 2, product
# half): union of the GUI package set + the product package set
# (systemd, GNOME, Yaru, full kernel modules) extracted into
# work/disk-rootfs, configured in a chroot (ldconfig, schemas,
# presets, service enablement), overlaid with product-rootfs/
# (branding, autologin, dconf defaults, users), and packed into an
# ext4 disk image build/saman-os-disk.img (LABEL=SAMANOS).
# The loader initramfs is built separately by tools/make-loader.py.
set -e
umask 022
cd "$(dirname "$0")/.."
ROOT="$PWD"

[ -f cache/product-packages.txt ] || { echo "MISSING cache/product-packages.txt -- run tools/fetch-product.py first"; exit 1; }
[ -f cache/gui-packages.txt ] || { echo "MISSING cache/gui-packages.txt -- run tools/fetch-gui.py first"; exit 1; }

mkdir -p work build
cat cache/gui-packages.txt cache/product-packages.txt cache/modules-packages.txt 2>/dev/null | sort -u > work/all-packages.txt
echo "package union: $(wc -l < work/all-packages.txt)"

# --- assemble the disk rootfs from the cached .debs ---
rm -rf work/disk-rootfs
mkdir -p work/disk-rootfs
while read -r name ver; do
  deb=$(ls cache/${name}_*.deb 2>/dev/null | sort -V | tail -1)
  if [ -z "$deb" ]; then echo "WARN: no .deb cached for $name"; continue; fi
  dpkg-deb -x "$deb" work/disk-rootfs
done < work/all-packages.txt
echo "extracted into work/disk-rootfs"

# --- merged-/usr links (same fix as the GUI build) ---
if [ -d work/disk-rootfs/lib ] && [ ! -L work/disk-rootfs/lib ]; then
  (cd work/disk-rootfs/lib && tar cf - .) | (cd work/disk-rootfs/usr/lib && tar xf -)
  rm -rf work/disk-rootfs/lib
fi
ln -s usr/lib work/disk-rootfs/lib
ln -s usr/lib64 work/disk-rootfs/lib64
mkdir -p work/disk-rootfs/usr/lib64
ln -sf ../lib/x86_64-linux-gnu/ld-linux-x86-64.so.2 work/disk-rootfs/usr/lib64/ld-linux-x86-64.so.2

# --- trim docs/man only. Mesa/LLVM stay: the product requirement is
# the full graphics stack (llvmpipe needs libLLVM). ---
rm -rf work/disk-rootfs/usr/share/doc work/disk-rootfs/usr/share/man

# --- base dirs ---
mkdir -p work/disk-rootfs/{proc,sys,dev,run,tmp,var/log,var/tmp,home/saman}
chmod 1777 work/disk-rootfs/tmp

# --- dpkg status DB + apt sources (same as GUI build, both lists) ---
mkdir -p work/disk-rootfs/var/lib/dpkg work/disk-rootfs/etc/apt/sources.list.d work/disk-rootfs/etc/apt/trusted.gpg.d
: > work/disk-rootfs/var/lib/dpkg/status
mkdir -p work/ctrl
while read -r name ver; do
  deb=$(ls cache/${name}_*.deb 2>/dev/null | sort -V | tail -1)
  [ -n "$deb" ] || continue
  rm -rf work/ctrl/*; dpkg-deb -e "$deb" work/ctrl 2>/dev/null || continue
  [ -f work/ctrl/control ] || continue
  { echo "Status: install ok installed"; cat work/ctrl/control; echo; } >> work/disk-rootfs/var/lib/dpkg/status
done < work/all-packages.txt
touch work/disk-rootfs/var/lib/dpkg/available
cat > work/disk-rootfs/etc/apt/sources.list.d/ubuntu.sources <<'EOF'
Types: deb
URIs: http://azure.archive.ubuntu.com/ubuntu
Suites: stonking stonking-updates stonking-security
Components: main universe restricted multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
EOF
ln -sf /usr/share/keyrings/ubuntu-archive-keyring.gpg work/disk-rootfs/etc/apt/trusted.gpg.d/ubuntu-archive-keyring.gpg 2>/dev/null || true
echo "dpkg status entries: $(grep -c '^Package: ' work/disk-rootfs/var/lib/dpkg/status)"

# --- product overlay (branding, users, gdm, dconf) ---
cp -a product-rootfs/. work/disk-rootfs/
rm -f work/disk-rootfs/etc/os-release
ln -s ../usr/lib/os-release work/disk-rootfs/etc/os-release
cat > work/disk-rootfs/etc/lsb-release <<'EOF'
DISTRIB_ID=SamanOS
DISTRIB_RELEASE=2.0
DISTRIB_CODENAME=stonking
DISTRIB_DESCRIPTION="Saman OS 2.0"
EOF
printf 'Saman OS 2.0 (Linux-based)\nID=samanos\nVERSION_ID=2.0\nBASE=ubuntu-26.10-stonking\nKERNEL=7.3.0-10-generic\n' > work/disk-rootfs/etc/saman-release
# Overlay files are authored under umask 0007 and land as 0660,
# which service users (gdm, messagebus...) cannot read. Normalize
# stray 0660 files under etc/usr to 0644; shadow files stay tight.
find work/disk-rootfs/etc work/disk-rootfs/usr -type f -perm 0660 -exec chmod 0644 {} + 2>/dev/null || true
chmod 0640 work/disk-rootfs/etc/shadow work/disk-rootfs/etc/gshadow 2>/dev/null || true
chown 0:42 work/disk-rootfs/etc/shadow work/disk-rootfs/etc/gshadow 2>/dev/null || true
python3 tools/sync-users.py work/disk-rootfs
chmod 644 work/disk-rootfs/etc/passwd work/disk-rootfs/etc/group
chown 0:42 work/disk-rootfs/etc/shadow; chmod 640 work/disk-rootfs/etc/shadow
chown -R 1000:1000 work/disk-rootfs/home/saman
[ -d work/disk-rootfs/var/lib/gdm3 ] && chown -R 106:107 work/disk-rootfs/var/lib/gdm3 || true
[ -d work/disk-rootfs/var/lib/colord ] && chown -R 108:109 work/disk-rootfs/var/lib/colord || true
[ -e work/disk-rootfs/usr/share/zoneinfo/Asia/Tehran ] && ln -sf /usr/share/zoneinfo/Asia/Tehran work/disk-rootfs/etc/localtime || true

# plain charmaps so the boot-time localedef fallback works here too
for cm in UTF-8 ANSI_X3.4-1968; do
  if [ -f "work/disk-rootfs/usr/share/i18n/charmaps/$cm.gz" ] && [ ! -f "work/disk-rootfs/usr/share/i18n/charmaps/$cm" ]; then
    zcat "work/disk-rootfs/usr/share/i18n/charmaps/$cm.gz" > "work/disk-rootfs/usr/share/i18n/charmaps/$cm"
  fi
done

# --- chroot configuration: what package postinst would have done ---
CR="chroot work/disk-rootfs"
export LC_ALL=C
$CR /usr/sbin/ldconfig || echo "WARN ldconfig"
[ -x work/disk-rootfs/usr/sbin/depmod ] && $CR /usr/sbin/depmod -a 7.3.0-10-generic || echo "WARN depmod"
[ -x work/disk-rootfs/usr/bin/glib-compile-schemas ] && $CR /usr/bin/glib-compile-schemas /usr/share/glib-2.0/schemas || echo "WARN schemas"
[ -x work/disk-rootfs/usr/bin/fc-cache ] && $CR /usr/bin/fc-cache -f >/dev/null 2>&1 || echo "WARN fc-cache"
[ -x work/disk-rootfs/usr/sbin/pam-auth-update ] && $CR /usr/sbin/pam-auth-update --force >/dev/null 2>&1 || echo "WARN pam-auth-update"
$CR /usr/bin/systemctl preset-all >/dev/null 2>&1 || echo "WARN preset-all"
$CR /usr/bin/systemctl enable gdm3.service >/dev/null 2>&1 || $CR /usr/bin/systemctl enable gdm.service >/dev/null 2>&1 || echo "WARN enable gdm"
$CR /usr/bin/systemctl enable NetworkManager.service >/dev/null 2>&1 || echo "WARN enable NM"
$CR /usr/bin/systemctl enable saman-updater.timer >/dev/null 2>&1 || echo "WARN enable updater timer"
$CR /usr/bin/systemctl set-default graphical.target >/dev/null 2>&1 || echo "WARN set-default"
# The test rig's serial line is a file, not a terminal: agetty exits
# instantly on EOF and systemd restarts it forever, burning the whole
# guest CPU and starving the boot. No serial login in the product.
$CR /usr/bin/systemctl mask serial-getty@ttyS0.service >/dev/null 2>&1 || echo "WARN mask serial-getty"
# dbus-broker's launcher child dies with EPERM in this rootfs (its
# reason is not yet pinned; the classic daemon is the Debian default
# with the same packages and is far more forgiving). The broker's
# [Install] Alias=dbus.service makes preset-all plant an
# /etc/systemd/system/dbus.service symlink to the broker, shadowing
# the real dbus-daemon unit in /usr/lib. Remove the alias, mask the
# broker; dbus.service (daemon) is socket-activated, no enablement.
rm -f work/disk-rootfs/etc/systemd/system/dbus.service
$CR /usr/bin/systemctl mask dbus-broker.service >/dev/null 2>&1 || echo "WARN mask dbus-broker"
[ -x work/disk-rootfs/usr/bin/dconf ] && $CR /usr/bin/dconf update || echo "NOTE: dconf CLI absent, system defaults compile at first login instead"

# pam-auth-update (chroot step above) regenerates common-session
# but does not apply the systemd pam-config here; without
# pam_systemd no logind session / user manager is created and
# gnome-session can never register. Append the line the config
# itself declares — AFTER pam-auth-update has run.
grep -q "pam_systemd.so" work/disk-rootfs/etc/pam.d/common-session || \
  printf 'session\toptional\tpam_systemd.so\n' >> work/disk-rootfs/etc/pam.d/common-session

# --- repair directory modes (LAST step before packing): dpkg-deb -x
# creates package parent dirs under the caller's umask, and cp -a of
# the overlay copies the overlay dirs' modes over existing targets;
# under umask 0007 + a setgid workdir they land as 2770, which locks
# every non-root service user out of /usr, /etc, /run (exec and
# config reads fail with EACCES while root sails through). Normalize
# exactly the poisoned modes; legitimate 0700/0710/2755 dirs stay. ---
find work/disk-rootfs -type d \( -perm 2770 -o -perm 0770 -o -perm 2700 -o -perm 0777 \) -exec chmod 0755 {} +

# --- disk image (ext4, LABEL=SAMANOS) ---
USED_MB=$(du -sm work/disk-rootfs | cut -f1)
SIZE_MB=$((USED_MB + 2048))
[ "$SIZE_MB" -lt 6144 ] && SIZE_MB=6144
echo "rootfs ${USED_MB} MB -> image ${SIZE_MB} MB"
rm -f build/saman-os-disk.img
truncate -s "${SIZE_MB}M" build/saman-os-disk.img
mkfs.ext4 -q -L SAMANOS -d work/disk-rootfs build/saman-os-disk.img
ls -lh build/
echo "BUILD_PRODUCT_OK"
