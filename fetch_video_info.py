import json
import sys
import os
import time
import tempfile
import shutil
import base64
import zipfile
import requests
from datetime import datetime, timezone
from yt_dlp import YoutubeDL

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'

# تصویر جایگزین JPEG معتبر ۱×۱ پیکسل (بیس۶۴)
PLACEHOLDER_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAMCAgMCAgMDAwMEAwMEBQgFBQQEBQoHBwYIDAoMCwsK"
    "CwsNDhIQDQ4RDgsLEBYQERMUFRUVDA8XGBYUGBIUFRT/2wBDAQMEBAUEBQkFBQkUDQsNFBQUFBQU"
    "FBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBT/wAARCAABAAEDASIAAhEB"
    "AxEB/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/xAAUAQEAAAAA"
    "AAAAAAAAAAAAAAAAAAAK/8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAwDAQACEQMRAD8AJwAB/9k="
)

def download_thumbnail(url, save_path, max_retries=2):
    """دانلود تامبنیل با قابلیت تلاش دوباره"""
    print(f"      📥 تلاش برای دانلود تامبنیل از {url}")
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
                    file_size = os.path.getsize(save_path)
                    print(f"      ✅ تامبنیل دانلود شد ({file_size} بایت)")
                    if file_size > 100:
                        return True
                    else:
                        print(f"      ⚠️ حجم فایل بسیار کم است: {file_size} بایت")
        except Exception as e:
            print(f"      ⚠️ تلاش {attempt+1} ناموفق: {e}")
        time.sleep(0.3)
    print(f"      ❌ پس از {max_retries} تلاش دانلود نشد.")
    return False

def extract_formats(info):
    """استخراج لیست فرمت‌های ویدئو با حجم"""
    formats = info.get('formats', [])
    print(f"      📋 تعداد فرمت‌های خام دریافت‌شده: {len(formats)}")
    useful = []
    for fmt in formats:
        vcodec = fmt.get('vcodec', 'none')
        acodec = fmt.get('acodec', 'none')
        if vcodec == 'none' and acodec == 'none':
            continue
        size = fmt.get('filesize') or fmt.get('filesize_approx')
        useful.append({
            'format_id': fmt.get('format_id'),
            'ext': fmt.get('ext'),
            'resolution': fmt.get('resolution'),
            'width': fmt.get('width'),
            'height': fmt.get('height'),
            'vcodec': vcodec,
            'acodec': acodec,
            'filesize': size,
            'tbr': fmt.get('tbr'),
            'fps': fmt.get('fps'),
        })
    print(f"      📊 فرمت‌های مفید استخراج‌شده: {len(useful)}")
    if useful:
        first = useful[0]
        print(f"      🔹 نمونه: {first.get('format_id')} ({first.get('ext')}) {first.get('resolution')}")
    else:
        print("      ⚠️ هیچ فرمت قابل‌استفاده‌ای یافت نشد!")
    return useful

