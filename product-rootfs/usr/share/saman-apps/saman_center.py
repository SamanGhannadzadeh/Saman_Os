#!/usr/bin/python3
# Saman Center — hub for Saman OS: system info, updater, links.
import subprocess
import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib


def os_info():
    info = {}
    try:
        for line in open("/usr/lib/os-release"):
            if "=" in line:
                k, v = line.strip().split("=", 1)
                info[k] = v.strip('"')
    except OSError:
        pass
    try:
        with open("/usr/lib/saman-os/VERSION") as fh:
            info["SAMAN_VERSION"] = fh.read().strip()
    except OSError:
        info["SAMAN_VERSION"] = "?"
    info["KERNEL"] = subprocess.run(["uname", "-r"], capture_output=True,
                                    text=True).stdout.strip()
    return info


class Center(Gtk.Window):
    def __init__(self):
        super().__init__(title="مرکز سامان — Saman Center")
        self.set_default_size(520, 420)
        self.set_border_width(14)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(box)

        info = os_info()
        title = Gtk.Label()
        title.set_markup(f"<b><big>{info.get('PRETTY_NAME', 'Saman OS')}</big></b>")
        title.set_halign(Gtk.Align.START)
        box.pack_start(title, False, False, 0)
        sub = Gtk.Label(label=f"نسخهٔ سامان: {info.get('SAMAN_VERSION')}   •   "
                              f"کرنل: {info.get('KERNEL')}   •   "
                              f"پایه: {info.get('VERSION_ID', '')}")
        sub.set_halign(Gtk.Align.START)
        box.pack_start(sub, False, False, 0)

        self.out = Gtk.Label(label="")
        self.out.set_halign(Gtk.Align.START)
        self.out.set_line_wrap(True)

        def btn(label, fn):
            b = Gtk.Button(label=label)
            b.connect("clicked", fn)
            box.pack_start(b, False, False, 0)
            return b

        btn("🔄  بررسی به‌روزرسانی سامان او‌اس", self.on_check)
        btn("⬆️  نصب به‌روزرسانی (با تأیید مدیر)", self.on_install)
        btn("🌐  پنل مدیریت DNS افق امن", lambda *_: self.open_url("http://127.0.0.1:8080"))
        btn("🎮  تست پینگ گیمینگ", lambda *_: subprocess.Popen(["saman-nettest"]))
        btn("🛡️  SamanOS Antivirus", lambda *_: subprocess.Popen(["saman-antivirus"]))
        btn("✍️  صفحهٔ کارزار — امضای کارزار", lambda *_: self.open_url("https://www.karzar.net/358363"))
        box.pack_start(self.out, True, True, 0)

    def open_url(self, url):
        subprocess.Popen(["xdg-open", url])

    def run_bg(self, argv, done):
        def work():
            try:
                r = subprocess.run(argv, capture_output=True, text=True, timeout=300)
                text = (r.stdout + r.stderr).strip()
            except Exception as exc:
                text = str(exc)
            GLib.idle_add(done, text)
        threading.Thread(target=work, daemon=True).start()

    def on_check(self, *_):
        self.out.set_text("در حال بررسی...")
        self.run_bg(["saman-updater", "check"],
                    lambda t: self.out.set_text(t or "پاسخی نیامد"))

    def on_install(self, *_):
        self.out.set_text("در حال نصب به‌روزرسانی... (ممکن است طول بکشد)")
        self.run_bg(["pkexec", "saman-updater", "install"],
                    lambda t: self.out.set_text(t or "تمام شد"))


win = Center()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
