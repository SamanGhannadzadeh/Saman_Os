#!/usr/bin/env python3
"""Fetch the Ubuntu stonking (26.10) packages Saman OS (Linux-based) needs for step 2
(product desktop (GNOME)): Xorg + fbdev, evdev/libinput, openbox, tint2, xterm,
Persian font + locale support, udev.

Same proven pattern as tools/fetch-base.py: urllib through the ambient
egress proxy, Packages.xz index, dpkg-deb -x extraction (no system apt).
Resolves Depends/Pre-Depends recursively over main + universe.
"""
import io, lzma, os, re, sys, time, urllib.request

BASE = "http://azure.archive.ubuntu.com/ubuntu"
# Saman's order 13 Nov 2026 ~13:07: always use the NEWEST stable release.
# Base is Ubuntu 26.10 "stonking" + kernel 7.3.0-10-generic (checked this run).
DIST = "stonking"
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "..", "cache")
os.makedirs(CACHE, exist_ok=True)

# Explicit top-level targets for the product desktop (GNOME).
TARGETS = [
    "linux-modules-7.3.0-10-generic",
    "linux-modules-extra-7.3.0-10-generic",
    "systemd",
    "systemd-sysv",
    "libpam-systemd",
    "udev",
    "kmod",
    "dbus",
    "policykit-1",
    "bash",
    "sudo",
    "gdm3",
    "gnome-shell",
    "gnome-session",
    "gnome-terminal",
    "gnome-control-center",
    "nautilus",
    "gnome-shell-extension-ubuntu-dock",
    "yaru-theme-gtk",
    "yaru-theme-icon",
    "yaru-theme-gnome-shell",
    "yaru-theme-sound",
    "fonts-ubuntu",
    "network-manager",
    "openssh-server",
    # Security/encryption maximum (Saman, 2026-11-19): LUKS2 disk
    # encryption in the installer + loader, automatic security
    # updates, nftables firewall, PAM password quality.
    "cryptsetup",
    "cryptsetup-bin",
    # Everyday completeness (2026-11-19): the product shipped with
    # NO web browser — a desktop cannot ask users to live without
    # one. Epiphany (webkitgtk) is the GNOME-native choice that
    # fits the extracted-rootfs model (Ubuntu's firefox/chromium
    # are snap stubs). Plus the basic viewers every desktop needs.
    # Desktop security pack (2026-11-19, Saman: «امنیتی‌تر»):
    # usbguard = BadUSB/device control, zram-tools = compressed
    # RAM swap (no secrets ever touch a disk swap), apparmor-utils
    # = profile management for the enforced AppArmor baseline.
    "usbguard",
    "zram-tools",
    "apparmor-utils",
    # Saman Antivirus (2026-11-19): the OS's own antivirus uses
    # ClamAV as its production engine when present, with the
    # built-in hash engine as fallback.
    "clamav",
    "epiphany-browser",
    "eog",
    "evince",
    "file-roller",
    "gnome-text-editor",
    "unattended-upgrades",
    "nftables",
    "iptables",
    "libpam-pwquality",
    "xdg-desktop-portal-gnome",
    "ubuntu-minimal",
    "dash",
    "tzdata",
    "coreutils",
    "sed",
    "grep",
    "gawk",
    "findutils",
    "diffutils",
    "debianutils",
    "hostname",
    "tar",
    "gzip",
    "util-linux",
    "procps",
    "gnome-keyring",
    "libpam-gnome-keyring",
    # Installer toolchain (step 3): partitioning, ESP formatting,
    # GRUB for UEFI + BIOS and EFI boot entries.
    "fdisk",
    "dosfstools",
    "grub-common",
    "grub2-common",
    "grub-efi-amd64",
    "grub-efi-amd64-bin",
    "grub-pc",
    "grub-pc-bin",
    "efibootmgr",
    # --- FULL PAYLOAD (2026-11-19, Saman: «همهٔ چیزهایی که باید
    # یک سیستم‌عامل خوب داشته باشد» + Windows-11-class completeness).
    # Everything a complete everyday OS ships, verified one by one
    # against the stonking main+universe index (108+17 names).
    # GNOME suite:
    "gnome-calendar", "gnome-contacts", "gnome-weather",
    "gnome-maps", "gnome-music", "gnome-clocks", "gnome-characters",
    "gnome-font-viewer", "gnome-disk-utility", "gnome-system-monitor",
    "gnome-logs", "gnome-connections", "gnome-snapshot", "baobab",
    "seahorse", "deja-dup", "simple-scan", "gnome-tweaks",
    "gnome-software", "gnome-calculator", "totem", "rhythmbox",
    "gnome-console", "gnome-remote-desktop", "gnome-power-manager",
    # Office (LibreOffice full + Persian + Office-metric fonts):
    "libreoffice-writer", "libreoffice-calc", "libreoffice-impress",
    "libreoffice-draw", "libreoffice-gtk3", "libreoffice-l10n-fa",
    "hunspell-fa", "hunspell-en-us", "fonts-liberation",
    "fonts-crosextra-carlito", "fonts-crosextra-caladea",
    # Media + codecs (what Ubuntu calls restricted extras, openly):
    "vlc", "mpv", "celluloid", "ffmpeg", "gstreamer1.0-plugins-bad",
    "gstreamer1.0-plugins-ugly", "gstreamer1.0-libav",
    "libavcodec-extra", "mesa-va-drivers", "i965-va-driver",
    # Creative:
    "gimp", "inkscape", "shotwell", "loupe", "drawing", "kdenlive",
    "flameshot", "xournalpp",
    # Mail + comms + files over the wire:
    "geary", "evolution", "filezilla", "remmina",
    # Fonts + language (full Noto + Persian packs):
    "fonts-noto", "fonts-noto-core", "fonts-noto-cjk",
    "fonts-noto-color-emoji", "fonts-noto-mono", "fonts-dejavu",
    "language-pack-fa", "language-pack-gnome-fa",
    # Hardware completeness: firmware, microcode, drivers tooling,
    # printing/scanning, bluetooth, mobile broadband, biometrics:
    "linux-firmware", "intel-microcode", "amd64-microcode",
    "ubuntu-drivers-common", "fwupd", "bolt", "power-profiles-daemon",
    "switcheroo-control", "iio-sensor-proxy", "cups", "cups-browsed",
    "printer-driver-all", "sane-utils", "bluez", "modemmanager",
    "mobile-broadband-provider-info", "usb-modeswitch", "fprintd",
    # App platform + everyday system tools:
    "flatpak", "gnome-software-plugin-flatpak",
    "software-properties-gtk", "git", "wget", "rsync", "zip",
    "unzip", "7zip", "unrar-free", "openssh-client", "ntfs-3g",
    "exfatprogs", "f2fs-tools", "xfsprogs", "btrfs-progs", "lvm2",
    "mdadm", "smartmontools", "nvme-cli", "hdparm", "lm-sensors",
    "wireguard-tools", "gparted", "gnome-boxes",
    # Accessibility (a good OS ships these, like Narrator & co):
    "orca", "onboard", "espeak-ng", "speech-dispatcher",
    # The small games Ubuntu ships:
    "gnome-mines", "gnome-mahjongg", "gnome-sudoku", "aisleriot",
    "gnome-chess", "quadrapassel",
    # VPN profiles in NetworkManager + gaming:
    "network-manager-openvpn", "network-manager-openconnect",
    "gamemode", "mangohud",
    "pavucontrol", "pipewire", "wireplumber",
    "xdg-desktop-portal-gtk",
    # --- WAVE 2 (2026-11-19): gaps from the Windows 11 (26H2 /
    # 25H2 — same servicing branch) inventory research, mapped to
    # their Saman OS equivalents:
    # Snipping Tool OCR -> tesseract (+Persian), To Do -> Endeavour,
    # Sound Recorder -> GNOME Sound Recorder, clipboard history
    # (Win+V) -> CopyQ, Get Help -> Yelp + GNOME user docs,
    # inbox image extensions (HEIF/WebP) -> loaders, screen
    # recording beyond the shell's -> OBS + SimpleScreenRecorder,
    # OneDrive sync client (optional use).
    "tesseract-ocr", "tesseract-ocr-fas", "endeavour", "onedrive",
    "gnome-sound-recorder", "copyq", "yelp", "gnome-user-docs",
    "webp-pixbuf-loader", "libheif1", "obs-studio",
    "simplescreenrecorder",
    # --- WAVE 3 (2026-11-19, Saman: «از قابلیت‌های ویندوز
    # استفاده کن»): Windows platform features whose equivalents
    # are genuinely useful here —
    # Phone Link (GNOME-native) -> GSConnect (replaces kdeconnect:
    # no KDE stack on a GNOME OS, shell-integrated pairing),
    # WSL-style distro containers -> distrobox,
    # Family / screen-time (also gold for the school) -> malcontent,
    # gaming-peripheral control (the owner's G923 world) ->
    # input-remapper + solaar (Logitech manager).
    "gnome-shell-extension-gsconnect", "distrobox", "malcontent",
    "input-remapper", "solaar",
]