def main():
    print(f"🚀 شروع اجرا در {datetime.now(timezone.utc).isoformat()}")
    
    # خواندن URLها
    urls = []
    try:
        with open('urls.txt', 'r', encoding='utf-8') as f:
            for line in f:
                url = line.strip()
                if url and not url.startswith('#'):
                    urls.append(url)
        print(f"📄 {len(urls)} لینک از urls.txt خوانده شد.")
    except FileNotFoundError:
        print("❌ فایل urls.txt پیدا نشد.")
        sys.exit(1)

    if not urls:
        print("⚠️ هیچ لینکی در urls.txt وجود ندارد.")
        sys.exit(0)

    # آماده‌سازی کوکی
    cookie_content = os.environ.get('YT_COOKIES')
    if not cookie_content:
        print("❌ متغیر محیطی YT_COOKIES تنظیم نشده است.")
        sys.exit(1)

    with open('cookies.txt', 'w', encoding='utf-8') as f:
        f.write(cookie_content)
    print("✅ فایل کوکی (از پیش تمیز) ذخیره شد.")

    # ساخت پوشهٔ موقت برای تامبنیل‌ها
    temp_thumb_dir = tempfile.mkdtemp(prefix='youtube_thumbs_')
    print(f"📁 پوشهٔ موقت تامبنیل‌ها: {temp_thumb_dir}")

    all_info = []
    errors = []

    for index, url in enumerate(urls, 1):
        print(f"\n🔍 [{index}/{len(urls)}] پردازش: {url}")
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'cookiefile': 'cookies.txt',
                'extract_flat': False,
                'ignore_no_formats_error': True,
                'extractor_args': {'youtube': {'player_client': ['web']}},
            }

            print("   ⏳ دریافت اطلاعات از یوتیوب...")
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            video_id = info.get('id', f'unknown_{index}')
            title = info.get('title', 'بی‌نام')
            print(f"   🆔 شناسه: {video_id}")
            print(f"   📺 عنوان: {title}")

            # دانلود تامبنیل
            thumb_filename = f"{video_id}.jpg"
            thumb_path = os.path.join(temp_thumb_dir, thumb_filename)
            thumb_downloaded = False
            thumb_url = info.get('thumbnail')
            if not thumb_url:
                thumbnails_list = info.get('thumbnails', [])
                if thumbnails_list:
                    thumb_url = thumbnails_list[-1].get('url')
            if thumb_url:
                print(f"   🖼️ آدرس تامبنیل: {thumb_url}")
                thumb_downloaded = download_thumbnail(thumb_url, thumb_path)

            if not thumb_downloaded:
                # نوشتن placeholder JPEG واقعی
                with open(thumb_path, 'wb') as f:
                    f.write(PLACEHOLDER_JPEG)
                print(f"   ⚠️ تامبنیل دریافت نشد، از placeholder استاندارد استفاده شد.")
            else:
                print(f"   ✅ تامبنیل ذخیره شد: {thumb_filename}")

            # dislike_count
            dislike_count = info.get('dislike_count')

            # استخراج فرمت‌ها
            formats_list = extract_formats(info)

            simplified = {
                'id': video_id,
                'title': title,
                'description': info.get('description'),
                'duration': info.get('duration'),
                'upload_date': info.get('upload_date'),
                'uploader': info.get('uploader'),
                'channel_id': info.get('channel_id'),
                'view_count': info.get('view_count'),
                'like_count': info.get('like_count'),
                'dislike_count': dislike_count,
                'categories': info.get('categories'),
                'tags': info.get('tags'),
                'url': url,
                'thumbnail': thumb_filename,   # فقط نام فایل، بدون مسیر
                'formats': formats_list
            }
            all_info.append(simplified)
            print(f"   ✔️ اطلاعات با موفقیت استخراج شد.")

        except Exception as e:
            print(f"   ❌ خطا در پردازش: {e}")
            errors.append({'index': index, 'url': url, 'error': str(e)})

    output = {
        'last_update': datetime.now(timezone.utc).isoformat(),
        'total_videos': len(urls),
        'successful': len(all_info),
        'failed': len(errors),
        'videos': all_info,
        'errors': errors
    }

    with open('videos_info.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n📁 فایل videos_info.json ذخیره شد. (موفق: {len(all_info)}, ناموفق: {len(errors)})")

    # ساخت ZIP با محتویات پوشهٔ موقت
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"youtube_data_{timestamp}.zip"
    print(f"📦 ساخت فایل ZIP: {zip_filename}")
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write('videos_info.json', arcname='videos_info.json')
        for root, _, files in os.walk(temp_thumb_dir):
            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, start=temp_thumb_dir)
                zf.write(full_path, arcname)
    print(f"✅ ZIP ساخته شد.")

    # ذخیرهٔ نام ZIP برای workflow
    zip_name_file = 'zip_name.txt'
    with open(zip_name_file, 'w') as f:
        f.write(zip_filename)
    print(f"📝 نام فایل ZIP در {zip_name_file} ذخیره شد.")

    # پاک‌سازی
    print("🧹 پاکسازی فایل‌های موقت...")
    shutil.rmtree(temp_thumb_dir)
    if os.path.exists('cookies.txt'):
        os.remove('cookies.txt')
        print("   🍪 فایل کوکی حذف شد.")

    if errors:
        print("⚠️ برخی ویدئوها با خطا مواجه شدند. لیست خطاها در JSON موجود است.")
    else:
        print("🎉 همهٔ ویدئوها با موفقیت پردازش شدند.")
    sys.exit(0)

if __name__ == '__main__':
    main()
