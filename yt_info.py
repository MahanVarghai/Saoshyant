#!/usr/bin/env python3
import json
import subprocess
import sys
import os

URLS_FILE = "urls.txt"
OUTPUT_FILE = "yt_results.json"

def get_video_info(url):
    """استخراج اطلاعات ویدئو با yt-dlp و برگرداندن دیکشنری"""
    try:
        cmd = [
            "yt-dlp",
            "--dump-json",          # خروجی JSON
            "--skip-download",      # دانلود نکن فقط اطلاعات
            "--no-playlist",        # فقط اولین ویدئو (اگر لیست نباشد)
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return {"error": result.stderr.strip()}
        data = json.loads(result.stdout)
        return {
            "title": data.get("title"),
            "duration": data.get("duration"),
            "channel": data.get("uploader"),
            "view_count": data.get("view_count"),
            "webpage_url": data.get("webpage_url"),
            "thumbnail": data.get("thumbnail"),
            "description": data.get("description", "")[:200]  # خلاصه
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
        results.append({
            "index": idx,
            "url": url,
            "status": "ok" if "error" not in info else "failed",
            "data": info if "error" not in info else None,
            "error": info.get("error") if "error" in info else None
        })

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Done. Output written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
