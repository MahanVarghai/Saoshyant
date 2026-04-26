import json
import sys
import os
import re
import time
import zipfile
import requests
from yt_dlp import YoutubeDL

# ------------------------------------------------------------
# تنظیمات اولیه
THUMBNAILS_DIR = 'thumbnails'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'

# ------------------------------------------------------------
def clean_cookie_file(filepath):
    """اصلاح فایل کوکی: حذف پیشوند #HttpOnly_ و نرمال‌سازی خطوط"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    cleaned = []
    for line in lines:
        if line.startswith('#') and 'HttpOnly_' not in line:
            cleaned.append(line)
            continue
        stripped = re.sub(r'^#?\s*HttpOnly_', '', line)
        if stripped and not stripped.startswith('#'):
            cleaned.append(stripped)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(cleaned)

# ------------------------------------------------------------
def download_thumbnail(url, save_path, max_retries=2):
    """دانلود عکس تامنیل از یک URL با چندبار تلاش مجدد"""
    headers = {'User-Agent': USER_AGENT}
    for attempt in range(max_retries):
        try:
            r = requests.get(url, headers=headers, timeout=15, stream=True)
            if r.status_code == 200:
                content_type = r.headers.get('content-type', '')
                if 'image' in content_type:
                    with open(save_path, 'wb') as f:
                        for chunk in r.iter_content(8192):
                            f.write(chunk)
                    if os.path.getsize(save_path) > 100:
                        return True
        except Exception:
            pass
        time.sleep(0.3)
    return False

# ------------------------------------------------------------
def main():
    # ۱. خواندن URLها
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

    # ۲. دریافت کوکی از متغیر محیطی
    cookie_content = os.environ.get('YT_COOKIES')
    if not cookie_content:
        print("❌ متغیر محیطی YT_COOKIES تنظیم نشده است.")
        sys.exit(1)

    with open('cookies.txt', 'w', encoding='utf-8') as f:
        f.write(cookie_content)
    clean_cookie_file('cookies.txt')
    print("✅ فایل کوکی تمیز و آماده شد.")

    # ۳. ایجاد پوشه تامنیل‌ها
    os.makedirs(THUMBNAILS_DIR, exist_ok=True)

    # ۴. استخراج اطلاعات و دانلود تامنیل‌ها
    all_info = []
    errors = []

    for index, url in enumerate(urls, 1):
        print(f"🔍 [{index}/{len(urls)}] در حال دریافت اطلاعات: {url}")
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'cookiefile': 'cookies.txt',
                'extract_flat': False,
                'ignore_no_formats_error': True,
                'extractor_args': {'youtube': {'player_client': ['web']}},
            }

            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            video_id = info.get('id', f'unknown_{index}')
            title = info.get('title', 'بی‌نام')

            # ---- دانلود تامنیل ----
            thumb_filename = f"{video_id}.jpg"
            thumb_path = os.path.join(THUMBNAILS_DIR, thumb_filename)
            thumb_downloaded = False

            # لینک‌های احتمالی تامنیل
            thumb_url = info.get('thumbnail')
            if not thumb_url:
                thumbnails_list = info.get('thumbnails', [])
                if thumbnails_list:
                    # بهترین کیفیت معمولاً آخرین عضو است
                    thumb_url = thumbnails_list[-1].get('url')

            if thumb_url:
                thumb_downloaded = download_thumbnail(thumb_url, thumb_path)

            if not thumb_downloaded:
                # بارگزاری یک placeholder یک پیکسلی
                with open(thumb_path, 'wb') as f:
                    f.write(
                        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
                        b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
                        b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
                    )
                print(f"   ⚠️ تامنیل برای {video_id} دریافت نشد، از placeholder استفاده شد.")
            else:
                print(f"   🖼️ تامنیل ذخیره شد: {thumb_filename}")

            # ---- ساخت اطلاعات JSON ----
            simplified = {
                'id': video_id,
                'title': title,
                'description': info.get('description'),
                'duration': info.get('duration'),
                'upload_date': info.get('upload_date'),
                'uploader': info.get('uploader'),
                'view_count': info.get('view_count'),
                'like_count': info.get('like_count'),
                'categories': info.get('categories'),
                'tags': info.get('tags'),
                'url': url,
                'thumbnail': os.path.join(THUMBNAILS_DIR, thumb_filename)   # مسیر نسبی
            }
            all_info.append(simplified)
            print(f"   ✅ موفق - عنوان: {title}")

        except Exception as e:
            print(f"   ❌ خطا: {e}")
            errors.append({'index': index, 'url': url, 'error': str(e)})

    # ۵. ساخت فایل JSON نهایی
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

    # ۶. ساخت فایل ZIP از پوشه تامنیل‌ها
    zip_filename = 'thumbnails.zip'
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(THUMBNAILS_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, THUMBNAILS_DIR)
                zf.write(file_path, arcname)
    print(f"📦 فایل {zip_filename} ساخته شد.")

    if errors:
        print("⚠️ برخی ویدئوها با خطا مواجه شدند.")
    sys.exit(0)

if __name__ == '__main__':
    main()
