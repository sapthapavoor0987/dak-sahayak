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

if __name__ == "__main__":
    init_db()
    test_id = log_chat("What are Speed Post rates?", "Speed Post rates depend on weight and distance.", "Speed Post")
    print(f"Logged test entry ID: {test_id}")
    update_feedback(test_id, "positive")
    print(f"History: {get_recent_history(5)}")
