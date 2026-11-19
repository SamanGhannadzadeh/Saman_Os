#!/usr/bin/env python3
# Saman Settings — a friendly front door to GNOME Settings + Saman tools.
import subprocess
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

def open_panel(panel):
    subprocess.Popen(["gnome-control-center", panel])

def run(cmd):
    subprocess.Popen([cmd])

ITEMS = [
    ("وای‌فای", lambda: open_panel("wifi")),
    ("شبکه", lambda: open_panel("network")),
    ("بلوتوث", lambda: open_panel("bluetooth")),
    ("نمایشگر", lambda: open_panel("display")),
    ("صدا", lambda: open_panel("sound")),
    ("برق و باتری", lambda: open_panel("power")),
    ("پس‌زمینه", lambda: open_panel("background")),
    ("تاریخ و ساعت", lambda: open_panel("datetime")),
    ("برنامه‌ها", lambda: open_panel("applications")),
    ("حریم خصوصی", lambda: open_panel("privacy")),
    ("کاربران", lambda: open_panel("user-accounts")),
    ("دربارهٔ سیستم", lambda: open_panel("info-overview")),
    ("تم تیره", lambda: subprocess.run(
        ["gsettings", "set", "org.gnome.desktop.interface",
         "color-scheme", "prefer-dark"])),
    ("تم روشن", lambda: subprocess.run(
        ["gsettings", "set", "org.gnome.desktop.interface",
         "color-scheme", "prefer-light"])),
    ("DNS افق امن", lambda: run("saman-dns-client")),
    ("مرکز سامان و به‌روزرسانی", lambda: run("saman-center")),
    ("اپ‌استور سامان", lambda: run("saman-store")),
]

class Settings(Gtk.Window):
    def __init__(self):
        super().__init__(title="تنظیمات سامان")
        self.set_default_size(520, 460)
        self.set_position(Gtk.WindowPosition.CENTER)
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        v.set_margin_top(14); v.set_margin_bottom(14)
        v.set_margin_start(16); v.set_margin_end(16)
        self.add(v)
        t = Gtk.Label()
        t.set_markup("<big><b>تنظیمات سامان</b></big>")
        v.pack_start(t, False, False, 0)
        grid = Gtk.Grid()
        grid.set_row_spacing(8); grid.set_column_spacing(8)
        grid.set_column_homogeneous(True)
        v.pack_start(grid, True, True, 0)
        for i, (name, fn) in enumerate(ITEMS):
            b = Gtk.Button(label=name)
            b.set_size_request(-1, 44)
            b.connect("clicked", lambda _b, f=fn: f())
            grid.attach(b, i % 3, i // 3, 1, 1)

if __name__ == "__main__":
    w = Settings()
    w.connect("destroy", Gtk.main_quit)
    w.show_all()
    Gtk.main()
