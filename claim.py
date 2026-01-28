import time
import os
from datetime import datetime
from curl_cffi import requests
from db import db 

# ================= 配置区 =================
CURL_FILE = "curl.txt"
DELAY = 2.5  # 下单请求间隔
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
    
    if not s_id or not c_csrf: return None

    return {
        'cookie': f'fab_csrftoken={c_csrf}; fab_sessionid={s_id}; cf_clearance={cf_clear};',
        'x-csrftoken': c_csrf,
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'accept': 'application/json, text/plain, */*',
        'content-type': 'multipart/form-data; boundary=----WebKitFormBoundaryl229K9g1SIGFRADA',
        'origin': 'https://www.fab.com',
        'x-requested-with': 'XMLHttpRequest'
    }

def start_claiming():
    auth = get_auth_config()
    if not auth:
        print("[!] 权限初始化失败")
        return

    # 1. 查找所有未购买且至少有一个 OfferID 的记录
    with db._get_conn() as conn:
        cursor = conn.execute('''
            SELECT fab_uid, offer_id_1, offer_id_2, retry_count 
            FROM fab_assets 
            WHERE is_acquired = 0 AND (offer_id_1 IS NOT NULL OR offer_id_2 IS NOT NULL)
        ''')
        pending_assets = cursor.fetchall()

    if not pending_assets:
        print("[*] 库中无待处理资产。")
        return

    print(f"[*] 准备处理 {len(pending_assets)} 个资源 (支持双 Offer 下单)...")
    
    session = requests.Session()

    for idx, (uid, oid1, oid2, retries) in enumerate(pending_assets):
        # 将非空的 OfferID 放入待处理列表
        offers_to_claim = []
        if oid1: offers_to_claim.append(oid1)
        if oid2: offers_to_claim.append(oid2)

        for sub_idx, offer_id in enumerate(offers_to_claim):
            api_url = f"https://www.fab.com/i/listings/{uid}/add-to-library"
            raw_data = (
                f"------WebKitFormBoundaryl229K9g1SIGFRADA\r\n"
                f"Content-Disposition: form-data; name=\"offer_id\"\r\n\r\n"
                f"{offer_id}\r\n"
                f"------WebKitFormBoundaryl229K9g1SIGFRADA--\r\n"
            )
            
            headers = auth.copy()
            headers['referer'] = f"https://www.fab.com/zh-cn/listings/{uid}"

            try:
                resp = session.post(api_url, headers=headers, data=raw_data.encode('utf-8'), impersonate="chrome120", timeout=30)
                
                res_text = resp.text.lower()
                if resp.status_code in [200, 201] and ('"success":true' in res_text or '"id"' in res_text):
                    status = f"SUCCESS (Offer {sub_idx+1})"
                elif resp.status_code == 403:
                    print(f"\n[!] 403 Forbidden. 停止运行。")
                    return
                else:
                    status = f"FAIL (Offer {sub_idx+1}) - {resp.status_code}"
                    db.update_asset(uid, retry_count=(retries or 0)+1, last_error=f"Offer{sub_idx+1}_Fail_{resp.status_code}")

                print(f"[*] [{idx+1}/{len(pending_assets)}] UID: {uid[:8]}... -> {status}", end='\r')

            except Exception as e:
                print(f"\n[!] 异常: {e}")
                return
            
            # 同一个 UID 的两个 Offer 之间也稍微停顿下
            time.sleep(DELAY)

    print(f"\n\n[*] 下单批次结束。请运行 compare.py 确认最终状态。")

if __name__ == "__main__":
    start_claiming()