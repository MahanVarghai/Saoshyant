#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import yt_dlp
import json
import sys
import os
import time

# نام فایل ورودی (لیست URLها، هر خط یک URL) و فایل خروجی
URLS_FILE = "urls.txt"
OUTPUT_FILE = "yt_info_results.json"


def get_video_info(url, retries=1):
    """
    با استفاده از yt-dlp و ارائه‌دهنده bgutil-ytdlp-pot-provider
    اطلاعات یک ویدیوی یوتیوب را استخراج می‌کند.
    """
    for attempt in range(retries + 1):
        try:
            # تنظیمات yt-dlp برای استفاده از پلاگین bgutil
            ydl_opts = {
                'quiet': True,          # خروجی کم و خلاصه
                'no_warnings': True,    # نمایش ندادن هشدارها (اختیاری)
                'extract_flat': 'in_playlist',  # استخراج فراداده سطح اول (سریع‌تر)
                'extractor_args': {
                    'youtube': {
                        'skip': ['hls', 'dash'],        # برای سرعت بخشیدن و جلوگیری از دانلود
                        'player_client': ['web'],       # استفاده از کلاینت وب (نیازمند PO Token)
                        # گزینه بعدی صریحاً به yt-dlp می‌گوید از پلاگین ما برای توکن استفاده کند.
                        # فرمت 'bgutil:http' به این معناست که ارائه‌دهنده در حالت HTTP Server اجرا می‌شود.
                        'po_token_provider': ['bgutil:http'],
                    }
                }
            }

            # اجرای yt-dlp برای استخراج اطلاعات
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info:
                    duration = info.get('duration')
                    if isinstance(duration, (int, float)) and duration > 0:
                        duration = int(duration)
                    else:
                        duration = 0

                    return {
                        "title": info.get('title', 'N/A'),
                        "duration": duration,
                        "channel": info.get('uploader', 'N/A'),
                        "view_count": info.get('view_count', 0),
                        "webpage_url": info.get('webpage_url', url),
                        "thumbnail": info.get('thumbnail', ''),
                        "description": (info.get('description', '') or '')[:200],
                        "status": "ok"
                    }
                return {"status": "failed", "error": "No info extracted"}

        except Exception as e:
            # اگر تعداد تلاش مجاز باقی مانده، صبر و دوباره تلاش کن
            if attempt < retries:
                time.sleep(3)
                continue
            return {"status": "failed", "error": str(e)}
    
    return {"status": "failed", "error": "Max retries exceeded"}


def main():
    # بررسی وجود فایل ورودی
    if not os.path.exists(URLS_FILE):
        print(f"Error: {URLS_FILE} not found")
        sys.exit(1)

    # خواندن URL ها از فایل (نادیده گرفتن خطوط خالی)
    with open(URLS_FILE, "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    results = []
    total = len(urls)
    
    for idx, url in enumerate(urls, 1):
        print(f"Processing {idx}/{total}: {url}")
        result = get_video_info(url)
        result['index'] = idx
        result['url'] = url
        results.append(result)
        # یک وقفه کوتاه برای جلوگیری از ارسال درخواست‌های پشت‌سرهم
        time.sleep(2)

    # ذخیره نتایج نهایی در فایل JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Done. Results saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
