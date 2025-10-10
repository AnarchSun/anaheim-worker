# anarcrypt.sol/anaheim-worker/src/playwright_runner.py
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError, Error as PWError
import traceback
import sys

LOG_FILE = "/work/data/devtools.log"

def run_checks(pages, selectors, out_path):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            for url in pages:
                page = context.new_page()
                try:
                    page.goto(url, timeout=15000)
                    for selector in selectors:
                        if not page.locator(selector).count():
                            log_line(f"⚠️ Missing selector {selector} on {url}")
                except (PWTimeoutError, PWError) as e:
                    log_line(f"🔥 Playwright error on {url}: {repr(e)}")
                finally:
                    page.close()
            browser.close()
    except PWError as e:
        log_line(f"❌ Global Playwright failure: {repr(e)}")
    except Exception as e:
        log_line(f"💥 Unexpected error: {repr(e)}\n{traceback.format_exc()}")

def log_line(line: str):
    """Safe logging that never throws, mais garde la trace."""
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
        sys.stdout.write(line + "\n")
    except OSError as e:
        sys.stderr.write(f"⚠️ Log write failed: {e}\n")