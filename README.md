# Saman OS

**سامان اواس** — یک سیستم‌عامل مدرن بر پایهٔ لینوکس (اوبونتو ۲۶٫۱۰) با محیط دسکتاپ GNOME و تم Yaru، ساختهٔ سامان قنادزاده یزدی.

**Saman OS** — a modern Linux-based operating system (Ubuntu 26.10 base) with the GNOME desktop and Yaru theme, built by Saman Ghannadzadeh Yazdi.

## وضعیت | Status

- نسخهٔ فعلی: **2.0** — دسکتاپ محصول (GNOME + Yaru) روی روت‌فایل‌سیستم واقعی دیسکی، با ورود خودکار و برندینگ Saman OS.
- ایمیج زنده (Live ISO) با بوت دوگانهٔ BIOS و UEFI در بخش Releases منتشر می‌شود.

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