# --- Server edition (2026-11-19): a REAL lean server closure.
# Saman caught the old "server" being the full desktop with GNOME
# masked (only 0.02 GB lighter). The server gets its own minimal
# target list: no GNOME, no desktop, just the system, networking,
# SSH and what the Ofogheamn stack (overlay binaries) needs.
SERVER_TARGETS = [
    "linux-modules-7.3.0-10-generic",
    "linux-modules-extra-7.3.0-10-generic",
    "systemd",
    "systemd-sysv",
    "libpam-systemd",
    "systemd-resolved",
    "udev",
    "kmod",
    "dbus",
    "bash",
    "sudo",
    "network-manager",
    "openssh-server",
    "openssh-client",
    "python3",
    "curl",
    "ca-certificates",
    "iptables",
    "nftables",
    "wireguard-tools",
    "iproute2",
    "iputils-ping",
    "procps",
    "locales",
    "tzdata",
    "nano",
    "less",
    "fail2ban",
    "unattended-upgrades",
    "grub2-common",
    "grub-efi-amd64",
    "grub-efi-amd64-bin",
    "grub-pc",
    "grub-pc-bin",
    "efibootmgr",
]

EDITION = os.environ.get("SAMAN_EDITION", "desktop")
if EDITION == "server":
    TARGETS = SERVER_TARGETS
    OUT_NAME = "server-packages.txt"
