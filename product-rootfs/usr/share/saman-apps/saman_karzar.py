#!/usr/bin/python3
# Saman Karzar — the petition app for Saman OS.
import subprocess

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

URL = "https://www.karzar.net/358363"


class Karzar(Gtk.Window):
    def __init__(self):
        super().__init__(title="کارزار — Saman Karzar")
        self.set_default_size(520, 330)
        self.set_border_width(16)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.add(box)
        t = Gtk.Label()
        t.set_markup("<b><big>مطالبهٔ پایان تأخیر نجومی در بازی‌های آنلاین</big></b>")
        t.set_line_wrap(True)
        box.pack_start(t, False, False, 0)
        body = Gtk.Label(label="و رفع محدودیت اینترنت — کارزار مردمی گیمرهای ایران.\n"
                               "کد رهگیری: ۳۵۸۳۶۳   •   مهلت امضا: ۱۳ اردیبهشت ۱۴۰۶")
        body.set_line_wrap(True)
        box.pack_start(body, False, False, 0)
        sign = Gtk.Button(label="✍️  امضای کارزار")
        sign.connect("clicked", lambda *_: subprocess.Popen(["xdg-open", URL]))
        box.pack_start(sign, False, False, 0)
        ig = Gtk.Button(label="📷  صفحهٔ اینستاگرام — ghannadzadeh_ir")
        ig.connect("clicked", lambda *_: subprocess.Popen(
            ["xdg-open", "https://www.instagram.com/ghannadzadeh_ir"]))
        box.pack_start(ig, False, False, 0)
        note = Gtk.Label(label="هر امضا یک قدم است؛ لینک کارزار را برای هم‌تیمی‌هایت بفرست.")
        note.set_line_wrap(True)
        box.pack_start(note, False, False, 0)


win = Karzar()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
