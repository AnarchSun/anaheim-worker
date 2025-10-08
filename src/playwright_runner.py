import json
import time

from playwright.sync_api import sync_playwright


def run_checks(pages, selectors, out_path="/work/data/dev_errors.json"):
    out=[]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()
        for url in pages:
            try:
                page.goto(url, timeout=15000)
                time.sleep(1)
                logs=[]
                def on_console(msg):
                    logs.append({"type":msg.type,"text":msg.text})
                page.on("console", on_console)
                for sel in selectors:
                    try:
                        if page.query_selector(sel):
                            page.click(sel, timeout=3000)
                            time.sleep(0.5)
                    except Exception:
                        pass
                out.append({"url":url,"console":logs})
            except Exception as e:
                out.append({"url":url,"error":str(e)})
        browser.close()
    with open(out_path,"w",encoding="utf-8") as f:
        json.dump(out,f,indent=2)
    return out
