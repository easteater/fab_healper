import os
import sys
import time
from playwright.sync_api import sync_playwright

URL = "https://www.fab.com/search?ui_filter_price=1&is_free=1&sort_by=-firstPublishedAt"
SESSION_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".session")
JS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clear_saved.js")


def main():
    auto_close = "--auto-close" in sys.argv
    os.makedirs(SESSION_DIR, exist_ok=True)
    js_code = open(JS_FILE, encoding="utf-8").read().strip()
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            SESSION_DIR,
            headless=False,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-user-check",
                "--disable-dev-shm-usage",
                "--lang=en-US",
                "--disable-extensions",
                "--remote-debugging-port=9222",
            ],
        )
        page = browser.pages[0] if browser.pages else browser.new_page()
        # stealth 补丁(与主启动脚本各自独立,互不影响)
        page.add_init_script(r"""
        () => {
          const np = window.Navigator.prototype;
          if (!Object.getOwnPropertyDescriptor(np, 'webdriver')) {
            Object.defineProperty(np, 'webdriver', {get: () => undefined});
          }
          if (!Object.getOwnPropertyDescriptor(np, 'languages')) {
            Object.defineProperty(np, 'languages', {get: () => ['en-US', 'en']});
          }
        }
        """)
        page.goto(URL, wait_until="domcontentloaded", timeout=120000)
        # 等 1 秒让列表渲染稳定,避免边删边被覆盖
        time.sleep(1)
        for _ in range(30):
            n = page.evaluate("document.querySelectorAll('[class*=\"fabkit-Surface-root\"]').length")
            if n > 0:
                break
            time.sleep(1)
        result = page.evaluate(js_code)
        print("【步骤1】清除已保存到库的商品")
        print("  已移除已保存商品数:", result.get("removed"))
        print("  会话(cookies/登录态)目录:", SESSION_DIR)
        print("  CDP 端点(供步骤2复用): http://127.0.0.1:9222")
        if auto_close:
            browser.close()
            print("已关闭(自动)")
        else:
            input("浏览器保持打开(已清除已保存商品),按回车键关闭...")
            browser.close()
            print("已关闭")


if __name__ == "__main__":
    main()
