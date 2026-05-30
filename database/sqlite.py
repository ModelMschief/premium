import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "local_payments.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_id TEXT UNIQUE,
            user_id INTEGER,
            package_name TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def log_local_payment(user_id: int, payment_id: str, package_name: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO payments (payment_id, user_id, package_name)
        VALUES (?, ?, ?)
    ''', (payment_id, user_id, package_name))
    conn.commit()
    conn.close()

# Initialize DB when module is imported
init_db()
