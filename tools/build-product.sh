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

if [ "${SAMAN_EDITION:-desktop}" = "server" ]; then
  [ -f cache/server-packages.txt ] || { echo "MISSING cache/server-packages.txt -- run SAMAN_EDITION=server tools/fetch-product.py first"; exit 1; }
else
  [ -f cache/product-packages.txt ] || { echo "MISSING cache/product-packages.txt -- run tools/fetch-product.py first"; exit 1; }
  [ -f cache/gui-packages.txt ] || { echo "MISSING cache/gui-packages.txt -- run tools/fetch-gui.py first"; exit 1; }
fi

mkdir -p work build
if [ "${SAMAN_EDITION:-desktop}" = "server" ]; then
  # Lean server: its own closure + kernel modules ONLY (no GUI, no
  # desktop product packages — the fix for the "masked desktop"
  # server Saman caught on 2026-11-19).
  cat cache/server-packages.txt cache/modules-packages.txt 2>/dev/null | sort -u > work/all-packages.txt
else
  cat cache/gui-packages.txt cache/product-packages.txt cache/modules-packages.txt 2>/dev/null | sort -u > work/all-packages.txt
fi
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
# The stock Yaru package ships themes/Yaru/gnome-shell as a SYMLINK
# into gnome-shell/theme/Yaru, but product-rootfs carries a real
# directory there (the glass CSS) — cp -a refuses to overwrite a
# symlink with a directory. Drop such symlinks first.
for p in usr/share/themes/Yaru/gnome-shell; do
  if [ -L "work/disk-rootfs/$p" ] && [ -d "product-rootfs/$p" ]; then
    rm "work/disk-rootfs/$p"
  fi
done
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
$CR /usr/bin/systemctl enable saman-dns-firstboot.service >/dev/null 2>&1 || echo "WARN enable dns-firstboot"
$CR /usr/bin/systemctl enable apparmor.service >/dev/null 2>&1 || echo "WARN enable apparmor"
$CR /usr/bin/systemctl enable nftables.service >/dev/null 2>&1 || echo "WARN enable nftables"
$CR /usr/bin/systemctl enable usbguard.service >/dev/null 2>&1 || echo "WARN enable usbguard"
$CR /usr/bin/systemctl enable zramswap.service >/dev/null 2>&1 || echo "WARN enable zramswap"
$CR /usr/bin/systemctl enable saman-av-scan.timer saman-av-update.timer >/dev/null 2>&1 || echo "WARN enable saman-av timer"
# A desktop does not need to advertise itself on the LAN.
$CR /usr/bin/systemctl mask avahi-daemon.service avahi-daemon.socket >/dev/null 2>&1 || echo "WARN mask avahi"
$CR /usr/bin/systemctl set-default graphical.target >/dev/null 2>&1 || echo "WARN set-default"
# The test rig's serial line is a file, not a terminal: agetty exits
# instantly on EOF and systemd restarts it forever, burning the whole
# guest CPU and starving the boot. No serial login in the product.
if [ "${SAMAN_TEST_SERIAL:-}" != "1" ]; then
  $CR /usr/bin/systemctl mask serial-getty@ttyS0.service >/dev/null 2>&1 || echo "WARN mask serial-getty"
else
  echo "TEST BUILD: serial-getty left unmasked (SAMAN_TEST_SERIAL=1)"
  # Test-only session diagnostic: 150 s after boot, report the
  # graphical session's truth to the serial line and un-blank it.
  cat > work/disk-rootfs/etc/systemd/system/saman-test-diag.service <<'DIAG_EOF'
[Unit]
Description=Saman OS test diagnostic (test builds only)
After=graphical.target
[Service]
Type=oneshot
ExecStart=/bin/bash -c 'sleep 150; { echo ===DIAG===; loginctl list-sessions; systemctl is-active gdm3; pgrep -a gnome-shell | head -2; journalctl -b --no-pager | grep -iE "gnome-shell|gdm|mutter" | grep -iE "error|crash|fail|segv|JS ERROR" | head -8; runuser -u saman -- env DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus XDG_RUNTIME_DIR=/run/user/1000 gsettings set org.gnome.desktop.session idle-delay 0; loginctl unlock-sessions; echo ===DIAG_END===; } > /dev/ttyS0 2>&1'
[Install]
WantedBy=multi-user.target
DIAG_EOF
  $CR /usr/bin/systemctl enable saman-test-diag.service >/dev/null 2>&1 || echo "WARN enable test-diag"
