#!/usr/bin/python3
# SamanOS Antivirus — the built-in antivirus of Saman OS.
# UI over /usr/bin/saman-av-scan: status, scan, quarantine,
# and the LAN management-server connection (school console).
import json
import os
import subprocess
import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

SIG_F = "/usr/share/saman-av/sigs.json"
QUAR = os.path.expanduser("~/.local/share/saman-av/quarantine")
CFG_F = os.path.expanduser("~/.config/saman-av/config.json")


def sig_version():
    try:
        return json.load(open(SIG_F, encoding="utf-8")).get(
            "version", "—")
    except Exception:
        return "—"


class App(Gtk.Window):
    def __init__(self):
        super().__init__(title="SamanOS Antivirus — آنتی‌ویروس سامان")
        self.set_default_size(560, 520)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(14)
        box.set_margin_bottom(14)
        box.set_margin_start(14)
        box.set_margin_end(14)
        self.add(box)

        title = Gtk.Label()
        title.set_markup("<b><big>🛡️ آنتی‌ویروس سامان</big></b>")
        box.pack_start(title, False, False, 0)

        self.status = Gtk.Label(label="وضعیت: آماده")
        self.status.set_xalign(0)
        box.pack_start(self.status, False, False, 0)

        self.info = Gtk.Label(
            label=f"نسخهٔ امضاها: {sig_version()} — "
                  "موتور: ClamAV یا موتور داخلی سامان")
        self.info.set_xalign(0)
        box.pack_start(self.info, False, False, 0)

        scan_btn = Gtk.Button(label="▶ اسکن سریع (خانه و دانلودها)")
        scan_btn.connect("clicked", self.on_scan)
        box.pack_start(scan_btn, False, False, 0)

        deep_btn = Gtk.Button(
            label="🔍 اسکن عمیق (کل خانه + برنامه‌های در حال اجرا + استارت‌آپ)")
        deep_btn.connect("clicked", self.on_deep_scan)
        box.pack_start(deep_btn, False, False, 0)

        act_row = Gtk.Box(spacing=8)
        act_row.pack_start(
            Gtk.Label(label="برخورد با فایل مخرب:"), False, False, 0)
        self.action_combo = Gtk.ComboBoxText()
        self.action_combo.append("quarantine", "قرنطینه (قابل برگرداندن)")
        self.action_combo.append("delete", "حذف فوری")
        current = "quarantine"
        try:
            current = json.load(open(CFG_F, encoding="utf-8")).get(
                "action", "quarantine")
        except Exception:
            pass
        self.action_combo.set_active_id(current)
        self.action_combo.connect("changed", self.on_action_changed)
        act_row.pack_start(self.action_combo, False, False, 0)
        box.pack_start(act_row, False, False, 0)

        self.results = Gtk.Label(label="")
        self.results.set_xalign(0)
        self.results.set_line_wrap(True)
        box.pack_start(self.results, False, False, 0)

        box.pack_start(Gtk.Label(label="— قرنطینه —"), False, False, 0)
        self.quar_list = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.pack_start(self.quar_list, False, False, 0)
        self.refresh_quar()

        box.pack_start(
            Gtk.Label(label="— اتصال به سرور مدیریت مرکزی (اختیاری) —"),
            False, False, 0)
        self.server_entry = Gtk.Entry()
        self.server_entry.set_placeholder_text(
            "http://192.168.1.10:8777")
        try:
            cfg = json.load(open(CFG_F, encoding="utf-8"))
            self.server_entry.set_text(cfg.get("server", ""))
        except Exception:
            pass
        box.pack_start(self.server_entry, False, False, 0)
        save_btn = Gtk.Button(label="ذخیرهٔ اتصال سرور")
        save_btn.connect("clicked", self.on_save_server)
        box.pack_start(save_btn, False, False, 0)

    def refresh_quar(self):
        for child in self.quar_list.get_children():
            self.quar_list.remove(child)
        items = []
        if os.path.isdir(QUAR):
            items = sorted(os.listdir(QUAR))
        if not items:
            self.quar_list.pack_start(
                Gtk.Label(label="قرنطینه خالی است ✓"), False, False, 0)
        for name in items:
            row = Gtk.Box(spacing=8)
            row.pack_start(Gtk.Label(label=name), True, True, 0)
            b = Gtk.Button(label="برگرداندن")
            b.connect("clicked", self.on_restore, name)
            row.pack_start(b, False, False, 0)
            self.quar_list.pack_start(row, False, False, 0)
        self.quar_list.show_all()

    def on_restore(self, _btn, name):
        src = os.path.join(QUAR, name)
        base = name.split("-", 3)[-1].replace(".quarantined", "")
        dest = os.path.join(os.path.expanduser("~"), base)
        try:
            os.replace(src, dest)
            self.status.set_text(f"وضعیت: برگردانده شد → {dest}")
        except OSError as e:
            self.status.set_text(f"وضعیت: خطا در برگرداندن ({e})")
        self.refresh_quar()

    def on_save_server(self, _btn):
        url = self.server_entry.get_text().strip()
        os.makedirs(os.path.dirname(CFG_F), exist_ok=True)
        cfg = {}
        try:
            cfg = json.load(open(CFG_F, encoding="utf-8"))
        except Exception:
            pass
        cfg["server"] = url
        cfg.setdefault("token", "school-av-2026")
        json.dump(cfg, open(CFG_F, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        self.status.set_text(
            "وضعیت: سرور مدیریت ذخیره شد — گزارش اسکن‌ها از این پس "
            "به کنسول مرکزی می‌رود" if url else "وضعیت: سرور حذف شد")

    def on_action_changed(self, combo):
        cfg = {}
        try:
            cfg = json.load(open(CFG_F, encoding="utf-8"))
        except Exception:
            pass
        cfg["action"] = combo.get_active_id()
        os.makedirs(os.path.dirname(CFG_F), exist_ok=True)
        json.dump(cfg, open(CFG_F, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        self.status.set_text(
            "وضعیت: برخورد با فایل مخرب ذخیره شد")

    def on_deep_scan(self, _btn):
        self._start_scan(["saman-av-scan", "--deep", "--json"])

    def on_scan(self, _btn):
        self._start_scan(["saman-av-scan", "--quick", "--json"])

    def _start_scan(self, cmd):
        self.status.set_text("وضعیت: در حال اسکن…")
        self.results.set_text("")

        def work():
            try:
                r = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=3600)
                data = json.loads(r.stdout.strip().splitlines()[-1])
                found = data.get("found", [])
                if found:
                    txt = f"⚠ {len(found)} یافته قرنطینه شد:\n" + \
                        "\n".join(f"• {f['path']} — {f['threat']}"
                                  for f in found)
                else:
                    txt = "✓ اسکن تمام شد — سیستم پاک است"
                GLib.idle_add(self._scan_done, txt)
            except Exception as e:
                GLib.idle_add(self._scan_done, f"خطا در اسکن: {e}")

        threading.Thread(target=work, daemon=True).start()

    def _scan_done(self, txt):
        self.status.set_text("وضعیت: اسکن کامل شد")
        self.results.set_text(txt)
        self.refresh_quar()


if __name__ == "__main__":
    win = App()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
