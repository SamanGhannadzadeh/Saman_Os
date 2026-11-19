#!/usr/bin/python3
# Saman DNS Client — point this machine at an Ofogheamn gaming DNS.
import subprocess
import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib


def active_connection():
    try:
        r = subprocess.run(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show", "--active"],
                           capture_output=True, text=True, timeout=8)
        for line in r.stdout.splitlines():
            name, _, typ = line.partition(":")
            if "wireless" in typ or "ethernet" in typ:
                return name
    except Exception:
        pass
    return ""


def current_dns():
    try:
        r = subprocess.run(["resolvectl", "dns"], capture_output=True, text=True, timeout=8)
        return r.stdout.strip() or "نامشخص"
    except Exception:
        return "نامشخص"


class DnsClient(Gtk.Window):
    def __init__(self):
        super().__init__(title="DNS افق امن — Saman DNS Client")
        self.set_default_size(520, 330)
        self.set_border_width(14)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(box)
        t = Gtk.Label()
        t.set_markup("<b>تنظیم DNS گیمینگ افق امن روی این سیستم</b>")
        t.set_halign(Gtk.Align.START)
        box.pack_start(t, False, False, 0)
        self.now = Gtk.Label(label=f"DNS فعلی: {current_dns()}")
        self.now.set_halign(Gtk.Align.START)
        box.pack_start(self.now, False, False, 0)
        box.pack_start(Gtk.Label(label="آدرس سرور DNS افق امن:"), False, False, 0)
        self.entry = Gtk.Entry(text="127.0.0.1")
        box.pack_start(self.entry, False, False, 0)
        apply_btn = Gtk.Button(label="✅  اعمال DNS روی اتصال فعال")
        apply_btn.connect("clicked", self.on_apply)
        box.pack_start(apply_btn, False, False, 0)
        reset_btn = Gtk.Button(label="↩️  برگرداندن به حالت خودکار (DHCP)")
        reset_btn.connect("clicked", self.on_reset)
        box.pack_start(reset_btn, False, False, 0)
        self.out = Gtk.Label(label="")
        self.out.set_line_wrap(True)
        self.out.set_halign(Gtk.Align.START)
        box.pack_start(self.out, True, True, 0)

    def run_bg(self, argv, done):
        def work():
            try:
                r = subprocess.run(argv, capture_output=True, text=True, timeout=60)
                text = (r.stdout + r.stderr).strip()
            except Exception as exc:
                text = str(exc)
            GLib.idle_add(done, text)
        threading.Thread(target=work, daemon=True).start()

    def _apply(self, dns_value):
        conn = active_connection()
        if not conn:
            self.out.set_text("اتصال فعالی پیدا نشد")
            return
        self.out.set_text("در حال اعمال...")
        cmds = ["pkexec", "nmcli", "connection", "modify", conn,
                "ipv4.dns", dns_value, "ipv4.ignore-auto-dns",
                "no" if dns_value == "" else "yes"]
        self.run_bg(cmds, lambda t: (
            subprocess.run(["nmcli", "connection", "up", conn],
                           capture_output=True, timeout=30),
            self.out.set_text("انجام شد. " + (t or "")),
            self.now.set_text(f"DNS فعلی: {current_dns()}")))

    def on_apply(self, *_):
        ip = self.entry.get_text().strip()
        if ip:
            self._apply(ip)

    def on_reset(self, *_):
        self._apply("")


win = DnsClient()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
