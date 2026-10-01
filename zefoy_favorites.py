#!/usr/bin/env python3
"""
⚡ TikTok Zefoy Favorites Booster v3 (Full Auto: Gemini Vision Captcha Solver) ⚡

Tính năng tự động 100%:
1. Tự động chụp ảnh captcha và gửi tới Gemini Vision API giải chữ.
2. Tự động điền captcha và đăng nhập (tự thử lại nếu sai).
3. Tự động chọn dịch vụ Favorites, điền link TikTok, bấm Search.
4. Tự động chọn limit 100 từ dropdown.
5. Tự động kích hoạt nút gửi Favorites.
6. Tự động theo dõi Cooldown đếm ngược chính xác và lặp lại liên tục.
"""

import argparse
import asyncio
import base64
import os
import re
import sys
import time
import requests
from playwright.async_api import async_playwright

ZEFOY_URL = "https://zefoy.com/"
DEFAULT_GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-3.5-flash-lite"

class ZefoyFavoritesBot:
    def __init__(self, target_url, api_key=None, loops=0):
        self.target_url = target_url
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", DEFAULT_GEMINI_KEY)
        self.loops = loops
        self.total_sent = 0
        self.start_time = time.time()

    def solve_captcha_api(self, image_bytes):
        """Gửi ảnh Captcha qua Gemini 3.5 Flash Lite để nhận diện text"""
        b64_img = base64.b64encode(image_bytes).decode('utf-8')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={self.api_key}"
        
        prompt = (
            "This is a text captcha image. Read the word or letters shown in this image. "
            "Output ONLY the letters in lowercase, with no spaces, no punctuation, and no markdown."
        )
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": "image/png",
                            "data": b64_img
                        }
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 20
            }
        }
        
        try:
            res = requests.post(url, json=payload, timeout=12)
            if res.status_code == 200:
                data = res.json()
                raw_text = data['candidates'][0]['content']['parts'][0]['text']
                # Làm sạch chuỗi: chỉ lấy chữ cái
                cleaned = re.sub(r'[^a-zA-Z]', '', raw_text).lower().strip()
                return cleaned
            else:
                print(f"[!] Gemini API Error ({res.status_code}): {res.text[:150]}")
        except Exception as e:
            print(f"[!] Lỗi gọi Gemini API: {e}")
        return None

    async def auto_solve_captcha(self, page):
        """Tự động phát hiện và giải Captcha liên tục cho đến khi thành công"""
        print("\n[*] 🤖 Đang kích hoạt bộ giải Captcha AI tự động (Gemini Vision)...")

        for attempt in range(1, 6):
            print(f"[*] Thử giải Captcha lần #{attempt}...")

            # 1. Chờ phần tử ảnh captcha xuất hiện
            captcha_img = page.locator('#captcha-img')
            try:
                await captcha_img.wait_for(state="visible", timeout=10000)
                await asyncio.sleep(1) # Chờ ảnh render hoàn chỉnh
            except Exception:
                # Kiểm tra xem đã qua được captcha chưa
                content = await page.content()
                if 'captchalogin' not in content:
                    print("[✅] Đã vượt qua Captcha!")
                    return True

            # 2. Chụp ảnh vùng Captcha
            img_bytes = await captcha_img.screenshot()

            # 3. Gửi qua Gemini Vision
            text = self.solve_captcha_api(img_bytes)
            if not text:
                print("[!] AI chưa nhận diện được chữ. Đang tải lại ảnh captcha...")
                await self._refresh_captcha(page)
                continue

            print(f"[🤖 Gemini AI]: Nhận diện từ trong Captcha = '{text}'")

            # 4. Điền vào form và submit
            input_cap = page.locator('input[name="captchalogin"]')
            await input_cap.click()
            await input_cap.fill("")
            await input_cap.fill(text)
            await asyncio.sleep(0.5)

            submit_btn = page.locator('button.submit-captcha, button[type="submit"]')
            if await submit_btn.count() > 0:
                await submit_btn.first.click()
            else:
                await input_cap.press("Enter")

            # 5. Chờ kết quả phản hồi
            await asyncio.sleep(4)

            # Kiểm tra xem đã vào được menu chính chưa
            content = await page.content()
            if 'captchalogin' not in content and 'colsmenu' in content:
                print(f"[✅ THÀNH CÔNG] Đã tự động vượt Captcha bằng AI ở lần #{attempt}!")
                return True

            print("[!] Captcha không chính xác hoặc Zefoy yêu cầu thử lại. Đang đổi mã...")
            await self._refresh_captcha(page)

        print("[!] Không vượt qua được Captcha sau 5 lần thử.")
        return False

    async def _refresh_captcha(self, page):
        """Click nút đổi captcha khác"""
        try:
            refresh_btn = page.locator('.refresh-capthca-btn-new, a[onclick*="ebot"]')
            if await refresh_btn.count() > 0:
                await refresh_btn.first.click(force=True)
            await asyncio.sleep(2)
        except Exception:
            pass

    async def run(self):
        print("="*65)
        print("  ⚡ ZEFOY FAVORITES AUTO-BOOSTER v3 (GEMINI VISION SOLVER) ⚡")
        print(f"  Target URL : {self.target_url}")
        print(f"  AI Model   : {GEMINI_MODEL}")
        print(f"  Target Loop: {'Vô hạn' if self.loops == 0 else f'{self.loops} lần'}")
        print("="*65)

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-infobars'
                ]
            )

            context = await browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            )

            page = await context.new_page()
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => false });")

            print("\n[*] Đang truy cập Zefoy.com...")
            await page.goto(ZEFOY_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # BƯỚC 1: TỰ ĐỘNG GIẢI CAPTCHA BẰNG AI
            content = await page.content()
            if 'captchalogin' in content:
                passed = await self.auto_solve_captcha(page)
                if not passed:
                    print("[!] Không thể tiếp tục do chưa vượt qua Captcha.")
                    await browser.close()
                    return

            await asyncio.sleep(2)

            # BƯỚC 2: KÍCH HOẠT MENU FAVORITES
            print("\n[*] Đang mở menu Favorites...")
            fav_btn = page.locator(".t-favorites-button")
            if await fav_btn.count() > 0:
                await fav_btn.first.click(force=True)
                print("[✅] Đã click nút Favorites!")
            else:
                await page.evaluate("""() => {
                    const btn = document.querySelector('.t-favorites-button');
                    if (btn) btn.click();
                }""")

            await asyncio.sleep(2)

            # Gỡ class ẩn để lộ panel form
            await page.evaluate("""() => {
                document.querySelectorAll('.colsmenu').forEach(e => e.classList.add('nonec'));
                const panel = document.querySelector('.t-favorites-menu');
                if (panel) {
                    panel.classList.remove('nonec');
                    panel.style.display = 'block';
                }
            }""")
            await asyncio.sleep(1)

            # BƯỚC 3: VÒNG LẶP AUTO BUFF
            round_count = 0
            while True:
                if self.loops > 0 and round_count >= self.loops:
                    print(f"\n[DONE] Hoàn tất đủ {self.loops} lượt.")
                    break

                round_count += 1
                elapsed = int(time.time() - self.start_time)
                print(f"\n{'='*55}")
                print(f"  Vòng #{round_count} | Đã buff: {self.total_sent} lần | Thời gian: {elapsed}s")
                print(f"{'='*55}")

                status = await self._execute_cycle(page)

                if status == "sent":
                    self.total_sent += 1
                    print(f"\n[🔥 THÀNH CÔNG] Đã buff Favorites thành công! (Tổng: {self.total_sent})")
                    await self._wait_cooldown(page)
                elif status == "cooldown":
                    await self._wait_cooldown(page)
                else:
                    print("[!] Thử lại chu trình sau 8 giây...")
                    await asyncio.sleep(8)

            await browser.close()

    async def _execute_cycle(self, page):
        """Điền link -> Bấm Search -> Chọn limit 100 -> Bấm Buff"""
        try:
            # 1. Tìm ô nhập link
            input_box = page.locator(
                '.t-favorites-menu input[type="search"], .t-favorites-menu input[placeholder*="URL"], .t-favorites-menu input[type="text"]'
            )
            if await input_box.count() == 0:
                print("[!] Không tìm thấy ô nhập link!")
                return "retry"

            target_input = input_box.first
            await target_input.click()
            await target_input.fill("")
            await asyncio.sleep(0.3)
            await target_input.fill(self.target_url)
            print(f"[*] Đã điền link TikTok: {self.target_url}")
            await asyncio.sleep(0.5)

            # 2. Bấm Search
            print("[*] Đang bấm nút Search...")
            search_btn = page.locator(
                '.t-favorites-menu button[type="submit"], .t-favorites-menu button:has-text("Search")'
            )
            if await search_btn.count() > 0:
                await search_btn.first.click(force=True)
            else:
                await target_input.press("Enter")

            try:
                await target_input.press("Enter")
            except Exception:
                pass

            # 3. Chờ phản hồi
            print("[*] Đang chờ server Zefoy xử lý kết quả...")
            action_clicked = False

            for wait_sec in range(15):
                await asyncio.sleep(1)

                # A. Chọn limit 100 từ dropdown nếu có
                selects = page.locator('.t-favorites-menu select')
                if await selects.count() > 0:
                    for s_idx in range(await selects.count()):
                        sel = selects.nth(s_idx)
                        options = await sel.locator('option').all_inner_texts()
                        print(f"[*] Phát hiện dropdown limit: {options}")

                        chosen = False
                        for opt in options:
                            if '100' in opt:
                                await sel.select_option(label=opt)
                                print(f"[✅] Đã chọn limit: {opt}")
                                chosen = True
                                break
                        if not chosen:
                            try:
                                await sel.select_option(value='100')
                                print("[✅] Đã chọn value='100'")
                                chosen = True
                            except Exception:
                                pass
                        if not chosen and len(options) > 0:
                            await sel.select_option(index=len(options)-1)
                            print(f"[*] Đã chọn mức tối đa: {options[-1]}")
                        await asyncio.sleep(0.5)

                # B. Bấm nút buff
                result_container = page.locator('#c2VuZF9mb2xsb3dlcnNfdGlrdG9L, .t-favorites-menu .card-ortlax')
                action_btns = result_container.locator('button:not([type="submit"]):not(:has-text("Search"))')

                if await action_btns.count() == 0:
                    action_btns = page.locator('#c2VuZF9mb2xsb3dlcnNfdGlrdG9L button, .t-favorites-menu form ~ div button')

                if await action_btns.count() > 0:
                    for b_i in range(await action_btns.count()):
                        btn = action_btns.nth(b_i)
                        txt = (await btn.inner_text()).strip()
                        if 'search' not in txt.lower():
                            print(f"[🔥] Phát hiện nút kích hoạt buff: '{txt}'! Đang click...")
                            await btn.click(force=True)
                            action_clicked = True
                            break

                if action_clicked:
                    break

                # C. Kiểm tra Cooldown sẵn
                panel_text = await page.locator('.t-favorites-menu').inner_text()
                if re.search(r'please wait\s*\d+\s*(?:minute|second|s|m)', panel_text, re.I) or re.search(r'\d{1,2}\s*:\s*\d{2}', panel_text):
                    print("[⏳] Phát hiện thông báo Cooldown đang đếm ngược.")
                    return "cooldown"

            if action_clicked:
                await asyncio.sleep(4)
                return "sent"

            final_text = await page.locator('.t-favorites-menu').inner_text()
            if re.search(r'\d{1,2}\s*:\s*\d{2}', final_text) or 'please wait' in final_text.lower():
                return "cooldown"

            print("[?] Chưa thấy kết quả hoặc server phản hồi chậm.")
            return "retry"

        except Exception as e:
            print(f"[!] Lỗi chu trình: {e}")
            return "retry"

    async def _wait_cooldown(self, page):
        """Theo dõi chính xác đồng hồ đếm ngược Cooldown"""
        print("[⏳] Bắt đầu theo dõi thời gian Cooldown...")

        empty_checks = 0
        for _ in range(72): # Tối đa 6 phút
            await asyncio.sleep(5)

            try:
                text = await page.evaluate("""() => {
                    const panel = document.querySelector('.t-favorites-menu');
                    return panel ? panel.innerText : document.body.innerText;
                }""")

                match_min_sec = re.search(r'(\d+)\s*m(?:inutes?)?\s*(\d+)\s*s(?:econds?)?', text, re.I)
                match_sec_only = re.search(r'(\d+)\s*s(?:econds?)?', text, re.I)
                match_colon = re.search(r'(\d{1,2})\s*:\s*(\d{2})', text)

                time_str = None
                total_seconds = 0

                if match_min_sec:
                    m = int(match_min_sec.group(1))
                    s = int(match_min_sec.group(2))
                    total_seconds = m * 60 + s
                    time_str = f"{m} phút {s} giây"
                elif match_colon:
                    m = int(match_colon.group(1))
                    s = int(match_colon.group(2))
                    total_seconds = m * 60 + s
                    time_str = f"{m}:{s:02d}"
                elif match_sec_only and 'please wait' in text.lower():
                    s = int(match_sec_only.group(1))
                    total_seconds = s
                    time_str = f"{s} giây"

                if time_str and total_seconds > 0:
                    empty_checks = 0
                    print(f"\r[⏳ Cooldown]: Còn lại {time_str} ({total_seconds}s)...   ", end="", flush=True)
                else:
                    empty_checks += 1
                    if empty_checks >= 2:
                        print("\n[✅] Thời gian chờ đã kết thúc! Bắt đầu lượt buff tiếp theo.")
                        return

            except Exception:
                pass

        print("\n[*] Hết thời gian chờ tối đa. Chuẩn bị lượt mới...")


def main():
    parser = argparse.ArgumentParser(description="⚡ TikTok Zefoy Favorites Booster v3 ⚡")
    parser.add_argument("--url", required=True, help="Link TikTok (video hoặc photo)")
    parser.add_argument("--api-key", default=None, help="Gemini API Key")
    parser.add_argument("--loops", type=int, default=0, help="Số lần lặp lại (0 = vô hạn)")
    args = parser.parse_args()

    bot = ZefoyFavoritesBot(target_url=args.url, api_key=args.api_key, loops=args.loops)
    asyncio.run(bot.run())

if __name__ == "__main__":
    main()
