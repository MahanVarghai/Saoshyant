import json
import sys
import os
import re
from yt_dlp import YoutubeDL

def clean_cookie_file(filepath):
    """اصلاح فایل کوکی: حذف پیشوند #HttpOnly_ و نرمال‌سازی خطوط"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    cleaned = []
    for line in lines:
        # نگه‌داشتن خطوط کامنت اصلی (شروع با # و بدون HttpOnly_)
        if line.startswith('#') and 'HttpOnly_' not in line:
            cleaned.append(line)
            continue

        # حذف # (اگر وجود دارد) و سپس حذف پیشوند HttpOnly_
        stripped = re.sub(r'^#?\s*HttpOnly_', '', line)
        if stripped and not stripped.startswith('#'):
            cleaned.append(stripped)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(cleaned)

def main():
    urls = []
    try:
        with open('urls.txt', 'r', encoding='utf-8') as f:
            for line in f:
                url = line.strip()
                if url and not url.startswith('#'):
                    urls.append(url)
    except FileNotFoundError:
        print("❌ فایل urls.txt پیدا نشد.")
        sys.exit(1)

    if not urls:
        print("⚠️ هیچ لینکی در urls.txt وجود ندارد.")
        sys.exit(0)

    cookie_content = os.environ.get('YT_COOKIES')
    if not cookie_content:
        print("❌ متغیر محیطی YT_COOKIES تنظیم نشده است.")
        sys.exit(1)

    with open('cookies.txt', 'w', encoding='utf-8') as f:
        f.write(cookie_content)

    clean_cookie_file('cookies.txt')
    print("✅ فایل کوکی تمیز شد. خطوط مهم:")

    # نمایش خلاصه‌ای از فایل کوکی برای دیباگ (بدون افشای کامل)
    with open('cookies.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        cookie_line_count = sum(1 for line in lines if not line.startswith('#'))
        print(f"   تعداد خطوط غیرکامنت: {cookie_line_count}")
        if cookie_line_count == 0:
            print("❌ هیچ کوکی معتبری باقی نمانده است!")
            sys.exit(1)

    all_info = []
    errors = []

    for index, url in enumerate(urls, 1):
        print(f"🔍 [{index}/{len(urls)}] در حال دریافت اطلاعات: {url}")
        try:
            ydl_opts = {
                'quiet': False,      # <-- برای نمایش لاگ
                'no_warnings': False,
                'verbose': True,     # <-- لاگ بسیار کامل
                'cookiefile': 'cookies.txt',
                'extract_flat': False,
                # 'format' را حذف کردیم چون extract_info نیازی به آن ندارد
            }

            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                simplified = {
                    'id': info.get('id'),
                    'title': info.get('title'),
                    'description': info.get('description'),
                    'duration': info.get('duration'),
                    'upload_date': info.get('upload_date'),
                    'uploader': info.get('uploader'),
                    'view_count': info.get('view_count'),
                    'like_count': info.get('like_count'),
                    'categories': info.get('categories'),
                    'tags': info.get('tags'),
                    'url': url,
                }
                all_info.append(simplified)
                print(f"   ✅ موفق - عنوان: {simplified.get('title')}")

        except Exception as e:
            print(f"   ❌ خطا: {e}")
            errors.append({'index': index, 'url': url, 'error': str(e)})

    output = {
        'last_update': None,
        'total_videos': len(urls),
        'successful': len(all_info),
        'failed': len(errors),
        'videos': all_info,
        'errors': errors
    }

    with open('videos_info.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n📁 اطلاعات در videos_info.json ذخیره شد. (موفق: {len(all_info)}, ناموفق: {len(errors)})")
    if errors:
        print("⚠️ برخی ویدئوها با خطا مواجه شدند.")
    sys.exit(0)

if __name__ == '__main__':
    main()
