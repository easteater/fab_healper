import time
import os
import re
from datetime import datetime
from curl_cffi import requests
from db import db  # 确保 db.py 在同一路径

# ================= 配置区 =================
CURL_FILE = "curl.txt"
DELAY = 1.8  # 详情页有 WAF 监控，建议维持在 1.5s - 2.0s
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

def get_auth_headers():
    if not os.path.exists(CURL_FILE): return None
    with open(CURL_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    s_id = extract_val(content, 'fab_sessionid')
    c_csrf = extract_val(content, 'fab_csrftoken')
    cf_clear = extract_val(content, 'cf_clearance')
    
    return {
        'cookie': f'fab_csrftoken={c_csrf}; fab_sessionid={s_id}; cf_clearance={cf_clear};',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'referer': 'https://www.fab.com/zh-cn/search?is_free=1'
    }

def start_parsing():
    headers = get_auth_headers()
    if not headers:
        print("[!] 权限解析失败，请检查 curl.txt")
        return

    # 1. 核心查询：只查未入库的记录 (is_acquired = 0)，不管 offer_id 是否有值
    with db._get_conn() as conn:
        cursor = conn.execute('''
            SELECT fab_uid FROM fab_assets 
            WHERE is_acquired = 0
        ''')
        pending_items = [row[0] for row in cursor.fetchall()]

    if not pending_items:
        print("[*] 数据库中没有待处理的未入库资产。")
        return

    print(f"[*] 准备解析 {len(pending_items)} 个资产的 OfferID...")
    
    session = requests.Session()
    success_count = 0

    for idx, uid in enumerate(pending_items):
        url = f"https://www.fab.com/zh-cn/listings/{uid}"
        
        try:
            # 使用 chrome120 强力模拟，防止详情页 403
            resp = session.get(url, headers=headers, impersonate="chrome120", timeout=30)
            
            if resp.status_code == 200:
                # 匹配 32 位 hex 格式的 offerId
                found_oids = re.findall(r'offerId["\']?\s*[:=]\s*["\']([a-f0-9]{32})', resp.text)
                
                if found_oids:
                    # 去重并保持顺序 (dict.fromkeys 是 Python 3.7+ 的去重黑科技)
                    unique_oids = list(dict.fromkeys(found_oids))
                    oid1 = unique_oids[0]
                    oid2 = unique_oids[1] if len(unique_oids) > 1 else None
                    
                    # 关键：更新两个字段。如果 oid2 为 None，DB 对应字段会存入 NULL
                    db.update_asset(uid, 
                                   offer_id_1=oid1, 
                                   offer_id_2=oid2, 
                                   last_error=None)
                    
                    status_str = f"SUCCESS (OIDs: {len(unique_oids)})"
                    success_count += 1
                else:
                    status_str = "FAILED (No ID Found)"
                    db.update_asset(uid, last_error="OfferID not found in HTML content")
            
            elif resp.status_code == 403:
                print(f"\n[!] 403 Forbidden. 详情页盾厚，请去浏览器点击过盾并更新 curl.txt")
                break
            else:
                status_str = f"HTTP_{resp.status_code}"
                db.update_asset(uid, last_error=f"HTTP Status {resp.status_code}")

            print(f"[*] [{idx+1}/{len(pending_items)}] UID: {uid[:8]}... -> {status_str}", end='\r')

        except Exception as e:
            error_msg = str(e)[:50]
            print(f"\n[!] 异常 (UID: {uid}): {error_msg}")
            db.update_asset(uid, last_error=error_msg)
            time.sleep(5)
            continue
        
        time.sleep(DELAY)

    print(f"\n\n[*] 任务结束。本次成功解析并回填: {success_count} 条")

if __name__ == "__main__":
    start_parsing()