#!/usr/bin/env python3
# Saman Clock — Tehran + world clocks, stopwatch and timer.
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

# --- Saman glass: prgname (blur whitelist) + shared template CSS ---
from gi.repository import Gdk, GLib
GLib.set_prgname("saman-clock")
try:
    _p = Gtk.CssProvider()
    _p.load_from_path("/usr/share/saman-os/saman-glass.css")
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), _p,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
except Exception:
    pass


CITIES = [("تهران", "Asia/Tehran"), ("دبی", "Asia/Dubai"),
          ("فرانکفورت", "Europe/Berlin"), ("لندن", "Europe/London"),
          ("لس‌آنجلس", "America/Los_Angeles")]

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

def jalali_month_len(jy, jm):
    if jm <= 6:
        return 31
    if jm <= 11:
        return 30
    leap, _gy, _m = _jal_cal(jy)
    return 30 if leap == 0 else 29

FA_MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
             "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]

class Clock(Gtk.Window):
    def __init__(self):
        super().__init__(title="ساعت سامان")
        self.set_default_size(430, 400)
        self.set_position(Gtk.WindowPosition.CENTER)
        nb = Gtk.Notebook()
        self.add(nb)
        # --- clocks tab
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(16); box.set_margin_start(18); box.set_margin_end(18)
        self.big = Gtk.Label()
        self.big.set_markup("<span size='42000'><b>--:--:--</b></span>")
        box.pack_start(self.big, False, False, 0)
        self.date_lbl = Gtk.Label()
        box.pack_start(self.date_lbl, False, False, 0)
        self.rows = {}
        for name, _tz in CITIES[1:]:
            l = Gtk.Label(label=name)
            l.set_xalign(0)
            box.pack_start(l, False, False, 0)
            self.rows[name] = l
        nb.append_page(box, Gtk.Label(label="ساعت‌ها"))
        # --- stopwatch tab
        sw = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        sw.set_margin_top(16); sw.set_margin_start(18); sw.set_margin_end(18)
        self.sw_lbl = Gtk.Label()
        self.sw_lbl.set_markup("<span size='30000'><b>۰۰:۰۰٫۰</b></span>")
        sw.pack_start(self.sw_lbl, False, False, 0)
        row = Gtk.Box(spacing=8)
        self.sw_btn = Gtk.Button(label="شروع")
        self.sw_btn.connect("clicked", self.sw_toggle)
        rb = Gtk.Button(label="صفر")
        rb.connect("clicked", self.sw_reset)
        row.pack_start(self.sw_btn, False, False, 0)
        row.pack_start(rb, False, False, 0)
        sw.pack_start(row, False, False, 0)
        nb.append_page(sw, Gtk.Label(label="کرونومتر"))
        self.sw_start = None
        self.sw_elapsed = 0.0
        # --- timer tab
        tm = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        tm.set_margin_top(16); tm.set_margin_start(18); tm.set_margin_end(18)
        self.tm_lbl = Gtk.Label()
        self.tm_lbl.set_markup("<span size='30000'><b>۰۰:۰۰</b></span>")
        tm.pack_start(self.tm_lbl, False, False, 0)
        trow = Gtk.Box(spacing=8)
        trow.pack_start(Gtk.Label(label="دقیقه:"), False, False, 0)
        self.tm_min = Gtk.SpinButton.new_with_range(1, 999, 1)
        self.tm_min.set_value(5)
        trow.pack_start(self.tm_min, False, False, 0)
        self.tm_btn = Gtk.Button(label="شروع تایمر")
        self.tm_btn.connect("clicked", self.tm_toggle)
        trow.pack_start(self.tm_btn, False, False, 0)
        tm.pack_start(trow, False, False, 0)
        nb.append_page(tm, Gtk.Label(label="تایمر"))
        self.tm_end = None
        GLib.timeout_add(200, self.tick)

    def tick(self):
        now = datetime.now(ZoneInfo("Asia/Tehran"))
        self.big.set_markup("<span size='42000'><b>%s</b></span>"
                            % now.strftime("%H:%M:%S"))
        jy, jm, jd = g2j(now.year, now.month, now.day)
        self.date_lbl.set_text("%d %s %d" % (jd, FA_MONTHS[jm - 1], jy))
        for name, tz in CITIES[1:]:
            t = datetime.now(ZoneInfo(tz))
            self.rows[name].set_text("%s — %s" % (name, t.strftime("%H:%M")))
        if self.sw_start is not None:
            e = self.sw_elapsed + (time.time() - self.sw_start)
            self.sw_lbl.set_markup("<span size='30000'><b>%02d:%05.1f</b></span>"
                                   % (int(e) // 60, e % 60))
        if self.tm_end is not None:
            left = self.tm_end - time.time()
            if left <= 0:
                self.tm_end = None
                self.tm_btn.set_label("شروع تایمر")
                self.tm_lbl.set_markup("<span size='30000'><b>تمام شد!</b></span>")
            else:
                self.tm_lbl.set_markup("<span size='30000'><b>%02d:%02d</b></span>"
                                       % (int(left) // 60, int(left) % 60))
        return True

    def sw_toggle(self, _b):
        if self.sw_start is None:
            self.sw_start = time.time()
            self.sw_btn.set_label("توقف")
        else:
            self.sw_elapsed += time.time() - self.sw_start
            self.sw_start = None
            self.sw_btn.set_label("شروع")

    def sw_reset(self, _b):
        self.sw_start = None
        self.sw_elapsed = 0.0
        self.sw_btn.set_label("شروع")
        self.sw_lbl.set_markup("<span size='30000'><b>۰۰:۰۰٫۰</b></span>")

    def tm_toggle(self, _b):
        if self.tm_end is None:
            self.tm_end = time.time() + self.tm_min.get_value() * 60
            self.tm_btn.set_label("لغو")
        else:
            self.tm_end = None
            self.tm_btn.set_label("شروع تایمر")

if __name__ == "__main__":
    w = Clock()
    w.connect("destroy", Gtk.main_quit)
    w.show_all()
    Gtk.main()