fi
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

# More postinst work the extraction skips (both editions):
# sudo on 26.10 is sudo-rs/sudo.ws; the /usr/bin/sudo alternatives
# symlink is planted by postinst, so without it there is no sudo.
[ -e work/disk-rootfs/usr/bin/sudo ] || ln -s sudo.ws work/disk-rootfs/usr/bin/sudo
# openssh-server: sshd_config is ucf-generated by postinst and the
# host keys likewise; without both, sshd fails instantly.
if [ ! -f work/disk-rootfs/etc/ssh/sshd_config ]; then
  printf 'Port 22\nPermitRootLogin no\nPasswordAuthentication yes\nKbdInteractiveAuthentication no\nUsePAM yes\nSubsystem sftp /usr/lib/openssh/sftp-server\n' \
    > work/disk-rootfs/etc/ssh/sshd_config
  chmod 644 work/disk-rootfs/etc/ssh/sshd_config
fi
$CR /usr/bin/ssh-keygen -A >/dev/null 2>&1 || echo "WARN ssh-keygen"

# --- Saman OS Server edition (SAMAN_EDITION=server): headless,
# with the Ofogheamn DNS + proxy + panel stack preinstalled ---
if [ "${SAMAN_EDITION:-desktop}" = "server" ]; then
  echo "SERVER EDITION: applying server-overlay"
  cp -a server-overlay/. work/disk-rootfs/
  $CR /usr/sbin/useradd --system --no-create-home --shell /usr/sbin/nologin ofodns 2>/dev/null || echo "NOTE ofodns user exists"
  $CR /usr/bin/chown -R ofodns:ofodns /var/cache/ofogheamn-dns /var/log/ofogheamn-dns 2>/dev/null || echo "WARN chown ofodns dirs"
  # The overlay's files carry the author's umask (0660 root:nogroup):
  # the ofodns service user could not even read smartdns.conf and the
  # service crash-looped with "Permission denied". Normalize: configs
  # and lists world-readable, secrets stay tight, the TLS key is
  # group-ofodns readable (smartdns reads it as ofodns).
  find work/disk-rootfs/etc/ofogheamn-dns -type f -perm 0660 -exec chmod 0644 {} +
  chmod 0600 work/disk-rootfs/etc/ofogheamn-dns/panel.conf \
             work/disk-rootfs/etc/ofogheamn-dns/proxy-users.json \
             work/disk-rootfs/etc/ofogheamn-dns/wg-server.key \
             work/disk-rootfs/etc/ofogheamn-dns/wg0.conf 2>/dev/null || true
  $CR /usr/bin/chown root:ofodns /etc/ofogheamn-dns/tls/privkey.pem 2>/dev/null || echo "WARN chown privkey"
  chmod 0640 work/disk-rootfs/etc/ofogheamn-dns/tls/privkey.pem
  $CR /usr/bin/systemctl mask gdm3.service >/dev/null 2>&1 || echo "WARN mask gdm3"
  # The server's firewall policy belongs to the Ofogheamn stack, not
  # the desktop nftables baseline.
  $CR /usr/bin/systemctl disable nftables.service >/dev/null 2>&1 || echo "WARN disable nftables (server)"
  $CR /usr/bin/systemctl set-default multi-user.target >/dev/null 2>&1 || echo "WARN set-default multi-user"
  $CR /usr/bin/systemctl enable ssh.service >/dev/null 2>&1 || $CR /usr/bin/systemctl enable sshd.service >/dev/null 2>&1 || echo "WARN enable ssh"
  # The name is "Saman OS" in EVERY edition (Saman, 2026-11-19);
  # the server is a VARIANT of it, never a different name.
  sed -i 's/^PRETTY_NAME=.*/PRETTY_NAME="Saman OS 2.0"/; s/^NAME=.*/NAME="Saman OS"/' work/disk-rootfs/usr/lib/os-release
  grep -q '^VARIANT=' work/disk-rootfs/usr/lib/os-release || printf 'VARIANT="Server"\nVARIANT_ID=server\n' >> work/disk-rootfs/usr/lib/os-release
fi

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
