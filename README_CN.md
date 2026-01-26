# Fab 资产自动添加入库，自动购买
# Fab 资产自动领取脚本操作手册
 
> **核心逻辑**：通过 `curl.txt` 模拟浏览器身份，自动化执行“扫描 -> 对比 -> 下单”流程。

---

## 🛠 准备工作 (Preparation)

1.  **身份凭证 (`curl.txt`)**
    * **获取方式**：登录 Fab 官网 -> F12 网络 (Network) -> 找一个 API 请求 -> 右键 `Copy as cURL (bash)`。
    * **存储**：将内容粘贴至 `curl.txt`。
    * **注意**：此文件等同于您的账号密码，**严禁泄露**。

2.  **环境要求**
    * Python 3.x
    * 安装依赖：`pip install requests` (建议使用 requests 库处理 cURL 中的 headers)。

---

## 🚀 脚本执行流程 (Workflow)

### 1. 资产扫描阶段：`get.py`
* **功能**：获取 Fab 所有免费资产，生成 `fab.txt`。
* **断点续传**：脚本会自动读取/更新 `lastCursor.txt`。
* **操作**：直接运行。若想从头开始，请删除 `lastCursor.txt`。

### 2. 数据对比阶段：`compare.py`
* **功能**：对比本地库，筛选出“未拥有的资产”。
* **产出**：
    * `acquired.txt` (已买资产 ID)
    * `unacquired.txt` (待领资产 ID)

### 3. 下单准备阶段：`getOfferId.py`
* **功能**：请求下单接口所需的 `offerId`。
* **产出**：`offerIds.txt` (下单任务列表)。

### 4. 自动化下单阶段：`claim.py` (原流程第5步)
* **功能**：遍历 `offerIds.txt` 执行 0 元购买动作。
* **注意**：此步建议设置随机 `sleep` (1-3秒)，防止被风控。

### 5. 一键串联：`start.sh`
* **功能**：按照上述顺序串行执行。 建议手动一步步执行， 以免有错误不能及时发现浪费资源

---

## ⚠️ 开发者注意事项 (Technical Notes)

* **路径依赖**：`.py` 脚本必须与 `curl.txt`、`lastCursor.txt` 在同一层级目录下。
* **频率限制**：如提示 `429 Too Many Requests`，请调大代码中的 `time.sleep()` 间隔。
* **失效处理**：如果脚本突然报错 `401` 或 `403`，说明 `curl.txt` 中的 Cookie 已过期，需重新获取。

## 鸣谢
感谢gemini
如果您没有pyhton3环境，可直接让AI 原样翻译一下即可。 比较 快捷的可转php golang js(浏览器直接调试也很方便) nodejs等 劳驾自行处理 
