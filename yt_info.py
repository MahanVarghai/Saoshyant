#!/usr/bin/env python3
import json
import yt_dlp
import sys
import os

URLS_FILE = "urls.txt"
OUTPUT_FILE = "yt_results.json"

def get_video_info(url):
    """استخراج اطلاعات ویدئو با استفاده از yt-dlp و PO Token"""
    
    # تنظیمات yt-dlp برای درخواست خودکار PO Token
    ydl_opts = {
        'quiet': True,
        'no_warnings': False,
        'extract_flat': False,
        'force_generic_extractor': False,
        # استفاده از کلاینت mweb که نیاز به PO Token دارد
        'extractor_args': {
            'youtube': {
                'player_client': ['mweb'],
            }
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info is None:
                return {"error": "Could not extract info"}
                
            return {
                "title": info.get('title', 'N/A'),
                "duration": info.get('duration', 0),
                "channel": info.get('uploader', 'N/A'),
                "view_count": info.get('view_count', 0),
                "webpage_url": info.get('webpage_url', url),
                "thumbnail": info.get('thumbnail', ''),
                "description": (info.get('description', '') or '')[:200]
            }
    except Exception as e:
        return {"error": str(e)}

def main():
    # چاپ نسخه yt-dlp و پلاگین‌های نصب شده برای اطمینان
    os.system("yt-dlp --version")
    
    if not os.path.exists(URLS_FILE):
        print(f"Error: {URLS_FILE} not found")
        sys.exit(1)

    with open(URLS_FILE, "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    results = []
    for idx, url in enumerate(urls, 1):
        print(f"Processing {idx}/{len(urls)}: {url}")
        info = get_video_info(url)
        
        result_item = {
            "index": idx,
            "url": url,
            "status": "ok" if "error" not in info else "failed",
            "data": info if "error" not in info else None,
            "error": info.get("error") if "error" in info else None
        }
        results.append(result_item)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Done. Output written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
