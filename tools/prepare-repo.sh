#!/bin/bash
# Stage the public GitHub repository content into release-repo/:
# text sources only — no disk images, ISOs, debs or caches.
set -e
cd "$(dirname "$0")/.."
DST=release-repo
mkdir -p "$DST/docs"
cp -r tools "$DST/"
cp -r product-loader "$DST/"
cp -r product-rootfs "$DST/"
cp ROADMAP.md GAP-REPORT.md HANDOFF-FOR-AI.md "$DST/docs/" 2>/dev/null || true
cp docs/DUALBOOT-GUIDE.fa.md "$DST/docs/" 2>/dev/null || true
# never ship build outputs or caches that may sit inside copied trees
find "$DST" -name "*.iso" -o -name "*.img" -o -name "*.deb" -delete
# never publish credential stores; the build regenerates them
rm -f "$DST/product-rootfs/etc/shadow" "$DST/product-rootfs/etc/gshadow"
find "$DST" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
du -sh "$DST"
echo "PREPARE_REPO_OK"
