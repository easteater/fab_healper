import time
import os
from datetime import datetime
from curl_cffi import requests

# ================= Configuration =================
CURL_FILE = "curl.txt"
SOURCE_FILE = "offerIds.txt" 
LOG_FILE = "claim_final_result.log"
DELAY = 2.5 
# =================================================

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
    
    if not s_id or not c_csrf: return None

    # 这里我们必须手动指定 Content-Type，因为我们要手动拼 boundary
    return {
        'cookie': f'fab_csrftoken={c_csrf}; fab_sessionid={s_id}; cf_clearance={cf_clear};',
        'x-csrftoken': c_csrf,
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'accept': 'application/json, text/plain, */*',
        'content-type': 'multipart/form-data; boundary=----WebKitFormBoundaryl229K9g1SIGFRADA',
        'origin': 'https://www.fab.com',
        'x-requested-with': 'XMLHttpRequest'
    }

def start_claiming():
    auth = get_auth_config()
    if not auth:
        print("[!] 权限解析失败")
        return

    if not os.path.exists(SOURCE_FILE):
        print(f"[!] 找不到文件: {SOURCE_FILE}")
        return

    with open(SOURCE_FILE, "r") as f:
        lines = [l.strip() for l in f if l.strip()]

    processed_offers = set()
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            for l in f:
                if "SUCCESS" in l:
                    parts = l.split('|')
                    if len(parts) > 2:
                        processed_offers.add(parts[2].strip())

    print(f"[*] 准备下单 {len(lines)} 个资源...")
    
    session = requests.Session()
    success_count = 0

    for idx, line in enumerate(lines):
        if ',' not in line: continue
        uid, offer_id = [x.strip() for x in line.split(',')]

        if offer_id in processed_offers:
            continue

        api_url = f"https://www.fab.com/i/listings/{uid}/add-to-library"
        
        # 核心改动：完全模拟你 curl 里的原始数据结构
        # 使用你提供的那个固定 boundary
        raw_data = (
            f"------WebKitFormBoundaryl229K9g1SIGFRADA\r\n"
            f"Content-Disposition: form-data; name=\"offer_id\"\r\n\r\n"
            f"{offer_id}\r\n"
            f"------WebKitFormBoundaryl229K9g1SIGFRADA--\r\n"
        )
        
        headers = auth.copy()
        headers['referer'] = f"https://www.fab.com/zh-cn/listings/{uid}"

        try:
            # 使用 data 发送原始字节流数据
            resp = session.post(
                api_url, 
                headers=headers, 
                data=raw_data.encode('utf-8'), 
                impersonate="chrome120", 
                timeout=30
            )

            ts = datetime.now().strftime('%H:%M:%S')
            
            if resp.status_code in [200, 201]:
                if '"success":true' in resp.text.lower() or '"id"' in resp.text.lower():
                    status = "SUCCESS"
                    success_count += 1
                else:
                    status = f"FAILED_MSG: {resp.text[:50]}"
            elif resp.status_code == 403:
                print(f"\n[!] 403 Forbidden. 可能是 cf_clearance 到期了。")
                break
            else:
                status = f"HTTP_{resp.status_code}"

            print(f"[*] [{idx+1}/{len(lines)}] UID: {uid[:8]}... -> {status}", end='\r')

            with open(LOG_FILE, 'a') as f:
                f.write(f"{ts} | {uid} | {offer_id} | {status}\n")

        except Exception as e:
            print(f"\n[!] 异常退出 (UID: {uid}): {e}")
            break

        time.sleep(DELAY)

    print(f"\n\n[*] 任务结束。成功入库: {success_count}")

if __name__ == "__main__":
    start_claiming()