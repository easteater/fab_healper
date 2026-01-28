# Fab Asset Auto-Library & Auto-Purchase (DB Version)
# Operation Manual for Fab Asset Auto-Claim Script
 
> **Core Logic**: Centered around `fab_assets.db`, using `curl.txt` to simulate browser identity, automating the "Scan -> Compare -> Fetch ID -> Claim -> Verify" closed-loop.

---

## 🛠 Preparation

1.  **Identity Credentials (`curl.txt`)**
    * **How to Get**: Login to Fab -> F12 Network (Network) -> Find a `listings-states` request -> Right-click `Copy as cURL (bash)`.
    * **Storage**: Paste the content into `curl.txt`.
    * **Note**: This file contains sensitive Tokens. **Strictly prohibit leakage**. If a 403 error occurs, please re-acquire it.

2.  **Environment Requirements**
    * Python 3.x
    * Dependencies: `pip install curl_cffi` (Mandatory, used to bypass TLS fingerprint detection).

---

## 🚀 Workflow

### 1. Asset Scanning Stage: `get.py`
* **Function**: Fetch all free Fab asset UIDs and write them directly into the `fab_assets` table.
* **Breakpoint Resume**: Automatically reads/updates `lastCursor.txt`.
* **New Logic**: Automatically stops if 10 consecutive existing records are detected (use parameter `0` for a mandatory full scan).

### 2. Data Validation Stage: `compare.py`
* **Function**: Validate unacquired assets in the database via the official API.
* **Output**:
    * **Database Update**: Change the `is_acquired` status of owned assets to 1.
    * **Log**: Generate `unacquired_list.log` (records UIDs currently not owned).

### 3. Claim Preparation Stage: `getOfferId.py`
* **Function**: Request detail pages to obtain the `offerId` required for the order interface.
* **Output**: Updates the `offer_id_1` and `offer_id_2` fields in the database. Supports dual-license asset grabbing.

### 4. Automated Claiming Stage: `claim.py`
* **Function**: Extract records with `offerId` from the DB and execute the $0 purchase action.
* **Note**: **This script does NOT modify the DB status**. Supports two consecutive orders for one UID (corresponding to two OfferIDs). Setting a `DELAY` is recommended to prevent risk control.

### 5. Result Verification Stage: `compare.py` (Run Again)
* **Function**: Run again after claiming to verify and update the database `is_acquired` status to 1 via the official API.

---

## ⚠️ Technical Notes

* **Path Dependency**: `.py` scripts and `db.py` must be in the same directory as `curl.txt`.
* **Data Consistency**: All statuses are based on `compare.py` validation. The claim script `claim.py` is only responsible for execution, not statistics.
* **Rate Limiting**: If `429` or `403` occurs, check if `curl.txt` has expired or increase the `time.sleep()` interval.

## Acknowledgments
Thanks to Gemini.
If you do not have a Python3 environment, you can ask the AI to translate the logic directly. It can be easily converted to PHP, Golang, JS, NodeJS, etc. Please handle this at your own discretion.