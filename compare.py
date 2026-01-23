import time
import os
import urllib.parse as urlparse
from datetime import datetime
from curl_cffi import requests  # 必须使用这个库绕过 TLS 指纹检测

# ================= 配置区 =================
CURL_FILE = "curl.txt"
DATE_STR = datetime.now().strftime('%Y%m%d')
INPUT_FILE = f"./fab.txt"
ACQUIRED_FILE = f"./acquired.txt"
UNACQUIRED_FILE = f"./unacquired.txt"

BATCH_SIZE = 24  # 保持在这个量级比较稳
DELAY = 1.5      # 稍微加长间歇，防止被检测出频率异常
# ==========================================

def extract_val(source, key):
    """最直接的关键字提取算法 (Direct Keyword Extraction)"""
    if key not in source: return None
    try:
        start_index = source.find(key) + len(key)
        # 自动跨过冒号或等号
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
    except:
        return None

def get_auth_config():
    if not os.path.exists(CURL_FILE): return None
    with open(CURL_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    s_id = extract_val(content, 'fab_sessionid')
    c_csrf = extract_val(content, 'fab_csrftoken')
    cf_clear = extract_val(content, 'cf_clearance')
    # 强制使用最新的 Chrome 143 的 UA 字符串
    ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"

    # 打印提取到的信息供你人肉确认
    print("=" * 50)
    print(f"[*] Session ID  : {s_id}")
    print(f"[*] CSRF Token  : {c_csrf}")
    print(f"[*] CF Clearance: {cf_clear[:30] if cf_clear else 'NOT FOUND'}...")
    print("=" * 50)

    if not s_id or not c_csrf:
        print("[!] 错误：未能在 curl.txt 中找到关键 Token！")
        return None

    # 模拟真实浏览器请求头
    headers = {
        'cookie': f'fab_csrftoken={c_csrf}; fab_sessionid={s_id}; cf_clearance={cf_clear};',
        'x-csrftoken': c_csrf,
        'user-agent': ua,
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'zh-CN,zh;q=0.9',
        'referer': 'https://www.fab.com/zh-cn/search?is_free=1',
        'x-requested-with': 'XMLHttpRequest'
    }
    return headers

def compare_assets():
    headers = get_auth_config()
    if not headers: return

    if not os.path.exists(INPUT_FILE):
        print(f"[!] 找不到输入文件: {INPUT_FILE}")
        return

    with open(INPUT_FILE, "r") as f:
        all_uids = [line.strip() for line in f if line.strip()]

    print(f"[*] 总计 {len(all_uids)} 个 UID，开始通过 TLS 模拟执行...")
    
    # 实时存盘结果
    open(ACQUIRED_FILE, 'w').close()
    open(UNACQUIRED_FILE, 'w').close()

    session = requests.Session()
    count_acq, count_unacq = 0, 0

    for i in range(0, len(all_uids), BATCH_SIZE):
        batch = all_uids[i : i + BATCH_SIZE]
        params = urlparse.urlencode([('listing_ids', uid) for uid in batch])
        api_url = f"https://www.fab.com/i/users/me/listings-states?{params}"

        try:
            # 核心：impersonate="chrome120" 让 Cloudflare 认为你是真实浏览器
            resp = session.get(api_url, headers=headers, impersonate="chrome120", timeout=30)
            
            if resp.status_code == 200:
                data = resp.json()
                acq_batch = [item['uid'] for item in data if item.get('acquired')]
                unacq_batch = [item['uid'] for item in data if not item.get('acquired')]
                
                if acq_batch:
                    with open(ACQUIRED_FILE, 'a') as f: f.writelines(f"{u}\n" for u in acq_batch)
                    count_acq += len(acq_batch)
                if unacq_batch:
                    with open(UNACQUIRED_FILE, 'a') as f: f.writelines(f"{u}\n" for u in unacq_batch)
                    count_unacq += len(unacq_batch)

                print(f"[*] 进度: {i+len(batch)}/{len(all_uids)} | 已入库: {count_acq} | 未入库: {count_unacq}", end='\r')
            else:
                print(f"\n[!] 异常: HTTP {resp.status_code}")
                if "Just a moment" in resp.text:
                    print("[!] 痛点确认：Cloudflare 5秒盾拦截。你的 cf_clearance 可能失效了。")
                break
        except Exception as e:
            print(f"\n[!] 崩溃: {e}")
            break
        
        time.sleep(DELAY)

    print(f"\n\n[*] 执行完毕。未入库名单见: {UNACQUIRED_FILE}")

if __name__ == "__main__":
    compare_assets()