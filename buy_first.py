import os
import sys
import time
from playwright.sync_api import sync_playwright

URL = "https://www.fab.com/search?ui_filter_price=1&is_free=1&sort_by=-firstPublishedAt"
SESSION_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".session")
JS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "buy_first.js")


def main():
    auto_close = "--auto-close" in sys.argv
    os.makedirs(SESSION_DIR, exist_ok=True)
    js_code = open(JS_FILE, encoding="utf-8").read()
    license_js = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "select_license.js"), encoding="utf-8").read()
    library_js = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "add_library.js"), encoding="utf-8").read()
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
        # 注入 window.__fab(步骤A/步骤B)
        page.add_init_script(js_code)
        page.add_init_script(license_js)
        page.add_init_script(library_js)
        # stealth 补丁(与主启动脚本各自独立)
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
        # 等列表渲染完成
        for _ in range(30):
            n = page.evaluate("document.querySelectorAll('[class*=\"fabkit-Surface-root\"]').length")
            if n > 0:
                break
            time.sleep(1)

        # 等列表渲染完成后,再等 1 秒
        time.sleep(1)
        # 步骤A: 点击第一个未购买商品
        first = page.evaluate("window.__fab.clickFirstUnpurchased()")
        print("【步骤2】点击第一个未购买商品:", first)
        if not first.get("ok"):
            print("无可购商品(可能都已入库或列表为空)。先运行 clear_saved.py 清除已购买项。")
            browser.close()
            return

        # 等待商品页加载完成(出现下单按钮)
        for _ in range(30):
            has_btn = page.evaluate("""
                () => Array.from(document.querySelectorAll('button')).some(
                    b => (b.textContent||'').includes('添加至购物车')
                        || (b.textContent||'').includes('立即购买')
                        || (b.textContent||'').includes('添加到我的库')
                )
            """)
            if has_btn:
                break
            time.sleep(1)

        # 步骤B: 点下单
        buy = page.evaluate("window.__fab.buyNow()")
        print("【步骤2】下单结果:", buy)

        # 检测是否完成任务(页面出现"已保存在我的库中"),完成即停掉
        complete = bool(buy.get("complete"))
        if not complete:
            for _ in range(10):
                if page.evaluate("window.__fab.isComplete()"):
                    complete = True
                    break
                time.sleep(0.5)

        if complete:
            print("【步骤2】任务完成(已保存在我的库中)。")
            browser.close()
            print("已关闭")
            return

        if auto_close:
            browser.close()
            print("已关闭(自动)")
        else:
            input("浏览器保持打开,按回车键关闭...")
            browser.close()
            print("已关闭")


if __name__ == "__main__":
    main()
