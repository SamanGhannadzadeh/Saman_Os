#!/usr/bin/env python3
# Saman Widgets — desktop widget layer in the Saman OS template:
# one glass column (Jalali clock, mini calendar, system status,
# shortcuts) pinned to the desktop, blurred by blur-my-shell
# like every other surface of the template.
import os
import time
from datetime import date, datetime
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk

GLib.set_prgname("saman-widgets")
from gi.repository import Gdk, GLib
GLib.set_prgname("saman-calendar")
try:
    _p = Gtk.CssProvider()
    _p.load_from_path("/usr/share/saman-os/saman-glass.css")
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), _p,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
except Exception:
    pass


BREAKS = [-61, 9, 38, 199, 426, 686, 756, 818, 1111, 1181, 1210,
          1635, 2060, 2097, 2192, 2262, 2324, 2394, 2456, 3178]

def _div(a, b):
    q = abs(a) // abs(b)
    return q if (a < 0) == (b < 0) else -q

def _mod(a, b):
    return a - _div(a, b) * b

def _jal_cal(jy):
    gy = jy + 621
    leap_j = -14
    jp = BREAKS[0]
    jump = 0
    for nxt in BREAKS[1:]:
        jump = nxt - jp
        if jy < nxt:
            break
        leap_j += _div(jump, 33) * 8 + _div(_mod(jump, 33), 4)
        jp = nxt
    n = jy - jp
    leap_j += _div(n, 33) * 8 + _div(_mod(n, 33) + 3, 4)
    if _mod(jump, 33) == 4 and jump - n == 4:
        leap_j += 1
    leap_g = _div(gy, 4) - _div((_div(gy, 100) + 1) * 3, 4) - 150
    march = 20 + leap_j - leap_g
    if jump - n < 6:
        n = n - jump + _div(jump + 4, 33) * 33
    leap = _mod(_mod(n + 1, 33) - 1, 4)
    if leap == -1:
        leap = 4
    return leap, gy, march

def _g2d(gy, gm, gd):
    d = _div((gy + _div(gm - 8, 6) + 100100) * 1461, 4) \
        + _div(153 * _mod(gm + 9, 12) + 2, 5) + gd - 34840408
    d = d - _div(_div(gy + 100100 + _div(gm - 8, 6), 100) * 3, 4) + 752
    return d

def _d2g(jdn):
    j = 4 * jdn + 139361631
    j += _div(_div(4 * jdn + 183187720, 146097) * 3, 4) * 4 - 3908
    i = _div(_mod(j, 1461), 4) * 5 + 308
    gd = _div(_mod(i, 153), 5) + 1
    gm = _mod(_div(i, 153), 12) + 1
    gy = _div(j, 1461) - 100100 + _div(8 - gm, 6)
    return gy, gm, gd

def g2j(gy, gm, gd):
    jdn = _g2d(gy, gm, gd)
    gy2 = _d2g(jdn)[0]
    jy = gy2 - 621
    leap, _gy, march = _jal_cal(jy)
    k = jdn - _g2d(gy2, 3, march)
    if k >= 0:
        if k <= 185:
            return jy, 1 + _div(k, 31), _mod(k, 31) + 1
        k -= 186
    else:
        jy -= 1
        k += 179
        if leap == 1:
            k += 1
    return jy, 7 + _div(k, 30), _mod(k, 30) + 1

def j2g(jy, jm, jd):
    _leap, gy, march = _jal_cal(jy)
    jdn = _g2d(gy, 3, march) + (jm - 1) * 31 - _div(jm, 7) * (jm - 7) + jd - 1
    return _d2g(jdn)

FA_WEEKDAYS = ["ش", "ی", "د", "س", "چ", "پ", "ج"]


def fa_digits(s):
    return str(s).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def cpu_percent(prev):
    try:
        parts = [int(x) for x in open("/proc/stat").readline().split()[1:]]
    except Exception:
        return 0, None
    idle = parts[3] + parts[4]
    total = sum(parts)
    if prev is None:
        return 0, (idle, total)
    didle = idle - prev[0]
    dtotal = total - prev[1]
    if dtotal <= 0:
        return 0, (idle, total)
    return round(100 * (1 - didle / dtotal)), (idle, total)


def mem_line():
    info = {}
    try:
        for line in open("/proc/meminfo"):
            k, v = line.split(":")
            info[k] = int(v.split()[0])
        used = (info["MemTotal"] - info["MemAvailable"]) / 1048576
        total = info["MemTotal"] / 1048576
        return f"رم: {used:.1f} از {total:.1f} گیگابایت"
    except Exception:
        return "رم: —"


