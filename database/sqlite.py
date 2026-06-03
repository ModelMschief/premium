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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_subscriptions (
            user_id INTEGER,
            chat_id INTEGER,
            expiry_date DATETIME,
            PRIMARY KEY (user_id, chat_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_warnings (
            chat_id INTEGER PRIMARY KEY,
            last_warning_message_id INTEGER
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

def get_group_subscription(user_id: int, chat_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT expiry_date FROM group_subscriptions WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def extend_group_subscription(user_id: int, chat_id: int, duration_days: int):
    import datetime
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT expiry_date FROM group_subscriptions WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
    row = cursor.fetchone()
    
    now = datetime.datetime.now(datetime.timezone.utc)
    
    if row:
        # User has an existing subscription
        current_expiry = datetime.datetime.fromisoformat(row[0])
        if current_expiry < now:
            # Expired, start from now
            new_expiry = now + datetime.timedelta(days=duration_days)
        else:
            # Active, extend from current expiry
            new_expiry = current_expiry + datetime.timedelta(days=duration_days)
            
        cursor.execute('''
            UPDATE group_subscriptions 
            SET expiry_date = ? 
            WHERE user_id = ? AND chat_id = ?
        ''', (new_expiry.isoformat(), user_id, chat_id))
    else:
        # New subscription
        new_expiry = now + datetime.timedelta(days=duration_days)
        cursor.execute('''
            INSERT INTO group_subscriptions (user_id, chat_id, expiry_date) 
            VALUES (?, ?, ?)
        ''', (user_id, chat_id, new_expiry.isoformat()))
        
    conn.commit()
    conn.close()

def get_last_warning(chat_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT last_warning_message_id FROM group_warnings WHERE chat_id = ?', (chat_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def set_last_warning(chat_id: int, message_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO group_warnings (chat_id, last_warning_message_id)
        VALUES (?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET last_warning_message_id = excluded.last_warning_message_id
    ''', (chat_id, message_id))
    conn.commit()
    conn.close()

# Initialize DB when module is imported
init_db()
