#!/usr/bin/env python3
import asyncio
import json
import os
import sys

import nodriver as uc

URL_FILE = "urls.txt"
OUTPUT_FILE = "yt_results.json"

def log(msg):
    print(f"[LOG] {msg}", flush=True)

async def get_video_info(browser, video_url, timeout=30):
    """استخراج اطلاعات ویدئو با استفاده از ytInitialPlayerResponse"""
    page = None
    try:
        log(f"Navigating to {video_url}")
        page = await asyncio.wait_for(browser.get(video_url), timeout=timeout)
        log("Page loaded, waiting 3 seconds...")
        await asyncio.sleep(3)

        script = """
        () => {
            if (window.ytInitialPlayerResponse && window.ytInitialPlayerResponse.videoDetails) {
                return window.ytInitialPlayerResponse;
            }
            const scripts = document.querySelectorAll('script');
            for (let script of scripts) {
                if (script.textContent.includes('ytInitialPlayerResponse')) {
                    const match = script.textContent.match(/var ytInitialPlayerResponse = (.*?)}};/s);
                    if (match) {
                        try {
                            const data = JSON.parse(match[1] + '}}');
                            if (data && data.videoDetails) return data;
                        } catch(e) {}
                    }
                }
            }
            return null;
        }
        """
        log("Injecting script to extract video data...")
        result = await asyncio.wait_for(page.evaluate(script), timeout=10)
        print("************")
        print(result)
        print("************")
        if result and result.get("videoDetails"):
            vd = result["videoDetails"]
            log("Video details extracted successfully.")
            return {
                "status": "ok",
                "data": {
                    "title": vd.get("title"),
                    "view_count": int(vd.get("viewCount")) if vd.get("viewCount") else 0,
                    "duration": int(vd.get("lengthSeconds")) if vd.get("lengthSeconds") else 0,
                    "channel": vd.get("author"),
                    "channelId": vd.get("channelId"),
                    "videoId": vd.get("videoId"),
                }
            }
        else:
            log("Could not find video details json in page source.")
            return {"status": "failed", "error": "Video details not found"}
    except asyncio.TimeoutError:
        log(f"Timeout after {timeout} seconds.")
        return {"status": "failed", "error": f"Timeout after {timeout}s"}
    except Exception as e:
        log(f"Exception caught: {str(e)}")
        return {"status": "failed", "error": str(e)}
    finally:
        if page and not page.closed:
            await page.close()
            log("Page closed.")

async def main():
    log("=== nodriver final attempt ===")
    if not os.path.exists(URL_FILE):
        log(f"File not found: {URL_FILE}")
        sys.exit(1)

    with open(URL_FILE, "r") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    log(f"Found {len(urls)} urls to process.")

    chrome_path = "/usr/bin/chromium-browser"
    if not os.path.exists(chrome_path):
        chrome_path = "/usr/bin/google-chrome"
    if not os.path.exists(chrome_path):
        log("Browser not found in default paths.")
        sys.exit(1)
    log(f"Using Chrome at: {chrome_path}")

    log("Starting browser...")
    browser = await uc.start(
        headless=True,
        sandbox=False,
        browser_executable_path=chrome_path,
        browser_args=[
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--hide-scrollbars',
            '--disable-gpu',
        ]
    )
    log("Browser started.")

    try:
        results = []
        for idx, url in enumerate(urls, 1):
            log(f"Processing {idx}/{len(urls)}: {url}")
            res = await get_video_info(browser, url)
            res["index"] = idx
            res["url"] = url
            results.append(res)
            await asyncio.sleep(2)
        with open(OUTPUT_FILE, "w") as f:
            json.dump(results, f, indent=2)
        log(f"Done, saved to {OUTPUT_FILE}")
    finally:
        log("Stopping browser...")
        browser.stop()

if __name__ == "__main__":
    asyncio.run(main())
