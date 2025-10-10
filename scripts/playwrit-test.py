from playwright.sync_api import sync_playwright
import time

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page()

    # Wait for server to start (max 30s)
    for _ in range(30):
        try:
            page.goto("http://localhost:3000", timeout=2000)
            print("✅ Server is ready!")
            break
        except:
            print("Waiting for server...")
            time.sleep(1)

    browser.close()
