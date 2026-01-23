import time
import os
import re
from datetime import datetime
from curl_cffi import requests

# ================= 配置区 =================
CURL_FILE = "curl.txt"
SOURCE_FILE = "unacquired.txt"  # 之前的未入库 UID 列表
OUTPUT_FILE = "offerIds.txt"    # 格式: uid,offerId
LOG_FILE = "get_offer_log.txt"

DELAY = 1.5  # 增加一点点延迟，保护 IP 不被详情页反爬策略盯上
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
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'referer': 'https://www.fab.com/zh-cn/search'
    }

def get_offer_ids():
    headers = get_auth_headers()
    if not headers:
        print("[!] 权限初始化失败，请检查 curl.txt")
        return

    if not os.path.exists(SOURCE_FILE):
        print(f"[!] 找不到源文件: {SOURCE_FILE}")
        return

    # 1. 加载所有需要处理的 UID
    with open(SOURCE_FILE, "r") as f:
        target_uids = [line.strip() for line in f if line.strip()]

    # 2. 加载已经处理过的 UID (用于断点续爬/去重)
    processed_uids = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r') as f:
            for line in f:
                if ',' in line:
                    processed_uids.add(line.split(',')[0].strip())

    print(f"[*] 准备解析 {len(target_uids)} 个 UID。已跳过 {len(processed_uids)} 个已处理项。")
    
    session = requests.Session()
    total_found = 0

    for idx, uid in enumerate(target_uids):
        # 跳过已存在的
        if uid in processed_uids:
            continue

        url = f"https://www.fab.com/zh-cn/listings/{uid}"
        
        try:
            # impersonate 关键，详情页对指纹检查更严
            resp = session.get(url, headers=headers, impersonate="chrome120", timeout=30)
            
            if resp.status_code == 200:
                # 匹配 32 位十六进制 offerId
                found = re.findall(r'offerId["\']?\s*[:=]\s*["\']([a-f0-9]{32})["\']', resp.text)
                
                if found:
                    # 一个 UID 页面可能存在多个 OfferID，全部存下来，后续下单一一尝试
                    unique_offers = list(set(found))
                    with open(OUTPUT_FILE, 'a') as f:
                        for oid in unique_offers:
                            f.write(f"{uid},{oid}\n")
                    
                    total_found += len(unique_offers)
                    status = f"FOUND({len(unique_offers)})"
                else:
                    status = "NOT_FOUND"
                    # 可选：记录没找到的 UID 到日志
                    with open(LOG_FILE, 'a') as log:
                        log.write(f"{datetime.now()} | {uid} | NO_OFFER_FOUND\n")
            
            elif resp.status_code == 403:
                print(f"\n[!] 403 Forbidden. 盾拦截。请重新获取 curl.txt 并刷新 cf_clearance。")
                break
            else:
                status = f"HTTP_{resp.status_code}"

            print(f"[*] [{idx+1}/{len(target_uids)}] UID: {uid[:8]}... -> {status} | Total OIDs: {total_found}", end='\r')

        except Exception as e:
            print(f"\n[!] 异常 UID {uid}: {e}")
            time.sleep(5)
            continue
        
        time.sleep(DELAY)

    print(f"\n\n[*] 任务完成。映射关系已存入: {OUTPUT_FILE}")

if __name__ == "__main__":
    get_offer_ids()