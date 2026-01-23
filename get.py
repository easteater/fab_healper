import time
import sys
import os
import urllib.parse as urlparse
from datetime import datetime
from curl_cffi import requests

# 配置 
BASE_URL = "https://www.fab.com/i/listings/search?is_free=1&sort_by=-firstPublishedAt"
DELAY = 3         # 正常请求间隔
RETRY_DELAY = 60  # 触发403后的等待时间
MAX_RETRIES = 99   # 最大重试次数
DATE_STR = datetime.now().strftime('%Y%m%d')
DATA_FILE = f"./fab.txt"
CURSOR_FILE = "./lastCursor.txt"

def get_start_cursor():
    if len(sys.argv) >= 2:
        return sys.argv[1]
    if os.path.exists(CURSOR_FILE):
        with open(CURSOR_FILE, "r") as f:
            c = f.read().strip()
            if c: return c
    return None

def update_cursor_file(url):
    if not url: return
    parsed = urlparse.urlparse(url)
    cursor = urlparse.parse_qs(parsed.query).get('cursor', [None])[0]
    if cursor:
        with open(CURSOR_FILE, "w") as f:
            f.write(cursor)

def start_crawl():
    start_cursor = get_start_cursor()
    current_url = BASE_URL
    if start_cursor:
        print(f"[*] 起始游标: {start_cursor}")
        current_url = f"{BASE_URL}&cursor={start_cursor}"

    retry_count = 0
    while current_url:
        print(f"[*] 正在请求: {current_url}")
        try:
            res = requests.get(current_url, impersonate="chrome120", timeout=15)
            
            # 针对 403 处理
            if res.status_code == 403:
                retry_count += 1
                if retry_count <= MAX_RETRIES:
                    print(f"[!] 触发 403。第 {retry_count}/{MAX_RETRIES} 次尝试：Sleep {RETRY_DELAY}s 后重试...")
                    time.sleep(RETRY_DELAY)
                    continue # 重新开始当前循环，不切换 URL
                else:
                    print("[!!!] 达到最大重试次数，IP 可能已被深度限制。退出。")
                    break
            
            # 正常响应
            if res.status_code == 200:
                retry_count = 0 # 重置重试计数
                data = res.json()
                uids = [item.get("uid") for item in data.get("results", []) if item.get("uid")]
                
                if uids:
                    with open(DATA_FILE, "a") as f:
                        f.writelines(f"{uid}\n" for uid in uids)
                    print(f"[+] 写入 {len(uids)} 条数据")

                next_url = data.get("next")
                if next_url:
                    update_cursor_file(next_url)
                    current_url = next_url
                    time.sleep(DELAY)
                else:
                    print("[*] 任务结束。")
                    break
            else:
                print(f"[!] 其他异常状态码: {res.status_code}")
                break
                
        except Exception as e:
            print(f"[!] 异常: {e}")
            time.sleep(RETRY_DELAY)
            continue

if __name__ == "__main__":
    start_crawl()