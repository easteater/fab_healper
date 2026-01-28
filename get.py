import time
import sys
import os
import urllib.parse as urlparse
from datetime import datetime
from curl_cffi import requests
from db import db 

# ================= 配置区 =================
BASE_URL = "https://www.fab.com/i/listings/search?is_free=1&sort_by=-firstPublishedAt"
DELAY = 2         
RETRY_DELAY = 60  
MAX_RETRIES = 99   
CURSOR_FILE = "./lastCursor.txt"
STOP_THRESHOLD = 10 # 连续重复超过 10 个则停止
# ==========================================

def get_config():
    """解析命令行参数"""
    start_cursor = None
    auto_return = 1 # 默认开启自动结束
    
    if len(sys.argv) >= 2:
        start_cursor = sys.argv[1]
    elif os.path.exists(CURSOR_FILE):
        with open(CURSOR_FILE, "r") as f:
            start_cursor = f.read().strip()
            
    if len(sys.argv) >= 3:
        try:
            auto_return = int(sys.argv[2])
        except:
            auto_return = 1
            
    return start_cursor, auto_return

def save_current_cursor(cursor):
    if cursor:
        with open(CURSOR_FILE, "w") as f:
            f.write(cursor)

def extract_cursor(url):
    if not url: return None
    parsed = urlparse.urlparse(url)
    return urlparse.parse_qs(parsed.query).get('cursor', [None])[0]

def start_crawl():
    current_cursor, auto_return = get_config()
    
    retry_count = 0
    total_saved = 0
    consecutive_exist_count = 0 # 连续存在的计数器
    
    print(f"[*] 配置: autoReturn={'开启' if auto_return else '关闭'} | 阈值={STOP_THRESHOLD}")

    while True:
        url = f"{BASE_URL}&cursor={current_cursor}" if current_cursor else BASE_URL
        if current_cursor:
            save_current_cursor(current_cursor)
            
        print(f"[*] [{datetime.now().strftime('%H:%M:%S')}] 正在请求: {url}")
        
        try:
            res = requests.get(url, impersonate="chrome120", timeout=15)
            
            if res.status_code == 403:
                retry_count += 1
                if retry_count <= MAX_RETRIES:
                    print(f"[!] 403 Forbidden. 重试 {retry_count}...")
                    time.sleep(RETRY_DELAY)
                    continue 
                break
            
            if res.status_code == 200:
                retry_count = 0 
                data = res.json()
                results = data.get("results", [])
                
                if not results:
                    print("[*] 无数据返回，可能已到底。")
                    break

                # 处理当前页数据
                uids = [item.get("uid") for item in results if item.get("uid")]
                
                # 调用修改后的 add_uids
                new_count, exist_count = db.add_uids(uids)
                total_saved += new_count
                
                # 连续存在逻辑
                if new_count == 0:
                    consecutive_exist_count += exist_count
                else:
                    # 只要本页有新的插入，连续计数重置（或者根据需求微调为只重置 0）
                    consecutive_exist_count = 0

                print(f"[+] 新增: {new_count} | 数据库已存在: {exist_count} | 连续重复: {consecutive_exist_count}")

                # 检查自动结束
                if auto_return != 0 and consecutive_exist_count >= STOP_THRESHOLD:
                    print(f"\n[!] 检测到连续 {consecutive_exist_count} 条重复数据，触发自动结束。")
                    break

                next_url = data.get("next")
                if next_url:
                    current_cursor = extract_cursor(next_url)
                    time.sleep(DELAY)
                else:
                    print("[*] 采集完成，游标耗尽。")
                    if os.path.exists(CURSOR_FILE): os.remove(CURSOR_FILE)
                    break
            else:
                print(f"[!] HTTP {res.status_code}")
                break
                
        except Exception as e:
            print(f"[!] 异常: {e}")
            time.sleep(10)
            continue

if __name__ == "__main__":
    start_crawl()