class Widgets(Gtk.Window):
    def __init__(self):
        super().__init__(title="Saman Widgets")
        self.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_below(True)
        self.get_style_context().add_class("saman-glass")
        try:
            p = Gtk.CssProvider()
            p.load_from_path("/usr/share/saman-os/saman-glass.css")
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(), p,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        except Exception:
            pass
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        root.set_margin_top(10); root.set_margin_bottom(10)
        root.set_margin_start(10); root.set_margin_end(10)
        self.add(root)
        # --- clock card ---
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        card.get_style_context().add_class("saman-card")
        self.clock_lbl = Gtk.Label()
        self.clock_lbl.get_style_context().add_class("saman-big")
        self.date_lbl = Gtk.Label()
        self.date_lbl.get_style_context().add_class("saman-mid")
        card.pack_start(self.clock_lbl, False, False, 0)
        card.pack_start(self.date_lbl, False, False, 0)
        root.pack_start(card, False, False, 0)
        # --- mini calendar card ---
        cal_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        cal_card.get_style_context().add_class("saman-card")
        self.cal_title = Gtk.Label()
        self.cal_title.get_style_context().add_class("saman-title")
        cal_card.pack_start(self.cal_title, False, False, 0)
        self.cal_grid = Gtk.Grid()
        self.cal_grid.set_column_homogeneous(True)
        self.cal_grid.set_row_spacing(2)
        cal_card.pack_start(self.cal_grid, False, False, 0)
        root.pack_start(cal_card, False, False, 0)
        # --- system card ---
        sys_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        sys_card.get_style_context().add_class("saman-card")
        self.cpu_lbl = Gtk.Label(label="پردازنده: —")
        self.mem_lbl = Gtk.Label()
        for lbl in (self.cpu_lbl, self.mem_lbl):
            lbl.set_halign(Gtk.Align.START)
            sys_card.pack_start(lbl, False, False, 0)
        root.pack_start(sys_card, False, False, 0)
        # --- shortcuts card ---
        link_card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        link_card.get_style_context().add_class("saman-card")
        for label, cmd in (
            ("✍️ کارزار", "xdg-open https://www.karzar.net/358363"),
            ("🌐 پنل DNS", "ofogheamn-panel-launch"),
            ("🛡️ آنتی‌ویروس", "saman-antivirus"),
        ):
            b = Gtk.Button(label=label)
            b.get_style_context().add_class("saman-chip")
            b.connect("clicked", lambda _b, c=cmd: GLib.spawn_command_line_async(c))
            link_card.pack_start(b, True, True, 0)
        root.pack_start(link_card, False, False, 0)
        self._cpu_prev = None
        self.refresh_calendar()
        self.tick()
        GLib.timeout_add_seconds(1, self.tick)
        self.connect("realize", self._place)

    def _place(self, *_):
        scr = Gdk.Screen.get_default()
        mon = scr.get_monitor_at_point(0, 0)
        geo = scr.get_monitor_workarea(mon)
        w, _h = self.get_size()
        self.move(geo.x + geo.width - w - 18, geo.y + 52)

    def refresh_calendar(self):
        t = date.today()
        jy, jm, jd = g2j(t.year, t.month, t.day)
        self.cal_title.set_text(f"{FA_MONTHS[jm - 1]} {fa_digits(jy)}")
        for child in self.cal_grid.get_children():
            self.cal_grid.remove(child)
        for i, wd in enumerate(FA_WEEKDAYS):
            lbl = Gtk.Label(label=wd)
            lbl.get_style_context().add_class("saman-title")
            self.cal_grid.attach(lbl, 6 - i, 0, 1, 1)
        # First weekday of the Jalali month (Sat=0 .. Fri=6)
        gy, gm, gd = j2g(jy, jm, 1)
        first_wd = (date(gy, gm, gd).weekday() + 2) % 7
        length = jalali_month_len(jy, jm)
        for d in range(1, length + 1):
            pos = first_wd + d - 1
            lbl = Gtk.Label(label=fa_digits(d))
            ctx = lbl.get_style_context()
            ctx.add_class("saman-today" if d == jd else "saman-cell")
            self.cal_grid.attach(lbl, 6 - (pos % 7), pos // 7 + 1, 1, 1)
        self.cal_grid.show_all()

    def tick(self):
        now = datetime.now()
        self.clock_lbl.set_text(
            fa_digits(now.strftime("%H:%M:%S")))
        t = date.today()
        jy, jm, jd = g2j(t.year, t.month, t.day)
        self.date_lbl.set_text(
            f"{fa_digits(jd)} {FA_MONTHS[jm - 1]} {fa_digits(jy)}")
        pct, self._cpu_prev = cpu_percent(self._cpu_prev)
        self.cpu_lbl.set_text(f"پردازنده: {fa_digits(pct)}٪")
        self.mem_lbl.set_text(mem_line())
        return True


if __name__ == "__main__":
    w = Widgets()
    w.connect("destroy", Gtk.main_quit)
    w.show_all()
    Gtk.main()
