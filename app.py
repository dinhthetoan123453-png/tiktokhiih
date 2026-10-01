#!/usr/bin/env python3
"""
⚡ TikTok Zefoy Favorites Booster - Render Web Service Edition ⚡
Tích hợp Web Server giám sát tiến độ + Chạy bot ngầm 24/7 với Gemini AI Captcha Solver.
"""

import os
import re
import sys
import time
import base64
import asyncio
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from playwright.async_api import async_playwright

ZEFOY_URL = "https://zefoy.com/"
DEFAULT_GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-3.5-flash-lite"
TARGET_URL = os.getenv("TIKTOK_URL", "https://www.tiktok.com/@toandinh0207/photo/7681249165866814741")
PORT = int(os.getenv("PORT", "10000"))

# Trạng thái toàn cục để hiển thị lên giao diện web
STATUS = {
    "total_sent": 0,
    "current_status": "Khởi động...",
    "cooldown": "Không",
    "uptime_start": time.time(),
    "last_update": "",
    "logs": []
}

def log(msg):
    timestamp = time.strftime("%H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    print(entry, flush=True)
    STATUS["logs"].append(entry)
    if len(STATUS["logs"]) > 40:
        STATUS["logs"].pop(0)
    STATUS["last_update"] = timestamp

class SimpleWebServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        uptime = int(time.time() - STATUS["uptime_start"])
        logs_html = "<br>".join(reversed(STATUS["logs"]))
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Zefoy TikTok Booster Status</title>
    <meta http-equiv="refresh" content="5">
    <style>
        body {{ font-family: monospace; background: #0d1117; color: #58a6ff; padding: 20px; }}
        .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; max-width: 800px; margin: auto; }}
        h2 {{ color: #2ea043; }}
        .badge {{ background: #238636; color: white; padding: 4px 8px; border-radius: 4px; }}
        .log-box {{ background: #000; color: #7ee787; padding: 15px; border-radius: 5px; height: 350px; overflow-y: auto; font-size: 13px; }}
    </style>
</head>
<body>
    <div class="card">
        <h2>⚡ Zefoy Favorites Booster (24/7 Cloud)</h2>
        <p><b>Target:</b> <a href="{TARGET_URL}" target="_blank" style="color: #79c0ff;">{TARGET_URL}</a></p>
        <p><b>Trạng thái:</b> <span class="badge">{STATUS['current_status']}</span></p>
        <p><b>Tổng lượt buff thành công:</b> <span style="font-size: 20px; font-weight: bold; color: #ff7b72;">{STATUS['total_sent']}</span></p>
        <p><b>Uptime:</b> {uptime}s | <b>Cập nhật lần cuối:</b> {STATUS['last_update']}</p>
        <h3>Nhật ký hoạt động (Tự refresh 5s):</h3>
        <div class="log-box">{logs_html}</div>
    </div>
</body>
</html>"""
        self.wfile.write(html.encode("utf-8"))

def start_web_server():
    server = HTTPServer(("0.0.0.0", PORT), SimpleWebServer)
    log(f"Web server giám sát đang chạy trên port {PORT}")
    server.serve_forever()

class ZefoyFavoritesBot:
    def __init__(self, target_url, api_key):
        self.target_url = target_url
        self.api_key = api_key

    def solve_captcha_api(self, image_bytes):
        b64_img = base64.b64encode(image_bytes).decode('utf-8')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={self.api_key}"
        prompt = "This is a text captcha image. Read the word or letters shown in this image. Output ONLY the letters in lowercase, with no spaces."
        payload = {
            "contents": [{"parts": [{"text": prompt}, {"inlineData": {"mimeType": "image/png", "data": b64_img}}]}],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": 20}
        }
        try:
            res = requests.post(url, json=payload, timeout=12)
            if res.status_code == 200:
                raw_text = res.json()['candidates'][0]['content']['parts'][0]['text']
                return re.sub(r'[^a-zA-Z]', '', raw_text).lower().strip()
        except Exception as e:
            log(f"Lỗi gọi Gemini API: {e}")
        return None

    async def run(self):
        STATUS["current_status"] = "Đang mở trình duyệt..."
        log("Khởi động Playwright...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False, # Chạy trong Xvfb ảo
                args=['--no-sandbox', '--disable-blink-features=AutomationControlled', '--disable-infobars']
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => false });")

            STATUS["current_status"] = "Đang nạp Zefoy..."
            log("Truy cập zefoy.com...")
            await page.goto(ZEFOY_URL, wait_until="domcontentloaded", timeout=40000)
            await asyncio.sleep(3)

            # Giải Captcha tự động
            content = await page.content()
            if 'captchalogin' in content:
                STATUS["current_status"] = "Đang giải Captcha bằng AI..."
                for attempt in range(1, 6):
                    log(f"AI giải Captcha lần #{attempt}...")
                    captcha_img = page.locator('#captcha-img')
                    await captcha_img.wait_for(state="visible", timeout=15000)
                    await asyncio.sleep(1)
                    img_bytes = await captcha_img.screenshot()
                    
                    text = self.solve_captcha_api(img_bytes)
                    if not text:
                        continue
                    log(f"Gemini nhận diện từ: '{text}'")
                    input_cap = page.locator('input[name="captchalogin"]')
                    await input_cap.fill(text)
                    await asyncio.sleep(0.5)
                    await page.locator('button.submit-captcha, button[type="submit"]').first.click()
                    await asyncio.sleep(4)
                    
                    c = await page.content()
                    if 'captchalogin' not in c and 'colsmenu' in c:
                        log("Vượt qua Captcha thành công!")
                        break

            await asyncio.sleep(2)
            # Mở menu Favorites
            STATUS["current_status"] = "Đang chọn Favorites..."
            fav_btn = page.locator(".t-favorites-button")
            if await fav_btn.count() > 0:
                await fav_btn.first.click(force=True)
            await asyncio.sleep(2)

            await page.evaluate("""() => {
                document.querySelectorAll('.colsmenu').forEach(e => e.classList.add('nonec'));
                const p = document.querySelector('.t-favorites-menu');
                if (p) { p.classList.remove('nonec'); p.style.display = 'block'; }
            }""")

            # Vòng lặp gửi
            round_idx = 0
            while True:
                round_idx += 1
                STATUS["current_status"] = f"Đang buff lượt #{round_idx}..."
                log(f"--- Bắt đầu lượt #{round_idx} ---")
                
                try:
                    input_box = page.locator('.t-favorites-menu input[type="search"], .t-favorites-menu input[type="text"]').first
                    await input_box.fill(self.target_url)
                    await asyncio.sleep(0.5)
                    
                    search_btn = page.locator('.t-favorites-menu button[type="submit"]').first
                    await search_btn.click(force=True)
                    await input_box.press("Enter")
                    log("Đã bấm Search, chờ kết quả...")

                    action_clicked = False
                    for _ in range(15):
                        await asyncio.sleep(1)
                        # Chọn limit 100
                        selects = page.locator('.t-favorites-menu select')
                        if await selects.count() > 0:
                            sel = selects.first
                            opts = await sel.locator('option').all_inner_texts()
                            for o in opts:
                                if '100' in o:
                                    await sel.select_option(label=o)
                                    log("Đã chọn limit: 100")
                                    break

                        # Bấm nút buff
                        result_btns = page.locator('#c2VuZF9mb2xsb3dlcnNfdGlrdG9L button, .t-favorites-menu form ~ div button')
                        if await result_btns.count() > 0:
                            for i in range(await result_btns.count()):
                                btn = result_btns.nth(i)
                                txt = (await btn.inner_text()).strip()
                                if 'search' not in txt.lower():
                                    log(f"Bấm nút kích hoạt: '{txt}'")
                                    await btn.click(force=True)
                                    action_clicked = True
                                    break
                        if action_clicked:
                            break

                    if action_clicked:
                        STATUS["total_sent"] += 1
                        log(f"✅ Gửi Favorites thành công! Tổng: {STATUS['total_sent']}")
                        await asyncio.sleep(4)

                    # Cooldown
                    STATUS["current_status"] = "Đang chờ Cooldown..."
                    log("Đang theo dõi Cooldown...")
                    for _ in range(70):
                        await asyncio.sleep(5)
                        text = await page.evaluate("() => document.querySelector('.t-favorites-menu')?.innerText || ''")
                        m = re.search(r'(\d+)\s*m\s*(\d+)\s*s', text) or re.search(r'(\d{1,2}):(\d{2})', text) or re.search(r'(\d+)\s*s', text)
                        if m:
                            STATUS["cooldown"] = m.group(0)
                        else:
                            STATUS["cooldown"] = "0s"
                            log("Hết thời gian Cooldown! Sẵn sàng cho lượt mới.")
                            break

                except Exception as e:
                    log(f"Lỗi: {e}")
                    await asyncio.sleep(8)

def start_bot_thread():
    bot = ZefoyFavoritesBot(TARGET_URL, DEFAULT_GEMINI_KEY)
    asyncio.run(bot.run())

if __name__ == "__main__":
    t = threading.Thread(target=start_bot_thread, daemon=True)
    t.start()
    start_web_server()
