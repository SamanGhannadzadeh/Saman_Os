#!/usr/bin/env python3
"""Build the product loader initramfs (build/product-initrd.img).

Contents: busybox + the storage module closure needed to mount the
real root disk (virtio-blk + ATA/IDE + ext4, resolved transitively
from the module tree's own modules.dep) + product-loader/init.
Modules ship .ko.zst in Ubuntu 26.10; they are decompressed here so
busybox insmod + finit_module always see plain ELF objects.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
KVER = "7.3.0-10-generic"
MODDIR = os.path.join(ROOT, "work", "disk-rootfs", "usr", "lib", "modules", KVER)
LOADER = os.path.join(ROOT, "work", "loader-rootfs")
SEEDS = [
    "kernel/drivers/block/virtio_blk.ko",
    "kernel/drivers/virtio/virtio_pci.ko",
    "kernel/drivers/ata/ata_piix.ko",
    "kernel/drivers/scsi/sd_mod.ko",
    "kernel/fs/ext4/ext4.ko",
    # live-ISO mode: read the ISO, mount the squashfs, overlay tmpfs
    "kernel/fs/isofs/isofs.ko",
    "kernel/fs/overlayfs/overlay.ko",
]

def load_depmap():
    depmap = {}
    with open(os.path.join(MODDIR, "modules.dep")) as f:
        for line in f:
            line = line.strip()
            if not line or ":" not in line:
                continue
            mod, deps = line.split(":", 1)
            depmap[mod.strip()] = deps.split()
    return depmap

def find_seed(depmap, seed):
    """modules.dep keys carry the compression suffix (.ko.zst)."""
    if seed in depmap:
        return seed
    for key in depmap:
        if key.startswith(seed):
            return key
    return None

def main():
    if not os.path.isdir(MODDIR):
        print(f"MISSING {MODDIR} -- run tools/build-product.sh first")
        return 1
    depmap = load_depmap()
    order, seen = [], set()

    def visit(modkey):
        if modkey in seen:
            return
        seen.add(modkey)
        for dep in depmap.get(modkey, []):
            visit(dep)
        order.append(modkey)

    builtin = set()
    bpath = os.path.join(MODDIR, "modules.builtin")
    if os.path.exists(bpath):
        with open(bpath) as f:
            builtin = {line.strip() for line in f if line.strip()}
    for seed in SEEDS:
        key = find_seed(depmap, seed)
        if key is None:
            if seed in builtin:
                print(f"seed built-in (=y), no module needed: {seed}")
                continue
            print(f"SEED NOT FOUND: {seed}")
            return 1
        visit(key)
    print(f"module closure: {len(order)} modules")

    subprocess.run(["rm", "-rf", LOADER], check=True)
    os.makedirs(os.path.join(LOADER, "bin"))
    os.makedirs(os.path.join(LOADER, "lib", "modules"))
    os.makedirs(os.path.join(LOADER, "dev"))
    os.makedirs(os.path.join(LOADER, "proc"))
    os.makedirs(os.path.join(LOADER, "sys"))

    bb_src = None
    for cand in (os.path.join(ROOT, "work", "bx73", "usr", "bin", "busybox"),
                 os.path.join(ROOT, "work", "bx73", "usr", "bin", "busybox-static")):
        if os.path.exists(cand):
            bb_src = cand
            break
    if not bb_src:
        print("MISSING busybox -- run tools/build-gui.sh once")
        return 1
    subprocess.run(["cp", bb_src, os.path.join(LOADER, "bin", "busybox")], check=True)
    os.chmod(os.path.join(LOADER, "bin", "busybox"), 0o755)

    names = []
    for modkey in order:
        src = os.path.join(MODDIR, modkey)
        base = os.path.basename(modkey)
        for suffix in (".zst", ".xz", ".gz"):
            if base.endswith(suffix):
                base = base[: -len(suffix)]
                break
        dest = os.path.join(LOADER, "lib", "modules", base)
        if modkey.endswith(".zst"):
            zstd = os.path.expanduser("~/workspace/tools/zstd-cli/usr/bin/zstd")
            if not os.path.exists(zstd):
                zstd = "zstd"
            with open(dest, "wb") as out:
                subprocess.run([zstd, "-d", "-q", "-c", src], stdout=out, check=True)
        elif modkey.endswith(".xz"):
            import lzma
            with open(src, "rb") as f, open(dest, "wb") as out:
                out.write(lzma.decompress(f.read()))
        else:
            subprocess.run(["cp", src, dest], check=True)
        names.append(f"/lib/modules/{base}")
    with open(os.path.join(LOADER, "modules.list"), "w") as f:
        f.write("\n".join(names) + "\n")

    subprocess.run(["cp", os.path.join(ROOT, "product-loader", "init"),
                    os.path.join(LOADER, "init")], check=True)
    os.chmod(os.path.join(LOADER, "init"), 0o755)

    out_img = os.path.join(ROOT, "build", "product-initrd.img")
    listing = subprocess.run(["find", "."], cwd=LOADER, capture_output=True, text=True, check=True).stdout
    cpio = subprocess.run([os.path.join(LOADER, "bin", "busybox"), "cpio", "-o", "-H", "newc"],
                          cwd=LOADER, input=listing.encode(), capture_output=True)
    if cpio.returncode != 0:
        print(cpio.stderr.decode("utf-8", "replace"))
        return 1
    import gzip
    with open(out_img, "wb") as f:
        f.write(gzip.compress(cpio.stdout, compresslevel=6))
    print(f"loader initrd: {out_img} ({os.path.getsize(out_img)/1e6:.1f} MB)")
    print("MAKE_LOADER_OK")
    return 0

if __name__ == "__main__":
    sys.exit(main())
