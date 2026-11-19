#!/usr/bin/python3
# Saman NetTest — gaming ping + DNS lookup test for Saman OS.
import re
import socket
import subprocess
import threading
import time

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

TARGETS = [
    ("کالاف — Demonware", "demonware.net"),
    ("بتل‌نت (Blizzard)", "battle.net"),
    ("اکتیویژن", "activision.com"),
    ("EA", "ea.com"),
    ("Riot", "riotgames.com"),
    ("استیم", "store.steampowered.com"),
    ("اپیک", "epicgames.com"),
    ("Cloudflare DNS", "1.1.1.1"),
    ("Google DNS", "8.8.8.8"),
]


def ping_ms(host):
    try:
        r = subprocess.run(["ping", "-c", "3", "-W", "2", host],
                           capture_output=True, text=True, timeout=12)
        m = re.search(r"avg[^=]*= [\d.]+/([\d.]+)/", r.stdout)
        return f"{float(m.group(1)):.0f} ms" if m else "بدون پاسخ"
    except Exception:
        return "خطا"


def dns_ms(host):
    t0 = time.time()
    try:
        socket.getaddrinfo(host, 443)
        return f"{(time.time() - t0) * 1000:.0f} ms"
    except Exception:
        return "خطا"


class NetTest(Gtk.Window):
    def __init__(self):
        super().__init__(title="تست پینگ گیمینگ — Saman NetTest")
        self.set_default_size(560, 430)
        self.set_border_width(12)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add(box)
        head = Gtk.Label()
        head.set_markup("<b>پینگ و سرعت DNS سرورهای بازی</b>")
        head.set_halign(Gtk.Align.START)
        box.pack_start(head, False, False, 0)
        self.store = Gtk.ListStore(str, str, str, str)
        for name, host in TARGETS:
            self.store.append([name, host, "…", "…"])
        tree = Gtk.TreeView(model=self.store)
        for i, col in enumerate(["سرویس", "هاست", "پینگ", "DNS"]):
            tree.append_column(Gtk.TreeViewColumn(col, Gtk.CellRendererText(), text=i))
        box.pack_start(Gtk.ScrolledWindow(child=tree), True, True, 0)
        self.btn = Gtk.Button(label="▶  شروع تست")
        self.btn.connect("clicked", self.on_run)
        box.pack_start(self.btn, False, False, 0)

    def on_run(self, *_):
        self.btn.set_sensitive(False)

        def work():
            for i, (_name, host) in enumerate(TARGETS):
                p, d = ping_ms(host), dns_ms(host)
                GLib.idle_add(self.set_row, i, p, d)
            GLib.idle_add(self.btn.set_sensitive, True)
        threading.Thread(target=work, daemon=True).start()

    def set_row(self, i, p, d):
        it = self.store.get_iter_from_string(str(i))
        self.store.set(it, 2, p, 3, d)


win = NetTest()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
