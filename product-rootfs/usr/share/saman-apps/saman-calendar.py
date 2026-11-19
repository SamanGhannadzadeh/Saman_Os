#!/usr/bin/env python3
# Saman Calendar — a Jalali (Persian) month calendar.
import calendar as _cal
from datetime import date
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

# --- Saman glass: prgname (blur whitelist) + shared template CSS ---
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

def jalali_month_len(jy, jm):
    if jm <= 6:
        return 31
    if jm <= 11:
        return 30
    leap, _gy, _m = _jal_cal(jy)
    return 30 if leap == 0 else 29

FA_MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
             "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]


class Cal(Gtk.Window):
    def __init__(self):
        super().__init__(title="تقویم سامان")
        self.set_default_size(380, 340)
        self.set_position(Gtk.WindowPosition.CENTER)
        t = date.today()
        self.jy, self.jm, self.jd = g2j(t.year, t.month, t.day)
        self.today = (self.jy, self.jm, self.jd)
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        v.set_margin_top(12); v.set_margin_bottom(12)
        v.set_margin_start(14); v.set_margin_end(14)
        self.add(v)
        nav = Gtk.Box(spacing=8)
        prev_b = Gtk.Button(label="‹ ماه قبل")
        prev_b.connect("clicked", lambda *_: self.move(-1))
        next_b = Gtk.Button(label="ماه بعد ›")
        next_b.connect("clicked", lambda *_: self.move(1))
        self.title = Gtk.Label()
        nav.pack_start(prev_b, False, False, 0)
        nav.pack_start(self.title, True, True, 0)
        nav.pack_start(next_b, False, False, 0)
        v.pack_start(nav, False, False, 0)
        self.grid = Gtk.Grid()
        self.grid.set_row_spacing(4); self.grid.set_column_spacing(4)
        self.grid.set_column_homogeneous(True)
        v.pack_start(self.grid, True, True, 0)
        self.draw()

    def move(self, d):
        self.jm += d
        if self.jm < 1:
            self.jm = 12; self.jy -= 1
        if self.jm > 12:
            self.jm = 1; self.jy += 1
        self.draw()

    def draw(self):
        for c in self.grid.get_children():
            self.grid.remove(c)
        self.title.set_markup("<b>%s %d</b>" % (FA_MONTHS[self.jm - 1], self.jy))
        for i, wd in enumerate(["ش", "ی", "د", "س", "چ", "پ", "ج"]):
            l = Gtk.Label()
            l.set_markup("<b>%s</b>" % wd)
            self.grid.attach(l, i, 0, 1, 1)
        gy, gm, gd = j2g(self.jy, self.jm, 1)
        # Python weekday: Mon=0..Sun=6; Persian week starts Saturday.
        first_col = (date(gy, gm, gd).weekday() + 2) % 7
        n = jalali_month_len(self.jy, self.jm)
        for day in range(1, n + 1):
            pos = first_col + day - 1
            l = Gtk.Label(label=str(day))
            if (self.jy, self.jm, day) == self.today:
                l.set_markup("<b><span background='#3584e4' foreground='white'> %d </span></b>" % day)
            self.grid.attach(l, pos % 7, 1 + pos // 7, 1, 1)
        self.grid.show_all()

if __name__ == "__main__":
    w = Cal()
    w.connect("destroy", Gtk.main_quit)
    w.show_all()
    Gtk.main()
