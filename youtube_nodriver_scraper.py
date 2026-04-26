import asyncio
import json
import re
import pickle
import os
import sys

import nodriver as uc

URL_FILE = "urls.txt"
COOKIE_FILE = "cookies.pkl"
OUTPUT_FILE = "yt_results.json"


async def save_cookies(page, path):
    """ذخیره کوکی‌ها (ماندن لاگین)"""
    cookies = await page.cookies.all()
    with open(path, "wb") as f:
        pickle.dump(cookies, f)


async def load_cookies(page, path):
    """بارگذاری کوکی‌ها برای لاگین خودکار"""
    if os.path.exists(path):
        with open(path, "rb") as f:
            cookies = pickle.load(f)
            for cookie in cookies:
                await page.cookies.set(cookie)


async def get_video_info(browser, video_url):
    """باز کردن صفحه ویدئو و استخراج اطلاعات با استفاده از تزریق JS"""
    page = None
    try:
        page = await browser.get(video_url)
        await page

        # اسکرول برای اطمینان از لود شدن کامل
        await page.scroll_down(500)
        await asyncio.sleep(2)
        await page.scroll_up(500)
        await asyncio.sleep(2)

        # تزریق جاوا اسکریپت برای استخراج دیتای اولیه ویدیو
        script = """
        () => {
            if (ytInitialPlayerResponse && ytInitialPlayerResponse.videoDetails) {
                return ytInitialPlayerResponse;
            }
            const scripts = document.querySelectorAll('script');
            for (let script of scripts) {
                if (script.textContent.includes('ytInitialPlayerResponse')) {
                    const regex = /var ytInitialPlayerResponse = (.*?);/s;
                    const match = script.textContent.match(regex);
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
            video_details = player_response["videoDetails"]
            if video_details:
                title = video_details.get("title")
                view_count = video_details.get("viewCount")
                length_seconds = video_details.get("lengthSeconds")
                channel = video_details.get("author")
                return {
                    "status": "ok",
                    "data": {
                        "title": title,
                        "view_count": int(view_count) if view_count else None,
                        "duration": int(length_seconds) if length_seconds else None,
                        "channel": channel,
                    },
                }

        return {"status": "failed", "error": "Video data not found on the page."}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
    finally:
        if page and not page.closed:
            await page.close()


async def main():
    if not os.path.exists(URL_FILE):
        print("urls.txt not found")
        sys.exit(1)

    with open(URL_FILE, "r") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    print(f"Starting Nodriver - Chromium will start normally...")
    browser = await uc.start(
        headless=False,  # **CRITICAL: NON-HEADLESS MODE**
        browser_executable_path=None,
        sandbox=True,
    )

    try:
        # 1. بارگذاری کوکی در صورت وجود
        first_page = await browser.get("https://www.youtube.com")
        await load_cookies(first_page, COOKIE_FILE)
        await first_page.reload()
        await first_page.close()

        # برای اطمینان از session جدید
        await asyncio.sleep(2)

        results = []
        for idx, url in enumerate(urls, 1):
            print(f"Processing {idx}/{len(urls)}: {url}")
            result = await get_video_info(browser, url)
            result["index"] = idx
            result["url"] = url
            results.append(result)
            await asyncio.sleep(2)  # احترام به سرور

        # ذخیره کوکی جدید بعد از انجام عملیات
        save_page = await browser.get("https://www.youtube.com")
        await save_cookies(save_page, COOKIE_FILE)
        await save_page.close()

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"Successfully processed {len(results)} videos. Results saved to {OUTPUT_FILE}")

    finally:
        if browser:
            browser.stop()


if __name__ == "__main__":
    uc.loop().run_until_complete(main())
