#!/usr/bin/env python3
# Saman Store — a curated app store over the Ubuntu archives (apt).
# Install/remove runs through pkexec; needs internet.
import subprocess, threading
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

CATALOG = [
    ("VLC", "vlc", "پخش‌کنندهٔ ویدئو و موسیقی", "رسانه"),
    ("GIMP", "gimp", "ویرایش عکس", "رسانه"),
    ("Kdenlive", "kdenlive", "ویرایش ویدئو", "رسانه"),
    ("OBS Studio", "obs-studio", "ضبط صفحه و استریم", "رسانه"),
    ("Audacity", "audacity", "ویرایش صدا", "رسانه"),
    ("Inkscape", "inkscape", "طراحی برداری", "رسانه"),
    ("HandBrake", "handbrake", "تبدیل فرمت ویدئو", "رسانه"),
    ("Celluloid", "celluloid", "پخش‌کنندهٔ سبک ویدئو", "رسانه"),
    ("Telegram Desktop", "telegram-desktop", "پیام‌رسان تلگرام", "اینترنت"),
    ("qBittorrent", "qbittorrent", "دانلود تورنت", "اینترنت"),
    ("FileZilla", "filezilla", "انتقال فایل FTP", "اینترنت"),
    ("Remmina", "remmina", "ریموت دسکتاپ", "اینترنت"),
    ("LibreOffice Writer", "libreoffice-writer", "واژه‌پرداز", "اداری"),
    ("LibreOffice Calc", "libreoffice-calc", "صفحه‌گسترده", "اداری"),
    ("LibreOffice Impress", "libreoffice-impress", "ارائه", "اداری"),
    ("Geany", "geany", "ویرایشگر کد سبک", "برنامه‌نویسی"),
    ("GNOME Tweaks", "gnome-tweaks", "دست‌کاری ظاهر گنوم", "ابزار"),
    ("Extension Manager", "gnome-shell-extension-manager", "مدیریت افزونه‌های گنوم", "ابزار"),
    ("Synaptic", "synaptic", "مدیر بستهٔ پیشرفته", "ابزار"),
]

def installed(pkg):
    r = subprocess.run(["dpkg-query", "-W", "-f=${Status}", pkg],
                       capture_output=True, text=True)
    return "install ok installed" in r.stdout

class Store(Gtk.Window):
    def __init__(self):
        super().__init__(title="اپ‌استور سامان")
        self.set_default_size(620, 520)
        self.set_position(Gtk.WindowPosition.CENTER)
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        v.set_margin_top(12); v.set_margin_bottom(12)
        v.set_margin_start(14); v.set_margin_end(14)
        self.add(v)
        t = Gtk.Label()
        t.set_markup("<big><b>اپ‌استور سامان</b></big>")
        v.pack_start(t, False, False, 0)
        note = Gtk.Label(label="نصب و حذف از مخزن رسمی اوبونتو انجام می‌شود و اینترنت می‌خواهد.")
        note.set_line_wrap(True)
        v.pack_start(note, False, False, 0)
        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text("جستجو…")
        self.search.connect("search-changed", lambda *_: self.fill())
        v.pack_start(self.search, False, False, 0)
        sw = Gtk.ScrolledWindow()
        self.listbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        sw.add(self.listbox)
        v.pack_start(sw, True, True, 0)
        self.status = Gtk.Label(label="")
        v.pack_start(self.status, False, False, 0)
        self.fill()

    def fill(self):
        for c in self.listbox.get_children():
            self.listbox.remove(c)
        q = self.search.get_text().strip()
        for name, pkg, desc, _cat in CATALOG:
            if q and q.lower() not in name.lower() and q not in desc:
                continue
            row = Gtk.Box(spacing=10)
            info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            n = Gtk.Label()
            n.set_markup("<b>%s</b>" % name)
            n.set_xalign(0)
            d = Gtk.Label(label=desc)
            d.set_xalign(0)
            info.pack_start(n, False, False, 0)
            info.pack_start(d, False, False, 0)
            row.pack_start(info, True, True, 0)
            btn = Gtk.Button(label="حذف" if installed(pkg) else "نصب")
            btn.connect("clicked", self.on_action, pkg, btn)
            row.pack_start(btn, False, False, 0)
            self.listbox.pack_start(row, False, False, 0)
        self.listbox.show_all()

    def on_action(self, btn_widget, pkg, btn):
        do_remove = btn.get_label() == "حذف"
        btn.set_sensitive(False)
        self.status.set_text(("در حال حذف %s…" if do_remove else "در حال نصب %s…") % pkg)
        def work():
            cmd = ["pkexec", "apt-get", "remove", "-y", pkg] if do_remove else \
                  ["pkexec", "sh", "-c",
                   "apt-get update -qq && apt-get install -y %s" % pkg]
            r = subprocess.run(cmd, capture_output=True, text=True)
            ok = r.returncode == 0
            GLib.idle_add(self.done, pkg, ok, do_remove)
        threading.Thread(target=work, daemon=True).start()

    def done(self, pkg, ok, was_remove):
        self.status.set_text("%s %s" % (pkg, "انجام شد ✓" if ok else "ناموفق بود ✗"))
        self.fill()
        return False

if __name__ == "__main__":
    w = Store()
    w.connect("destroy", Gtk.main_quit)
    w.show_all()
    Gtk.main()