else:
    OUT_NAME = "product-packages.txt"

# Virtual-package preferences (dep name -> real package to prefer).
VIRTUAL_PREF = {
    "awk": "mawk",
    "default-mta": None,          # not needed, drop
    "lsb-base": "lsb-base",
}

def get(url):
    # The egress proxy occasionally answers 502/503/504; retry a few times.
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "saman-os-fetch/1.0"})
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except Exception as e:
            last = e
            print(f"  retry {attempt+1}/5: {url.split('/')[-1]} ({e})", flush=True)
            time.sleep(5 * (attempt + 1))
    raise last

def stanzas(raw):
    text = raw.decode("utf-8", "replace")
    for block in text.split("\n\n"):
        d = {}
        key = None
        for line in block.splitlines():
            if line.startswith(" ") and key:
                d[key] += "\n" + line
            elif ": " in line:
                key, val = line.split(": ", 1)
                d[key] = val
        if d:
            yield d

def parse_dep_field(field):
    """Yield dep names from a Depends/Pre-Depends field (first alt only)."""
    if not field:
        return
    for group in field.split(","):
        group = group.strip()
        if not group:
            continue
        first = group.split("|")[0].strip()
        name = re.split(r"\s|\(", first)[0].strip()
        name = name.split(":")[0]  # drop :amd64 qualifiers
        if name:
            yield name

def main():
    pkgs = {}       # name -> stanza (highest version)
    provides = {}   # virtual name -> [real names]
    for comp in ("main", "universe"):
        print(f"fetching {DIST} {comp} Packages.xz ...", flush=True)
        raw = lzma.decompress(get(f"{BASE}/dists/{DIST}/{comp}/binary-amd64/Packages.xz"))
        n = 0
        for p in stanzas(raw):
            n += 1
            name = p.get("Package")
            if not name:
                continue
            if name not in pkgs or p.get("Version", "") > pkgs[name].get("Version", ""):
                pkgs[name] = p
            for prov in p.get("Provides", "").split(","):
                prov = prov.strip().split(" ")[0]
                if prov:
                    provides.setdefault(prov, []).append(name)
        print(f"  {comp}: {n} stanzas", flush=True)
    print(f"index ok: {len(pkgs)} packages", flush=True)

    def resolve(name):
        if name in pkgs:
            return pkgs[name]
        if name in VIRTUAL_PREF:
            pref = VIRTUAL_PREF[name]
            if pref is None:
                return None
            return pkgs.get(pref)
        cands = provides.get(name, [])
        if cands:
            # Prefer a non-virtual, already-common provider.
            return pkgs[sorted(cands)[0]]
        return None

    wanted = {}
    missing = []
    queue = list(TARGETS)
    while queue:
        name = queue.pop(0)
        if name in wanted:
            continue
        p = resolve(name)
        if p is None:
            missing.append(name)
            print(f"NOT FOUND: {name}", flush=True)
            continue
        wanted[p["Package"]] = p
        for field in (p.get("Pre-Depends", ""), p.get("Depends", "")):
            for dep in parse_dep_field(field):
                if dep not in wanted:
                    queue.append(dep)

    print(f"resolved: {len(wanted)} packages", flush=True)
    if missing:
        print(f"missing: {missing}", flush=True)

    total = 0
    for name in sorted(wanted):
        p = wanted[name]
        dest = os.path.join(CACHE, os.path.basename(p["Filename"]))
        size = int(p["Size"])
        total += size
        if os.path.exists(dest) and os.path.getsize(dest) == size:
            print(f"cached: {name} {p['Version']}", flush=True)
            continue
        print(f"downloading {p['Filename']} ({size/1e6:.1f} MB) ...", flush=True)
        data = get(f"{BASE}/{p['Filename']}")
        assert len(data) == size, (len(data), size)
        with open(dest, "wb") as f:
            f.write(data)
        print(f"saved: {dest}", flush=True)
    print(f"TOTAL download size: {total/1e6:.1f} MB", flush=True)
    with open(os.path.join(CACHE, OUT_NAME), "w") as f:
        for name in sorted(wanted):
            f.write(f"{name} {wanted[name]['Version']}\n")
    print("DONE", flush=True)

if __name__ == "__main__":
    main()
