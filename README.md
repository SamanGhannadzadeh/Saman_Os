# Saman OS

**سامان اواس** — یک سیستم‌عامل مدرن بر پایهٔ لینوکس (اوبونتو ۲۶٫۱۰) با محیط دسکتاپ GNOME و طراحی شیشه‌ای اختصاصی، ساختهٔ سامان قنادزاده یزدی.

**Saman OS** — a modern Linux-based operating system (Ubuntu 26.10 base) with the GNOME desktop and a custom glass design, built by Saman Ghannadzadeh Yazdi.

## وضعیت | Status

- نسخهٔ فعلی: **4.0** — نسخهٔ سازگاری با سخت‌افزار: لودر زنده با ۵۴ ماژول ذخیره‌سازی، شناسایی خودکار سخت‌افزار و انتظار/تلاشِ دوباره برای دیده‌شدن دیسک‌ها (رفع مشکل بوت ۳٫۱ روی برخی لپ‌تاپ‌ها)، طراحی شیشه‌ای ۳٫۵، ویزارد اینتروی اجرای اول و ۱٬۹۲۵ بسته؛ آنتی‌ویروس SamanOS، نصاب دوال‌بوت با رمزگذاری LUKS2 و به‌روزرسان داخلی. بوت از فایل ISO روی دیسک داخلی (بدون فلش، با GRUB2Win) — راهنما در `docs/GRUB2WIN-BOOT.fa.md`.
- ایمیج زنده (Live ISO) با بوت دوگانهٔ BIOS و UEFI در بخش Releases منتشر می‌شود.

## دانلود | Download

ایمیج زنده (Live ISO) از سه راه منتشر می‌شود — هر سه، یک فایل
با یک هش SHA-256 یکسان‌اند:

1. **GitHub Releases** (راه اصلی):
   https://github.com/saman-ghannadzadeh/saman-os/releases
   — نسخهٔ ۴٫۰ (کامل، ۲٫۶۳۴ گیگابایت): ISO به‌علت سقف آپلود در ۳ تکه روی گوگل درایو میزبانی می‌شود؛ هر ۳ تکه را بگیرید و با اسکریپت وصل‌کردنِ همان صفحه به یک ISO تبدیل کنید:
   بخش ۰۰: https://drive.google.com/file/d/1N3kSWCcFkpeFCeFL__H1Pfvb9X-xzJMY/view
   بخش ۰۱: https://drive.google.com/file/d/19e5LSxG1Z3s8s4xlrR-uQwecXQ9158aP/view
   بخش ۰۲: https://drive.google.com/file/d/1gYAVygnCkEVruD3qP0GyxnGvTE1MqTal/view
   وصل‌کردن (لینوکس): https://drive.google.com/file/d/1tagpI-Kjnqt1lauHcenV3T080-t1CkN9/view
   وصل‌کردن (ویندوز): https://drive.google.com/file/d/1Fnbo4-n7t889S8JLa7RGv6TRvOMxBfEL/view
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
