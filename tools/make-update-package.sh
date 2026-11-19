#!/bin/bash
# Build a Saman OS update package for a GitHub Release.
# Usage: tools/make-update-package.sh <version> <payload-dir>
# The payload dir must contain:
#   install.sh  – run as root at install time, $1 = payload dir
#   files.txt   – absolute paths the update touches (for backup)
#   ...any payload files install.sh needs...
# Output: build/updates/saman-os-update-<version>.tar.gz (+ .sha256)
set -e
umask 022
cd "$(dirname "$0")/.."
VER="${1:?version required}"
PAYLOAD="${2:?payload dir required}"
[ -f "$PAYLOAD/install.sh" ] || { echo "payload needs install.sh"; exit 1; }
[ -f "$PAYLOAD/files.txt" ] || { echo "payload needs files.txt"; exit 1; }
mkdir -p build/updates
OUT="build/updates/saman-os-update-${VER}.tar.gz"
tar -czf "$OUT" -C "$PAYLOAD" .
(cd build/updates && sha256sum "saman-os-update-${VER}.tar.gz" > "saman-os-update-${VER}.tar.gz.sha256")
ls -la "$OUT"*
echo "MAKE_UPDATE_PACKAGE_OK"
