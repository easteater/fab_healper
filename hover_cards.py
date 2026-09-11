import os
import time
from playwright.sync_api import sync_playwright

URL = "https://www.fab.com/search?ui_filter_price=1&is_free=1&sort_by=-firstPublishedAt"
SESSION_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".session")
JS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hover_cards.js")
# 有效点击后的停顿(秒)。调大更温和、不易拉黑 IP;调小更快
DELAY = 2
# 轮训完成后等新卡加载的停顿(秒)。调大更温和, 调小更快
POLL_DELAY = 2
# 每轮回退重检的卡片数。下轮从(末尾 - BACKOFF)开始, 不漏末尾几张; 设为 0 则每轮从头开始
BACKOFF = 5


def fetch_cards(page):
    # 重新获取列表卡片数;渲染中则等待
    n = 0
    for _ in range(30):
        n = page.evaluate("window.__fab.allCards().length")
        if n > 0:
            break
        time.sleep(1)
    return n


def main():
    os.makedirs(SESSION_DIR, exist_ok=True)
    js_code = open(JS_FILE, encoding="utf-8").read()
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
        page.add_init_script(js_code)
        page.goto(URL, wait_until="domcontentloaded", timeout=120000)
        time.sleep(2)
        total = 0
        iteration = 0
        prev_count = 0
        start = 0
        while True:
            # 一轮遍历: 从 start-BACKOFF 悬停到末尾, 全局点击所有未点过的"添加到我的库"按钮
            iteration += 1
            n = fetch_cards(page)
            loop_start = max(0, start - BACKOFF)
            print(f"[第 {iteration} 轮] 当前 {n} 张, 从第 {loop_start+1} 张遍历到第 {n} 张")
            locator = page.locator('[class*="fabkit-Surface-root"]')
            for i in range(loop_start, n):
                print(f"[遍历] 第 {i+1}/{n} 张")
                debug = page.evaluate("""(i) => {
                    const el = document.querySelectorAll('[class*="fabkit-Surface-root"]')[i];
                    if (!el) return null;
                    const r = el.getBoundingClientRect();
                    return {
                        rect: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
                        inView: r.y >= 0 && r.y <= window.innerHeight && r.height > 0,
                        text: el.textContent.replace(/\\s+/g, ' ').trim().slice(0, 30),
                    };
                }""", i)
                print(f"    坐标={debug['rect']} 视口内={debug['inView']} 文本={debug['text']}")
                if "已保存" in debug["text"]:
                    time.sleep(0.5)
                    continue
                before = page.evaluate("window.__fab.allAddButtons().length")
                locator.nth(i).hover()
                time.sleep(0.3)
                after = page.evaluate("window.__fab.allAddButtons().length")
                print(f"    悬停前按钮={before} 悬停后按钮={after}")
                clicked = page.evaluate("window.__fab.clickUnclickedAddButtons()")
                total += clicked
                if clicked > 0:
                    time.sleep(DELAY)  # 有效点击后再停顿, 无效(0点击)直接进下一张
            start = n  # 记录本轮末尾, 下一轮回退 BACKOFF 张重检
            # 轮训完成后等新卡加载, 再检查有没有新卡
            time.sleep(POLL_DELAY)
            new_count = fetch_cards(page)
            if new_count > prev_count:
                print(f"[第 {iteration} 轮] 发现 {new_count - prev_count} 张新卡 (共 {new_count})。继续。")
                prev_count = new_count
            else:
                print(f"[第 {iteration} 轮] 无新卡 (共 {new_count})。再等 {POLL_DELAY}s。")
            # 无限轮询, 直到手动停止 (Ctrl+C)
        browser.close()


if __name__ == "__main__":
    main()
