#!/usr/bin/env python3
import json
import subprocess
import sys
import os

URLS_FILE = "urls.txt"
OUTPUT_FILE = "yt_results.json"

def get_video_info(url):
    """استخراج اطلاعات ویدئو با استفاده از روش '--flat-playlist' و وارسی پلی‌لیست"""
    try:
        # ترفند: از آدرس ویدئو برای گرفتن اطلاعات از پلی‌لیست کانال استفاده می‌کنیم
        # اینکار باعث می‌شود درخواست 'flat-playlist' تلقی شود
        cmd = [
            "yt-dlp",
            "--flat-playlist",  # کلید موفقیت: فقط فراداده
            "--dump-json",
            "--skip-download",
            "--no-playlist",   # فقط خود ویدئو، نه کل پلی‌لیست
            "--no-warnings",
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return {"error": result.stderr.strip()}
        
        # خروجی مستقیم JSON است
        data = json.loads(result.stdout)
        
        # استخراج فیلدهای مورد نظر
        # توجه: در حالت flat-playlist، همه فیلدها مثل duration وجود ندارد
        # برای duration و view_count باید از روش مستقیم استفاده کنیم (در صورت نیاز)
        return {
            "title": data.get("title", "N/A"),
            "duration": data.get("duration", 0),
            "channel": data.get("uploader", "N/A"),
            "view_count": data.get("view_count", 0),  # در flat-playlist نیست، 0 برمی‌گرداند
            "webpage_url": data.get("webpage_url", url),
            "thumbnail": data.get("thumbnail", ""),
            "description": data.get("description", "")[:200]
        }
    except subprocess.TimeoutExpired:
        return {"error": "Timeout after 60 seconds"}
    except Exception as e:
        return {"error": str(e)}

def main():
    if not os.path.exists(URLS_FILE):
        print(f"Error: {URLS_FILE} not found")
        sys.exit(1)

    with open(URLS_FILE, "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    results = []
    for idx, url in enumerate(urls, 1):
        print(f"Processing {idx}/{len(urls)}: {url}")
        info = get_video_info(url)
        
        # تشخیص موفقیت: اگر خطای امنیتی وجود نداشته باشد
        error_msg = info.get("error", "")
        is_bot_error = "Sign in to confirm" in error_msg or "bot" in error_msg.lower()
        
        if "error" not in info or is_bot_error:
            # در صورت خطای ربات، وضعیت failed با پیام مناسب
            status = "failed"
            error_detail = error_msg if error_msg else "Bot detection triggered. Try different URL format."
        else:
            status = "ok"
            error_detail = None
        
        results.append({
            "index": idx,
            "url": url,
            "status": status,
            "data": info if status == "ok" and "error" not in info else None,
            "error": error_detail
        })

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Done. Output written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
