#!/usr/bin/env python3
import asyncio
import json
import pickle
import os
import sys
import re

import nodriver as uc

URL_FILE = "urls.txt"
COOKIE_FILE = "cookies.pkl"
OUTPUT_FILE = "yt_results.json"

async def save_cookies(page, path):
    """ذخیره کوکی‌ها در فایل"""
    cookies = await page.cookies.all()
    with open(path, "wb") as f:
        pickle.dump(cookies, f)

async def load_cookies(page, path):
    """بارگذاری کوکی‌ها از فایل"""
    if os.path.exists(path):
        with open(path, "rb") as f:
            cookies = pickle.load(f)
            for cookie in cookies:
                await page.cookies.set(cookie)
        return True
    return False

async def get_video_info(browser, video_url):
    """استخراج اطلاعات یک ویدیو با تزریق JavaScript"""
    page = None
    try:
        page = await browser.get(video_url)
        await page
        await asyncio.sleep(3)

        # تزریق اسکریپت برای دریافت ytInitialPlayerResponse
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
        player_response = await page.evaluate(script)

        if player_response and "videoDetails" in player_response:
            vd = player_response["videoDetails"]
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
            return {"status": "failed", "error": "Video details not found"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
    finally:
        if page and not page.closed:
            await page.close()

async def main():
    if not os.path.exists(URL_FILE):
        print(f"Error: {URL_FILE} not found")
        sys.exit(1)

    with open(URL_FILE, "r") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    print(f"Starting Nodriver in headless mode (xvfb)...")
    # تنظیمات کلیدی: headless=True, sandbox=False
    browser = await uc.start(
        headless=True,
        sandbox=False,
        browser_args=[
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-dev-shm-usage'
        ]
    )

    try:
        # بارگذاری کوکی در صورت وجود
        test_page = await browser.get("https://www.youtube.com")
        cookies_loaded = await load_cookies(test_page, COOKIE_FILE)
        if cookies_loaded:
            await test_page.reload()
        await asyncio.sleep(2)
        await test_page.close()

        results = []
        for idx, url in enumerate(urls, 1):
            print(f"Processing {idx}/{len(urls)}: {url}")
            result = await get_video_info(browser, url)
            result["index"] = idx
            result["url"] = url
            results.append(result)
            await asyncio.sleep(2)

        # ذخیره کوکی‌ها برای دفعات بعد
        save_page = await browser.get("https://www.youtube.com")
        await save_cookies(save_page, COOKIE_FILE)
        await save_page.close()

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"Done. Results saved to {OUTPUT_FILE}")

    finally:
        browser.stop()

if __name__ == "__main__":
    uc.loop().run_until_complete(main())
