#!/usr/bin/env python3
"""Make the extracted rootfs's /etc/passwd + /etc/group complete.

Extraction (dpkg-deb -x) never runs postinst, so the system users
that packages create with adduser (geoclue, whoopsie, malcontent-*)
are missing -- and dbus-broker treats an unknown user in a policy
file as fatal. This script, run by build-product.sh on
work/disk-rootfs:
  1. merges base-passwd's canonical master lists (names not already
     present in the overlay's passwd/group are appended with the
     master's uid/gid),
  2. scans D-Bus system policy configs and systemd unit User=/Group=
     for names still missing and appends fresh system entries
     (uid/gid from 200 up, nologin).
"""
import os, re, sys

R = sys.argv[1] if len(sys.argv) > 1 else "work/disk-rootfs"

def read_names(path):
    names = {}
    if os.path.exists(path):
        for line in open(path):
            if ":" in line:
                parts = line.rstrip("\n").split(":")
                names[parts[0]] = parts
    return names

passwd = read_names(os.path.join(R, "etc/passwd"))
group = read_names(os.path.join(R, "etc/group"))

# 1) base-passwd masters
for master, table, dest in (
    ("usr/share/base-passwd/passwd.master", passwd, "etc/passwd"),
    ("usr/share/base-passwd/group.master", group, "etc/group"),
):
    mp = os.path.join(R, master)
    if not os.path.exists(mp):
        continue
    added = []
    for line in open(mp):
        if ":" not in line:
            continue
        parts = line.rstrip("\n").split(":")
        if parts[0] not in table:
            table[parts[0]] = parts
            added.append(line.rstrip("\n"))
    if added:
        with open(os.path.join(R, dest), "a") as f:
            f.write("\n".join(added) + "\n")
        print(f"sync-users: +{len(added)} from {master}")

# 2) referenced-but-missing users/groups
users, groups = set(), set()
for d in ("usr/share/dbus-1/system.d", "etc/dbus-1/system.d"):
    p = os.path.join(R, d)
    if os.path.isdir(p):
        for fn in os.listdir(p):
            t = open(os.path.join(p, fn), errors="replace").read()
            users |= set(re.findall(r'user="([^"]+)"', t))
            groups |= set(re.findall(r'group="([^"]+)"', t))
for d in ("usr/lib/systemd/system", "etc/systemd/system"):
    p = os.path.join(R, d)
    if os.path.isdir(p):
        for fn in os.listdir(p):
            fp = os.path.join(p, fn)
            if os.path.isfile(fp):
                t = open(fp, errors="replace").read()
                users |= set(re.findall(r"^User=(\S+)", t, re.M))
                groups |= set(re.findall(r"^Group=(\S+)", t, re.M))

def clean(names):
    return sorted(n for n in names
                  if n and not n.isdigit() and "%" not in n and "/" not in n)

next_uid = 200
used_uids = {int(p[2]) for p in passwd.values() if p[2].isdigit()}
new_users = []
for name in clean(users):
    if name in passwd:
        continue
    while next_uid in used_uids:
        next_uid += 1
    used_uids.add(next_uid)
    gid = next_uid
    new_users.append(name)
    passwd[name] = [name, "x", str(next_uid), str(gid), "", "/nonexistent", "/usr/sbin/nologin"]
    if name not in group:
        group[name] = [name, "x", str(gid), ""]
    next_uid += 1
if new_users:
    with open(os.path.join(R, "etc/passwd"), "a") as f:
        for name in new_users:
            f.write(":".join(passwd[name]) + "\n")
    print(f"sync-users: added users {new_users}")

next_gid = 200
used_gids = {int(p[2]) for p in group.values() if p[2].isdigit()}
new_groups = []
for name in clean(groups):
    if name in group:
        continue
    while next_gid in used_gids:
        next_gid += 1
    used_gids.add(next_gid)
    group[name] = [name, "x", str(next_gid), ""]
    new_groups.append(name)
    next_gid += 1
if new_groups:
    with open(os.path.join(R, "etc/group"), "a") as f:
        for name in new_groups:
            f.write(":".join(group[name]) + "\n")
    print(f"sync-users: added groups {new_groups}")
print("SYNC_USERS_OK")
