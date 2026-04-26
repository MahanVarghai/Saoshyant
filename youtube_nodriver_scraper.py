#!/usr/bin/env python3
import asyncio
import json
import pickle
import os
import sys
import subprocess

import nodriver as uc

URL_FILE = "urls.txt"
COOKIE_FILE = "cookies.pkl"
OUTPUT_FILE = "yt_results.json"
CHROME_PATH = "/usr/bin/chromium-browser"

def log(msg):
    print(f"[LOG] {msg}", flush=True)

async def save_cookies(page, path):
    log("Saving cookies...")
    cookies = await page.cookies.all()
    with open(path, "wb") as f:
        pickle.dump(cookies, f)
    log("Cookies saved.")

async def load_cookies(page, path):
    if os.path.exists(path):
        log(f"Loading cookies from {path}")
        with open(path, "rb") as f:
            cookies = pickle.load(f)
            for cookie in cookies:
                await page.cookies.set(cookie)
        log("Cookies loaded.")
        return True
    log("No existing cookies file.")
    return False

async def get_video_info(browser, video_url, timeout=30):
    log(f"Navigating to {video_url}")
    page = None
    try:
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
                    const match = script.textContent.match(/var ytInitialPlayerResponse = (.*?);/s);
                    if (match) {
                        try {
                            return JSON.parse(match[1]);
                        } catch(e) {}
                    }
                }
            }
            return null;
        }
        """
        log("Injecting script to extract video data...")
        player_response = await asyncio.wait_for(page.evaluate(script), timeout=10)

        if player_response and "videoDetails" in player_response:
            vd = player_response["videoDetails"]
            log("Video details extracted successfully.")
            return {
                "status": "ok",
                "data": {
                    "title": vd.get("title"),
                    "view_count": int(vd.get("viewCount", 0)) if vd.get("viewCount") else 0,
                    "duration": int(vd.get("lengthSeconds", 0)) if vd.get("lengthSeconds") else 0,
                    "channel": vd.get("author"),
                }
            }
        else:
            log("Failed to find video details in page.")
            return {"status": "failed", "error": "Video details not found"}
    except asyncio.TimeoutError:
        log(f"Timeout after {timeout} seconds for {video_url}")
        return {"status": "failed", "error": f"Timeout after {timeout}s"}
    except Exception as e:
        log(f"Exception in get_video_info: {str(e)}")
        return {"status": "failed", "error": str(e)}
    finally:
        if page and not page.closed:
            await page.close()
            log("Page closed.")

async def main():
    log("=== Starting YouTube Scraper with Nodriver ===")
    if not os.path.exists(URL_FILE):
        print(f"Error: {URL_FILE} not found")
        sys.exit(1)

    with open(URL_FILE, "r") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    log(f"Found {len(urls)} URLs to process.")

    # بررسی وجود کرومیم
    if not os.path.exists(CHROME_PATH):
        log(f"Chromium not found at {CHROME_PATH}, trying to find...")
        result = subprocess.run(["which", "chromium-browser"], capture_output=True, text=True)
        if result.returncode == 0:
            CHROME_PATH = result.stdout.strip()
            log(f"Found chromium at {CHROME_PATH}")
        else:
            log("Chromium not found in PATH. Exiting.")
            sys.exit(1)

    log("Starting browser...")
    browser = await uc.start(
        headless=True,
        sandbox=False,
        browser_executable_path=CHROME_PATH,
        browser_args=[
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu'
        ]
    )
    log("Browser started.")

    try:
        log("Opening test page and loading cookies...")
        test_page = await asyncio.wait_for(browser.get("https://www.youtube.com"), timeout=30)
        await load_cookies(test_page, COOKIE_FILE)
        await test_page.reload()
        await asyncio.sleep(2)
        await test_page.close()
        log("Cookies loaded and test page closed.")

        results = []
        for idx, url in enumerate(urls, 1):
            log(f"Processing {idx}/{len(urls)}: {url}")
            result = await get_video_info(browser, url)
            result["index"] = idx
            result["url"] = url
            results.append(result)
            log(f"Result status: {result['status']}")
            await asyncio.sleep(2)

        log("Saving final cookies...")
        save_page = await asyncio.wait_for(browser.get("https://www.youtube.com"), timeout=30)
        await save_cookies(save_page, COOKIE_FILE)
        await save_page.close()

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        log(f"Done. Results saved to {OUTPUT_FILE}")
    finally:
        log("Stopping browser...")
        browser.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        log(f"Fatal error: {e}")
        sys.exit(1)
