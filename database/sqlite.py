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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS crypto_invoices (
            invoice_id TEXT PRIMARY KEY,
            user_id INTEGER,
            package_name TEXT,
            temp_address TEXT,
            status TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # ─── Multi-Tenant Clone Tables ─────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cloned_bots (
            bot_id INTEGER PRIMARY KEY,
            owner_user_id INTEGER NOT NULL,
            bot_username TEXT,
            bot_token TEXT UNIQUE NOT NULL,
            clone_status TEXT DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clone_quotas (
            user_id INTEGER PRIMARY KEY,
            total_slots INTEGER DEFAULT 1,
            used_slots INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS connected_groups (
            group_id INTEGER PRIMARY KEY,
            group_title TEXT,
            bot_id INTEGER NOT NULL,
            owner_user_id INTEGER NOT NULL,
            connected_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_packages (
            package_id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            duration_days INTEGER NOT NULL,
            stars_price INTEGER NOT NULL,
            usdt_price REAL NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS creator_balances (
            owner_user_id INTEGER PRIMARY KEY,
            balance_usdt REAL DEFAULT 0.0,
            total_earned_usdt REAL DEFAULT 0.0,
            withdrawal_address TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS withdrawals (
            withdrawal_id TEXT PRIMARY KEY,
            owner_user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            to_address TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            tx_hash TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clone_subscriptions (
            user_id INTEGER,
            group_id INTEGER,
            bot_id INTEGER,
            expiry_date DATETIME,
            PRIMARY KEY (user_id, group_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clone_crypto_invoices (
            invoice_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            bot_id INTEGER NOT NULL,
            group_id INTEGER,
            package_name TEXT,
            usdt_amount REAL,
            temp_address TEXT,
            status TEXT DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_languages (
            user_id INTEGER PRIMARY KEY,
            lang_code TEXT DEFAULT 'en'
        )
    ''')
    # Safe migration: add lang_code to connected_groups if it doesn't exist
    try:
        cursor.execute("ALTER TABLE connected_groups ADD COLUMN lang_code TEXT DEFAULT 'en'")
    except Exception:
        pass  # Column already exists
    conn.commit()
    conn.close()

def get_user_lang(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT lang_code FROM user_languages WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None  # None = not set yet

def set_user_lang(user_id: int, lang_code: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user_languages (user_id, lang_code) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET lang_code = excluded.lang_code
    ''', (user_id, lang_code))
    conn.commit()
    conn.close()

def get_group_lang(group_id: int) -> str:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT lang_code FROM connected_groups WHERE group_id = ?', (group_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 'en'

def set_group_lang(group_id: int, lang_code: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE connected_groups SET lang_code = ? WHERE group_id = ?", (lang_code, group_id))
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

def add_crypto_invoice(invoice_id: str, user_id: int, package_name: str, temp_address: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO crypto_invoices (invoice_id, user_id, package_name, temp_address, status)
        VALUES (?, ?, ?, ?, 'pending')
    ''', (invoice_id, user_id, package_name, temp_address))
    conn.commit()
    conn.close()

def get_pending_crypto_invoices(user_id: int, package_name: str = None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if package_name:
        cursor.execute('SELECT invoice_id, package_name, temp_address FROM crypto_invoices WHERE user_id = ? AND status = ? AND package_name = ?', (user_id, 'pending', package_name))
    else:
        cursor.execute('SELECT invoice_id, package_name, temp_address FROM crypto_invoices WHERE user_id = ? AND status = ?', (user_id, 'pending'))
    rows = cursor.fetchall()
    conn.close()
    return [{"invoice_id": row[0], "package_name": row[1], "temp_address": row[2]} for row in rows]

def update_crypto_invoice_status(invoice_id: str, status: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE crypto_invoices SET status = ? WHERE invoice_id = ?', (status, invoice_id))
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════
# Multi-Tenant Clone Feature — Helper Functions
# ═══════════════════════════════════════════════════════════════

import datetime

# ─── Cloned Bots ──────────────────────────────────────────────

def add_cloned_bot(bot_id: int, owner_user_id: int, bot_username: str, bot_token: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO cloned_bots (bot_id, owner_user_id, bot_username, bot_token)
        VALUES (?, ?, ?, ?)
    ''', (bot_id, owner_user_id, bot_username, bot_token))
    conn.commit()
    conn.close()

def get_all_active_cloned_bots():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT bot_id, owner_user_id, bot_username, bot_token FROM cloned_bots WHERE clone_status = ?', ('active',))
    rows = cursor.fetchall()
    conn.close()
    return [{"bot_id": r[0], "owner_user_id": r[1], "bot_username": r[2], "bot_token": r[3]} for r in rows]

def get_cloned_bot_by_id(bot_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT bot_id, owner_user_id, bot_username, bot_token, clone_status FROM cloned_bots WHERE bot_id = ?', (bot_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"bot_id": row[0], "owner_user_id": row[1], "bot_username": row[2], "bot_token": row[3], "clone_status": row[4]}
    return None

def get_cloned_bots_by_owner(owner_user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT bot_id, bot_username, clone_status FROM cloned_bots WHERE owner_user_id = ?', (owner_user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"bot_id": r[0], "bot_username": r[1], "clone_status": r[2]} for r in rows]

def remove_cloned_bot(bot_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE cloned_bots SET clone_status = ? WHERE bot_id = ?', ('stopped', bot_id))
    conn.commit()
    conn.close()

# ─── Clone Quotas ─────────────────────────────────────────────

def get_clone_quota(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT total_slots, used_slots FROM clone_quotas WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"total_slots": row[0], "used_slots": row[1]}
    return {"total_slots": 1, "used_slots": 0}

def increment_used_slots(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM clone_quotas WHERE user_id = ?', (user_id,))
    if cursor.fetchone():
        cursor.execute('UPDATE clone_quotas SET used_slots = used_slots + 1 WHERE user_id = ?', (user_id,))
    else:
        cursor.execute('INSERT INTO clone_quotas (user_id, total_slots, used_slots) VALUES (?, 1, 1)', (user_id,))
    conn.commit()
    conn.close()

def add_clone_slots(user_id: int, slots: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM clone_quotas WHERE user_id = ?', (user_id,))
    if cursor.fetchone():
        cursor.execute('UPDATE clone_quotas SET total_slots = total_slots + ? WHERE user_id = ?', (slots, user_id))
    else:
        cursor.execute('INSERT INTO clone_quotas (user_id, total_slots, used_slots) VALUES (?, ?, 0)', (user_id, 1 + slots))
    conn.commit()
    conn.close()

# ─── Connected Groups ────────────────────────────────────────

def add_connected_group(group_id: int, group_title: str, bot_id: int, owner_user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO connected_groups (group_id, group_title, bot_id, owner_user_id)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(group_id) DO UPDATE SET group_title = excluded.group_title, bot_id = excluded.bot_id, owner_user_id = excluded.owner_user_id
    ''', (group_id, group_title, bot_id, owner_user_id))
    conn.commit()
    conn.close()

def get_connected_groups(bot_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT group_id, group_title FROM connected_groups WHERE bot_id = ?', (bot_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"group_id": r[0], "group_title": r[1]} for r in rows]

def get_connected_group(group_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT group_id, group_title, bot_id, owner_user_id FROM connected_groups WHERE group_id = ?', (group_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"group_id": row[0], "group_title": row[1], "bot_id": row[2], "owner_user_id": row[3]}
    return None

def remove_connected_group(group_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM connected_groups WHERE group_id = ?', (group_id,))
    conn.commit()
    conn.close()

# ─── Group Packages ──────────────────────────────────────────

def add_group_package(group_id: int, duration_days: int, stars_price: int, usdt_price: float):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO group_packages (group_id, duration_days, stars_price, usdt_price)
        VALUES (?, ?, ?, ?)
    ''', (group_id, duration_days, stars_price, usdt_price))
    conn.commit()
    conn.close()

def get_group_packages(group_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT package_id, duration_days, stars_price, usdt_price FROM group_packages WHERE group_id = ? ORDER BY duration_days ASC', (group_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"package_id": r[0], "duration_days": r[1], "stars_price": r[2], "usdt_price": r[3]} for r in rows]

def get_group_package_by_id(package_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT package_id, group_id, duration_days, stars_price, usdt_price FROM group_packages WHERE package_id = ?', (package_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"package_id": row[0], "group_id": row[1], "duration_days": row[2], "stars_price": row[3], "usdt_price": row[4]}
    return None

def update_group_package(package_id: int, duration_days: int, stars_price: int, usdt_price: float):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE group_packages SET duration_days = ?, stars_price = ?, usdt_price = ? WHERE package_id = ?', (duration_days, stars_price, usdt_price, package_id))
    conn.commit()
    conn.close()

def delete_group_package(package_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM group_packages WHERE package_id = ?', (package_id,))
    conn.commit()
    conn.close()

# ─── Creator Balances ────────────────────────────────────────

def get_creator_balance(owner_user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT balance_usdt, total_earned_usdt, withdrawal_address FROM creator_balances WHERE owner_user_id = ?', (owner_user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"balance_usdt": row[0], "total_earned_usdt": row[1], "withdrawal_address": row[2]}
    return {"balance_usdt": 0.0, "total_earned_usdt": 0.0, "withdrawal_address": None}

def credit_creator_balance(owner_user_id: int, amount: float):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT owner_user_id FROM creator_balances WHERE owner_user_id = ?', (owner_user_id,))
    if cursor.fetchone():
        cursor.execute('UPDATE creator_balances SET balance_usdt = balance_usdt + ?, total_earned_usdt = total_earned_usdt + ? WHERE owner_user_id = ?', (amount, amount, owner_user_id))
    else:
        cursor.execute('INSERT INTO creator_balances (owner_user_id, balance_usdt, total_earned_usdt) VALUES (?, ?, ?)', (owner_user_id, amount, amount))
    conn.commit()
    conn.close()

def debit_creator_balance(owner_user_id: int, amount: float):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE creator_balances SET balance_usdt = balance_usdt - ? WHERE owner_user_id = ?', (amount, owner_user_id))
    conn.commit()
    conn.close()

def set_withdrawal_address(owner_user_id: int, address: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT owner_user_id FROM creator_balances WHERE owner_user_id = ?', (owner_user_id,))
    if cursor.fetchone():
        cursor.execute('UPDATE creator_balances SET withdrawal_address = ? WHERE owner_user_id = ?', (address, owner_user_id))
    else:
        cursor.execute('INSERT INTO creator_balances (owner_user_id, withdrawal_address) VALUES (?, ?)', (owner_user_id, address))
    conn.commit()
    conn.close()

# ─── Withdrawals ─────────────────────────────────────────────

def create_withdrawal(withdrawal_id: str, owner_user_id: int, amount: float, to_address: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO withdrawals (withdrawal_id, owner_user_id, amount, to_address)
        VALUES (?, ?, ?, ?)
    ''', (withdrawal_id, owner_user_id, amount, to_address))
    conn.commit()
    conn.close()

def complete_withdrawal(withdrawal_id: str, tx_hash: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cursor.execute('UPDATE withdrawals SET status = ?, tx_hash = ?, completed_at = ? WHERE withdrawal_id = ?', ('completed', tx_hash, now, withdrawal_id))
    conn.commit()
    conn.close()

def fail_withdrawal(withdrawal_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE withdrawals SET status = ? WHERE withdrawal_id = ?', ('failed', withdrawal_id))
    conn.commit()
    conn.close()

# ─── Clone Subscriptions ─────────────────────────────────────

def get_clone_subscription(user_id: int, group_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT expiry_date FROM clone_subscriptions WHERE user_id = ? AND group_id = ?', (user_id, group_id))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def extend_clone_subscription(user_id: int, group_id: int, bot_id: int, duration_days: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT expiry_date FROM clone_subscriptions WHERE user_id = ? AND group_id = ?', (user_id, group_id))
    row = cursor.fetchone()
    
    now = datetime.datetime.now(datetime.timezone.utc)
    
    if row:
        current_expiry = datetime.datetime.fromisoformat(row[0])
        if current_expiry < now:
            new_expiry = now + datetime.timedelta(days=duration_days)
        else:
            new_expiry = current_expiry + datetime.timedelta(days=duration_days)
        cursor.execute('UPDATE clone_subscriptions SET expiry_date = ? WHERE user_id = ? AND group_id = ?', (new_expiry.isoformat(), user_id, group_id))
    else:
        new_expiry = now + datetime.timedelta(days=duration_days)
        cursor.execute('INSERT INTO clone_subscriptions (user_id, group_id, bot_id, expiry_date) VALUES (?, ?, ?, ?)', (user_id, group_id, bot_id, new_expiry.isoformat()))
    
    conn.commit()
    conn.close()

# ─── Clone Crypto Invoices ───────────────────────────────────

def add_clone_crypto_invoice(invoice_id: str, user_id: int, bot_id: int, group_id: int, package_name: str, usdt_amount: float, temp_address: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO clone_crypto_invoices (invoice_id, user_id, bot_id, group_id, package_name, usdt_amount, temp_address, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
    ''', (invoice_id, user_id, bot_id, group_id, package_name, usdt_amount, temp_address))
    conn.commit()
    conn.close()

def get_pending_clone_invoice(user_id: int, bot_id: int = None):
    """Get the single pending clone invoice for a user (1-invoice limit)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if bot_id:
        cursor.execute('SELECT invoice_id, group_id, package_name, usdt_amount, temp_address FROM clone_crypto_invoices WHERE user_id = ? AND bot_id = ? AND status = ?', (user_id, bot_id, 'pending'))
    else:
        cursor.execute('SELECT invoice_id, group_id, package_name, usdt_amount, temp_address FROM clone_crypto_invoices WHERE user_id = ? AND status = ?', (user_id, 'pending'))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"invoice_id": row[0], "group_id": row[1], "package_name": row[2], "usdt_amount": row[3], "temp_address": row[4]}
    return None

def update_clone_invoice_status(invoice_id: str, status: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE clone_crypto_invoices SET status = ? WHERE invoice_id = ?', (status, invoice_id))
    conn.commit()
    conn.close()

def get_stale_crypto_invoices(hours: int = 12):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT invoice_id FROM crypto_invoices WHERE status = ? AND timestamp <= datetime(''now'', ?)', ('pending', f'-{hours} hours'))
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def get_stale_clone_crypto_invoices(hours: int = 12):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT invoice_id FROM clone_crypto_invoices WHERE status = ? AND created_at <= datetime(''now'', ?)', ('pending', f'-{hours} hours'))
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def update_cloned_bot_token(old_bot_id: int, new_bot_token: str, new_bot_id: int, new_username: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # Verify the old bot exists
        cursor.execute('SELECT bot_id FROM cloned_bots WHERE bot_id = ?', (old_bot_id,))
        if not cursor.fetchone():
            return False
            
        # Update cloned_bots table
        # Since bot_id is the primary key, SQLite allows updating it.
        cursor.execute('''
            UPDATE cloned_bots 
            SET bot_id = ?, bot_token = ?, bot_username = ?
            WHERE bot_id = ?
        ''', (new_bot_id, new_bot_token, new_username, old_bot_id))
        
        # Update references in other tables
        cursor.execute('UPDATE connected_groups SET bot_id = ? WHERE bot_id = ?', (new_bot_id, old_bot_id))
        cursor.execute('UPDATE clone_subscriptions SET bot_id = ? WHERE bot_id = ?', (new_bot_id, old_bot_id))
        cursor.execute('UPDATE clone_crypto_invoices SET bot_id = ? WHERE bot_id = ?', (new_bot_id, old_bot_id))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating cloned bot token: {e}")
        conn.rollback()
        return False
        conn.close()

# ─── System Stats ────────────────────────────────────────

def get_system_stats() -> dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Clone bots count
        cursor.execute("SELECT COUNT(*) FROM cloned_bots")
        clone_bots = cursor.fetchone()[0]
        
        # Connected groups count
        cursor.execute("SELECT COUNT(*) FROM connected_groups")
        groups = cursor.fetchone()[0]
        
        # Total users (estimated by distinct IDs across tables)
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) FROM (
                SELECT user_id FROM user_languages
                UNION SELECT user_id FROM payments
                UNION SELECT user_id FROM clone_subscriptions
                UNION SELECT owner_user_id FROM cloned_bots
            )
        """)
        users = cursor.fetchone()[0]
        
        # Total payments (XTR + completed crypto)
        cursor.execute("SELECT COUNT(*) FROM payments")
        xtr_payments = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM crypto_invoices WHERE status='completed'")
        crypto_payments = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM clone_crypto_invoices WHERE status='completed'")
        clone_crypto_payments = cursor.fetchone()[0]
        
        total_payments = xtr_payments + crypto_payments + clone_crypto_payments
        
        return {
            "clone_bots": clone_bots,
            "groups": groups,
            "users": users,
            "payments": total_payments
        }
    except Exception as e:
        print(f"Error fetching system stats: {e}")
        return {"clone_bots": 0, "groups": 0, "users": 0, "payments": 0}
    finally:
        conn.close()
