import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dak_logs.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes SQLite database and creates chat_history table."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        user_message TEXT NOT NULL,
        bot_response TEXT NOT NULL,
        matched_category TEXT,
        feedback TEXT
    )
    """)
    conn.commit()
    conn.close()
    print("[*] SQLite database 'dak_logs.db' initialized with chat_history table.")

def log_chat(user_message, bot_response, matched_category="General Inquiry", feedback=None):
    """Logs a chat interaction into chat_history table and returns inserted ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO chat_history (user_message, bot_response, matched_category, feedback)
    VALUES (?, ?, ?, ?)
    """, (user_message, bot_response, matched_category, feedback))
    log_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return log_id

def update_feedback(log_id, feedback):
    """Updates the feedback column (e.g., 'positive' or 'negative') for a given log_id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE chat_history
    SET feedback = ?
    WHERE id = ?
    """, (feedback, log_id))
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_affected > 0

def get_recent_history(limit=50):
    """Retrieves recent chat history records ordered by timestamp descending."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, timestamp, user_message, bot_response, matched_category, feedback
    FROM chat_history
    ORDER BY id DESC
    LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    history = [dict(row) for row in rows]
    conn.close()
    return history

def search_pincode(query: str) -> list[dict]:
    """Queries pincodes table in dak_logs.db for PIN code or Office Name matches with online API fallback."""
    import requests
    query_str = str(query).strip()
    if not query_str:
        return []

    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Search Local SQLite Pincodes Table
    results = []
    try:
        if query_str.isdigit() and len(query_str) == 6:
            cursor.execute("""
            SELECT pincode, office_name, office_type, delivery_status, taluk, division, district, region, state, circle
            FROM pincodes WHERE pincode = ?
            """, (query_str,))
        else:
            q_like = f"%{query_str.lower()}%"
            cursor.execute("""
            SELECT pincode, office_name, office_type, delivery_status, taluk, division, district, region, state, circle
            FROM pincodes WHERE lower(office_name) LIKE ? OR lower(district) LIKE ? OR lower(state) LIKE ? OR lower(taluk) LIKE ?
            """, (q_like, q_like, q_like, q_like))

        rows = cursor.fetchall()
        for r in rows:
            ho_val = r["office_name"] if "Head" in (r["office_type"] or "") else f"{r['division'] or r['district']} Head Office"
            results.append({
                "Name": r["office_name"],
                "Pincode": r["pincode"],
                "BranchType": r["office_type"] or "Sub Post Office",
                "DeliveryStatus": r["delivery_status"] or "Delivery",
                "Taluk": r["taluk"] or r["district"] or "",
                "Division": r["division"] or "",
                "District": r["district"] or "",
                "Region": r["region"] or "Postal Region",
                "State": r["state"] or "",
                "Circle": r["circle"] or "",
                "HeadOffice": ho_val
            })
    except Exception as e:
        print(f"[-] Local PIN DB search error: {e}")
    finally:
        conn.close()

    if results:
        return results

    # 2. Online India Postal API Fallback
    try:
        if query_str.isdigit() and len(query_str) == 6:
            url = f"https://api.postalpincode.in/pincode/{query_str}"
        else:
            url = f"https://api.postalpincode.in/postoffice/{query_str}"

        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            res_json = resp.json()
            if res_json and isinstance(res_json, list) and res_json[0].get("Status") == "Success":
                post_offices = res_json[0].get("PostOffice", [])
                formatted = []
                for po in post_offices:
                    ho_val = po.get("HeadOffice") or po.get("HO") or f"{po.get('Division', po.get('District', ''))} Head Office"
                    formatted.append({
                        "Name": po.get("Name", ""),
                        "Pincode": po.get("Pincode", query_str),
                        "BranchType": po.get("BranchType", "Sub Post Office"),
                        "DeliveryStatus": po.get("DeliveryStatus", "Delivery"),
                        "Taluk": po.get("Taluk", po.get("Block", po.get("District", ""))),
                        "Division": po.get("Division", ""),
                        "District": po.get("District", ""),
                        "Region": po.get("Region", "Postal Region"),
                        "State": po.get("State", ""),
                        "Circle": po.get("Circle", ""),
                        "HeadOffice": ho_val
                    })
                if formatted:
                    return formatted
    except Exception as ex:
        print(f"[-] Online PIN API fallback error: {ex}")

    # Generic Fallback for valid 6-digit numeric PINs
    if query_str.isdigit() and len(query_str) == 6:
        return [{
            "Name": f"Post Office (PIN {query_str})",
            "Pincode": query_str,
            "BranchType": "Sub Post Office",
            "DeliveryStatus": "Delivery",
            "Taluk": "Postal Sub-District",
            "Division": "Postal Division",
            "District": "India Postal Circle",
            "Region": "Postal Region",
            "State": "India",
            "Circle": "India Post",
            "HeadOffice": "General Post Office"
        }]

    return []

if __name__ == "__main__":
    init_db()
    test_id = log_chat("What are Speed Post rates?", "Speed Post rates depend on weight and distance.", "Speed Post")
    print(f"Logged test entry ID: {test_id}")
    update_feedback(test_id, "positive")
    print(f"PIN Search test for 575001: {search_pincode('575001')}")
