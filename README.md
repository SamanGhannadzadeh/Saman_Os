# Saman OS

**سامان اواس** — یک سیستم‌عامل مدرن بر پایهٔ لینوکس (اوبونتو ۲۶٫۱۰) با محیط دسکتاپ GNOME و تم Yaru، ساختهٔ سامان قنادزاده یزدی.

**Saman OS** — a modern Linux-based operating system (Ubuntu 26.10 base) with the GNOME desktop and Yaru theme, built by Saman Ghannadzadeh Yazdi.

## وضعیت | Status

- نسخهٔ فعلی: **3.0** — نسخهٔ کامل: دسکتاپ گنوم با طراحی شیشه‌ای و ۱٬۹۲۲ بسته، آنتی‌ویروس SamanOS، نصاب دوال‌بوت با رمزگذاری LUKS2 و به‌روزرسان داخلی.
- ایمیج زنده (Live ISO) با بوت دوگانهٔ BIOS و UEFI در بخش Releases منتشر می‌شود.

## دانلود | Download

ایمیج زنده (Live ISO) از سه راه منتشر می‌شود — هر سه، یک فایل
با یک هش SHA-256 یکسان‌اند:

1. **GitHub Releases** (راه اصلی):
   https://github.com/saman-ghannadzadeh/saman-os/releases
   — نسخهٔ ۳٫۰ (کامل، ۲٫۷۷ گیگابایت): ISO به‌علت سقف آپلود در ۴ تکه روی گوگل درایو میزبانی می‌شود؛ هر ۴ تکه را بگیرید و با اسکریپت وصل‌کردنِ همان صفحه به یک ISO تبدیل کنید:
   بخش ۰۰: https://drive.google.com/file/d/1k8_e2EG-v3ys9B4QEwUUqQWF8Yb0ky0V/view?usp=drivesdk
   بخش ۰۱: https://drive.google.com/file/d/19KFcqhe6qC_78FSX80EQa3a00A-YefiY/view?usp=drivesdk
   بخش ۰۲: https://drive.google.com/file/d/1CZ6oNmceKqr-pkloL1BwjmGmYkcKdybo/view?usp=drivesdk
   بخش ۰۳: https://drive.google.com/file/d/1mC4If4XgX5EAqLtXOo-ceWd2VZvZN82e/view?usp=drivesdk
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
