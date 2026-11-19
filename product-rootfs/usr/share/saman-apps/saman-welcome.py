#!/usr/bin/env python3
# Saman Welcome — the first-run intro of Saman OS.
# Shows once on the first login (autostart passes --first-run and a
# stamp file suppresses later runs); from the apps menu it always opens.
import os, subprocess, sys
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

STAMP = os.path.expanduser("~/.config/saman-welcome-done")

def run(*args):
    subprocess.Popen(list(args))

def gset(schema, key, value):
    subprocess.run(["gsettings", "set", schema, key, value],
                   capture_output=True)

class Welcome(Gtk.Window):
    def __init__(self):
        super().__init__(title="خوش آمدید به سامان او اس")
        self.set_default_size(560, 430)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.page = 0
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(18); vbox.set_margin_bottom(14)
        vbox.set_margin_start(22); vbox.set_margin_end(22)
        self.add(vbox)
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)
        vbox.pack_start(self.stack, True, True, 0)
        nav = Gtk.Box(spacing=8)
        self.dots = Gtk.Label()
        self.back_btn = Gtk.Button(label="قبلی")
        self.back_btn.connect("clicked", lambda *_: self.go(-1))
        self.next_btn = Gtk.Button(label="بعدی")
        self.next_btn.get_style_context().add_class("suggested-action")
        self.next_btn.connect("clicked", lambda *_: self.go(1))
        nav.pack_start(self.dots, False, False, 0)
        nav.pack_end(self.next_btn, False, False, 0)
        nav.pack_end(self.back_btn, False, False, 0)
        vbox.pack_start(nav, False, False, 0)
        self.pages = [self.page_welcome(), self.page_look(),
                      self.page_dns(), self.page_update(), self.page_done()]
        for i, p in enumerate(self.pages):
            self.stack.add_named(p, str(i))
        self.refresh()

    def page_box(self, title, body):
        b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        t = Gtk.Label()
        t.set_markup("<big><b>%s</b></big>" % title)
        t.set_line_wrap(True)
        b.pack_start(t, False, False, 0)
        l = Gtk.Label(label=body)
        l.set_line_wrap(True)
        l.set_xalign(0)
        b.pack_start(l, False, False, 0)
        return b

    def page_welcome(self):
        b = self.page_box("سامان او اس — خوش آمدید",
            "این سیستم‌عامل بر پایهٔ اوبونتو ۲۶٫۱۰ ساخته شده: مدرن، فارسی و آمادهٔ کار.\n"
            "در چند قدم کوتاه، ظاهر و اتصالتان را تنظیم می‌کنیم.")
        try:
            v = open("/usr/lib/saman-os/VERSION").read().strip()
            l = Gtk.Label(label="نسخهٔ %s" % v)
            b.pack_start(l, False, False, 0)
        except Exception:
            pass
        return b

    def page_look(self):
        b = self.page_box("ظاهر",
            "تم روشن یا تیره را انتخاب کنید (بعداً از «تنظیمات سامان» هم می‌شود عوضش کرد).")
        row = Gtk.Box(spacing=8)
        bl = Gtk.Button(label="روشن")
        bl.connect("clicked", lambda *_: gset(
            "org.gnome.desktop.interface", "color-scheme", "prefer-light"))
        bd = Gtk.Button(label="تیره")
        bd.connect("clicked", lambda *_: gset(
            "org.gnome.desktop.interface", "color-scheme", "prefer-dark"))
        row.pack_start(bl, False, False, 0)
        row.pack_start(bd, False, False, 0)
        b.pack_start(row, False, False, 0)
        return b

    def page_dns(self):
        b = self.page_box("DNS گیمینگ افق امن",
            "اگر گیمر هستید، DNS افق امن را روی اتصالتان بگذارید تا لوک‌اپ‌های بازی "
            "سریع و تمیز انجام شود. این کار اختیاری است و هر وقت خواستید برمی‌گردد.")
        btn = Gtk.Button(label="باز کردن تنظیم DNS")
        btn.connect("clicked", lambda *_: run("saman-dns-client"))
        b.pack_start(btn, False, False, 0)
        return b

    def page_update(self):
        b = self.page_box("به‌روزرسانی",
            "سامان او اس از مخزن رسمی خودش در گیت‌هاب به‌روز می‌شود. "
            "همین حالا یک بررسی بکنید:")
        btn = Gtk.Button(label="بررسی به‌روزرسانی")
        btn.connect("clicked", lambda *_: run("saman-center"))
        b.pack_start(btn, False, False, 0)
        return b

    def page_done(self):
        b = self.page_box("تمام شد — بفرمایید داخل",
            "از اپ‌استور سامان برنامه نصب کنید، از تنظیمات سامان سیستم را دست‌کاری کنید "
            "و اگر گیمرید، اپ تست پینگ را امتحان کنید.\nموفق باشید!")
        btn = Gtk.Button(label="باز کردن اپ‌استور سامان")
        btn.connect("clicked", lambda *_: run("saman-store"))
        b.pack_start(btn, False, False, 0)
        return b

    def go(self, d):
        if d > 0 and self.page == len(self.pages) - 1:
            self.finish()
            return
        self.page = max(0, min(len(self.pages) - 1, self.page + d))
        self.refresh()

    def refresh(self):
        self.stack.set_visible_child_name(str(self.page))
        self.back_btn.set_sensitive(self.page > 0)
        last = self.page == len(self.pages) - 1
        self.next_btn.set_label("شروع" if last else "بعدی")
        self.dots.set_text(" ".join(
            "●" if i == self.page else "○" for i in range(len(self.pages))))

    def finish(self):
        os.makedirs(os.path.dirname(STAMP), exist_ok=True)
        open(STAMP, "w").write("done\n")
        self.destroy()

if __name__ == "__main__":
    if "--first-run" in sys.argv and os.path.exists(STAMP):
        sys.exit(0)
    w = Welcome()
    w.connect("destroy", Gtk.main_quit)
    w.show_all()
    Gtk.main()
