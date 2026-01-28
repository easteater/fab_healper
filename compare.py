import time
import os
import urllib.parse as urlparse
from datetime import datetime
from curl_cffi import requests
from db import db

# ================= 配置区 =================
CURL_FILE = "curl.txt"
UNACQUIRED_LOG = "unacquired_list.log" # 专门存放未入库 UID 的文件
BATCH_SIZE = 24  
DELAY = 1.5      
# ==========================================

def extract_val(source, key):
    if key not in source: return None
    start_index = source.find(key) + len(key)
    actual_start = -1
    for i in range(start_index, len(source)):
        if source[i] not in [':', '=', ' ', "'", '"']:
            actual_start = i
            break
    if actual_start == -1: return None
    res = ""
    for char in source[actual_start:]:
        if char in [';', "'", '"', '\n', '\r']:
            break
        res += char
    return res.strip()

def get_auth_config():
    if not os.path.exists(CURL_FILE): return None
    with open(CURL_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    s_id = extract_val(content, 'fab_sessionid')
    c_csrf = extract_val(content, 'fab_csrftoken')
    cf_clear = extract_val(content, 'cf_clearance')
    
    if not s_id or not c_csrf:
        print("[!] Auth Parsing Failed!")
        return None

    return {
        'cookie': f'fab_csrftoken={c_csrf}; fab_sessionid={s_id}; cf_clearance={cf_clear};',
        'x-csrftoken': c_csrf,
        'user-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        'accept': 'application/json, text/plain, */*',
        'referer': 'https://www.fab.com/zh-cn/search?is_free=1',
        'x-requested-with': 'XMLHttpRequest'
    }

def compare_assets():
    headers = get_auth_config()
    if not headers: return

    # 1. 获取 DB 中所有未入库的
    with db._get_conn() as conn:
        cursor = conn.execute('SELECT fab_uid FROM fab_assets WHERE is_acquired = 0')
        pending_uids = [row[0] for row in cursor.fetchall()]

    if not pending_uids:
        print("[*] No pending assets to compare.")
        return

    print(f"[*] Total {len(pending_uids)} pending assets. Checking status...")
    
    # 每次运行前清空旧的未入库日志，只保留当前最准确的名单
    with open(UNACQUIRED_LOG, "w") as f:
        f.write(f"# Unacquired Assets List - {datetime.now()}\n")

    session = requests.Session()
    new_acquired = 0
    still_unacquired = 0

    for i in range(0, len(pending_uids), BATCH_SIZE):
        batch = pending_uids[i : i + BATCH_SIZE]
        params = urlparse.urlencode([('listing_ids', uid) for uid in batch])
        api_url = f"https://www.fab.com/i/users/me/listings-states?{params}"

        try:
            resp = session.get(api_url, headers=headers, impersonate="chrome120", timeout=30)
            
            if resp.status_code == 200:
                data = resp.json()
                for item in data:
                    uid = item.get('uid')
                    is_acq = item.get('acquired', False)
                    
                    if is_acq:
                        db.update_asset(uid, is_acquired=1, acquired_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                        new_acquired += 1
                    else:
                        # 记录到未入库日志
                        with open(UNACQUIRED_LOG, "a") as f:
                            f.write(f"{uid}\n")
                        still_unacquired += 1
                
                print(f"[*] Processed: {min(i + BATCH_SIZE, len(pending_uids))}/{len(pending_uids)} | New Acquired: {new_acquired} | Still Unacquired: {still_unacquired}", end='\r')
            
            elif resp.status_code == 403:
                print(f"\n[!] 403 Forbidden. Update your Token.")
                break
            else:
                print(f"\n[!] HTTP Error {resp.status_code}")
                break
                
        except Exception as e:
            print(f"\n[!] Request Error: {e}")
            break
        
        time.sleep(DELAY)

    print(f"\n\n[*] Task Finished.")
    print(f"[*] New mark as ACQUIRED: {new_acquired}")
    print(f"[*] STILL UNACQUIRED: {still_unacquired} (Check: {UNACQUIRED_LOG})")

if __name__ == "__main__":
    compare_assets()