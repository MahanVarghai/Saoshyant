import json
import sys
import ytc
from yt_dlp import YoutubeDL

def main():
    urls = []
    # خواندن لینک‌ها از urls.txt (هر خط یک لینک)
    try:
        with open('urls.txt', 'r', encoding='utf-8') as f:
            for line in f:
                url = line.strip()
                if url and not url.startswith('#'):  # رد خطوط خالی و کامنت
                    urls.append(url)
    except FileNotFoundError:
        print("❌ فایل urls.txt پیدا نشد.")
        sys.exit(1)

    if not urls:
        print("⚠️ هیچ لینکی در urls.txt وجود ندارد.")
        sys.exit(0)

    all_info = []
    errors = []

    for index, url in enumerate(urls, 1):
        print(f"🔍 [{index}/{len(urls)}] در حال دریافت اطلاعات: {url}")
        try:
            # تنظیمات yt-dlp با استفاده از کوکی ytc
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'cookiefile': None,  # استفاده از فایل کوکی غیرفعال شود
                'http_headers': {
                    'Cookie': ytc.youtube()
                },
                'extract_flat': False,  # اطلاعات کامل دریافت شود
            }

            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                # فیلدهای مهم را نگه می‌داریم (قابل شخصی‌سازی)
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

    # ذخیره در JSON
    output = {
        'total_videos': len(urls),
        'successful': len(all_info),
        'failed': len(errors),
        'videos': all_info,
        'errors': errors
    }

    with open('videos_info.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n📁 اطلاعات در videos_info.json ذخیره شد. (موفق: {len(all_info)}, ناموفق: {len(errors)})")

    # اگر خطایی رخ داده بود، هشدار می‌دهیم ولی workflow با شکست مواجه نمی‌شود
    if errors:
        print("⚠️ برخی ویدئوها با خطا مواجه شدند.")
        sys.exit(0)  # خروج موفق (برای ادامه workflow)

if __name__ == '__main__':
    main()
