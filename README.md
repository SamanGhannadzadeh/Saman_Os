# Saman OS

**سامان اواس** — یک سیستم‌عامل مدرن بر پایهٔ لینوکس (اوبونتو ۲۶٫۱۰) با محیط دسکتاپ GNOME و تم Yaru، ساختهٔ سامان قنادزاده یزدی.

**Saman OS** — a modern Linux-based operating system (Ubuntu 26.10 base) with the GNOME desktop and Yaru theme, built by Saman Ghannadzadeh Yazdi.

## وضعیت | Status

- نسخهٔ فعلی: **2.0** — دسکتاپ محصول (GNOME + Yaru) روی روت‌فایل‌سیستم واقعی دیسکی، با ورود خودکار و برندینگ Saman OS.
- ایمیج زنده (Live ISO) با بوت دوگانهٔ BIOS و UEFI در بخش Releases منتشر می‌شود.

## دانلود | Download

ایمیج زنده (Live ISO) از سه راه منتشر می‌شود — هر سه، یک فایل
با یک هش SHA-256 یکسان‌اند:

1. **GitHub Releases** (راه اصلی):
   https://github.com/saman-ghannadzadeh/saman-os/releases
   — نسخهٔ ۲٫۰: فایل ISO روی گوگل درایو میزبانی می‌شود:
   https://drive.google.com/file/d/1_O4r_PWBngu0K_r7kawHJQ2J6mvFI-2O/view?usp=drivesdk
2. **آینهٔ archive.org** — برای دانلود راحت‌تر از داخل ایران،
   لینک هر نسخه در همان صفحهٔ Releases اعلام می‌شود.
3. **تورنت** — فایل `.torrent` و لینک مگنت کنار هر Release
   قرار می‌گیرد.

پیش از نصب، سلامت فایل را با `SHA256SUMS.txt` همان Release
بسنجید:

```sh
sha256sum -c SHA256SUMS.txt
```

## به‌روزرسانی | Updates

داخل خود سیستم‌عامل، ابزار `saman-updater` انتشارهای همین مخزن را بررسی می‌کند:

```sh
saman-updater check            # بررسی نسخهٔ تازه
sudo saman-updater install     # دریافت، راستی‌آزمایی هش و نصب
sudo saman-updater rollback    # برگشت به نسخهٔ قبل
```

بسته‌های به‌روزرسانی با هش SHA-256 منتشر می‌شوند و آپدیتر پیش از نصب، هش را راستی‌آزمایی و از فایل‌های جایگزین‌شونده پشتیبان می‌گیرد.

## ساختار این مخزن | Layout

- `tools/` — ابزارهای ساخت (دریافت بسته‌ها، ساخت محصول، ISO و بستهٔ به‌روزرسانی)
- `product-loader/` — اینیت لودر (بوت از دیسک و بوت زنده از ISO)
- `product-rootfs/` — لایهٔ اختصاصی Saman OS روی روت‌فایل‌سیستم اوبونتو
- `docs/` — نقشهٔ راه، گزارش شکاف‌ها و راهنمای دوال‌بوت
