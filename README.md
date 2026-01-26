# Fab Asset Auto-Library & Auto-Purchase
# Fab Asset Auto-Claim Script Manual
 
> Core Logic: Use `curl.txt` to simulate browser identity and automate the "Scan -> Compare -> Checkout" workflow.

---

## 🛠 Preparation

1. Identity Credentials (curl.txt)
   - How to obtain: Log in to the Fab official website -> F12 Network tab -> Find any API request -> Right-click and select "Copy as cURL (bash)".
   - Storage: Paste the content into `curl.txt`.
   - Note: This file is equivalent to your account password. DO NOT leak it.

2. Environment Requirements
   - Python 3.x
   - Install dependencies: `pip install requests` (Recommended for handling headers from cURL).

---

## 🚀 Workflow

### 1. Asset Scanning Phase: get.py
- Function: Fetch all free assets from Fab and generate `fab.txt`.
- Breakpoint Resume: The script automatically reads/updates `lastCursor.txt`.
- Operation: Run directly. To restart from scratch, delete `lastCursor.txt`.

### 2. Data Comparison Phase: compare.py
- Function: Compare with local library to filter "unowned assets."
- Output:
    - `acquired.txt` (Purchased asset IDs)
    - `unacquired.txt` (Pending asset IDs)

### 3. Checkout Preparation Phase: getOfferId.py
- Function: Request the `offerId` required for the checkout API.
- Output: `offerIds.txt` (Checkout task list).

### 4. Automated Checkout Phase: claim.py
- Function: Iterate through `offerIds.txt` to execute $0.00 purchase actions.
- Note: It is recommended to set a random `sleep` (1-3 seconds) to prevent triggering "Risk Control" (anti-bot mechanisms).

### 5. One-Click Execution: start.sh
- Function: Execute the above steps in sequence. 
- Advice: It is suggested to execute manually step-by-step initially to ensure errors are caught early and resources are not wasted.

---

## ⚠️ Technical Notes

- Path Dependency: All `.py` scripts must be in the same directory as `curl.txt` and `lastCursor.txt`.
- Rate Limiting: If you see "429 Too Many Requests," increase the `time.sleep()` interval in the code.
- Token Expiration: If the script returns "401" or "403" errors, the Cookie in `curl.txt` has expired and needs to be refreshed.

## Credits
Special thanks to Gemini.
If you do not have a Python 3 environment, you can ask the AI to port the logic to PHP, Golang, JS (browser console debugging), or NodeJS. Please handle the implementation as needed.


