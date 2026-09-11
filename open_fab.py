import os

URL = "https://www.fab.com/search?ui_filter_price=1&is_free=1&sort_by=-firstPublishedAt"
SESSION_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".session")

STEALTH_INIT = r"""
() => {
  try {
    // 1. 隐藏 navigator.webdriver（最关键）
    const navProto = window.Navigator.prototype;
    if (!Object.getOwnPropertyDescriptor(navProto, 'webdriver')) {
      Object.defineProperty(navProto, 'webdriver', {get: () => undefined});
    }

    // 2. 补全 navigator.languages / language（避免 headless 默认值）
    if (!Object.getOwnPropertyDescriptor(navProto, 'languages')) {
      Object.defineProperty(navProto, 'languages', {get: () => ['en-US', 'en']});
    }
    if (!Object.getOwnPropertyDescriptor(navProto, 'language')) {
      Object.defineProperty(navProto, 'language', {get: () => 'en-US'});
    }

    // 3. 补全 PluginArray.length（真实 Chrome 为 3，headless 为 0）
    const pluginsProto = window.PluginArray.prototype;
    if (!Object.getOwnPropertyDescriptor(pluginsProto, 'length')) {
      Object.defineProperty(pluginsProto, 'length', {
        value: { value: 3, writable: false, enumerable: false, configurable: true, get() { return 3; } },
      });
    }
  } catch (e) {}
}
"""


def main():
    os.makedirs(SESSION_DIR, exist_ok=True)
    from playwright.sync_api import sync_playwright

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
            ],
        )
        page = browser.pages[0] if browser.pages else browser.new_page()
        page.add_init_script(STEALTH_INIT)
        page.goto(URL, wait_until="domcontentloaded", timeout=120000)
        print("已在内嵌浏览器打开（已加 stealth）:", URL)
        print("会话(cookies/登录态)目录:", SESSION_DIR)
        input("浏览器已打开,按回车键关闭...")
        browser.close()
        print("已关闭")


if __name__ == "__main__":
    main()
