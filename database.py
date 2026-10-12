import sqlite3
import os
from datetime import datetime

DB_PATH = "shop.db"

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()

    # Товары
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price INTEGER NOT NULL,
            duration TEXT NOT NULL,
            category TEXT DEFAULT 'Основное',
            active INTEGER DEFAULT 1
        )
    """)

    # Ключи/лицензии для товаров
    c.execute("""
        CREATE TABLE IF NOT EXISTS keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            key_value TEXT NOT NULL,
            used INTEGER DEFAULT 0,
            used_by INTEGER,
            used_at TEXT,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    # Заказы
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            product_id INTEGER NOT NULL,
            product_name TEXT,
            amount INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now')),
            confirmed_at TEXT,
            key_given TEXT
        )
    """)

    # Пользователи
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            registered_at TEXT DEFAULT (datetime('now')),
            total_orders INTEGER DEFAULT 0
        )
    """)

    # Заполнить примерными товарами если пусто
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        products = [
            ("ULTIMA iOS", "Мощный чит для iOS. Все функции в одном софте, без бана, быстрая установка.", 130, "1 день", "iOS"),
            ("ULTIMA iOS", "Мощный чит для iOS. Все функции в одном софте, без бана, быстрая установка.", 600, "7 дней", "iOS"),
            ("ULTIMA iOS", "Мощный чит для iOS. Все функции в одном софте, без бана, быстрая установка.", 1800, "30 дней", "iOS"),
            ("ULTIMA Android", "Версия для Android с теми же функциями.", 100, "1 день", "Android"),
            ("ULTIMA Android", "Версия для Android с теми же функциями.", 500, "7 дней", "Android"),
            ("ULTIMA PC", "Полный функционал для PC/Windows.", 200, "1 день", "PC"),
            ("ULTIMA PC", "Полный функционал для PC/Windows.", 900, "7 дней", "PC"),
        ]
        c.executemany(
            "INSERT INTO products (name, description, price, duration, category) VALUES (?,?,?,?,?)",
            products
        )

    conn.commit()
    conn.close()

# ── Products ──────────────────────────────────────────────
def get_categories():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT DISTINCT category FROM products WHERE active=1")
    cats = [row[0] for row in c.fetchall()]
    conn.close()
    return cats

def get_products_by_category(category):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE category=? AND active=1", (category,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_product(product_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE id=?", (product_id,))
    row = c.fetchone()
    conn.close()
    return row

def get_all_products():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM products ORDER BY category, price")
    rows = c.fetchall()
    conn.close()
    return rows

def add_product(name, description, price, duration, category):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO products (name, description, price, duration, category) VALUES (?,?,?,?,?)",
        (name, description, price, duration, category)
    )
    pid = c.lastrowid
    conn.commit()
    conn.close()
    return pid

def toggle_product(product_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE products SET active = 1 - active WHERE id=?", (product_id,))
    conn.commit()
    conn.close()

# ── Keys ──────────────────────────────────────────────────
def add_key(product_id, key_value):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO keys (product_id, key_value) VALUES (?,?)", (product_id, key_value))
    conn.commit()
    conn.close()

def get_free_key(product_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, key_value FROM keys WHERE product_id=? AND used=0 LIMIT 1", (product_id,))
    row = c.fetchone()
    conn.close()
    return row

def use_key(key_id, user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "UPDATE keys SET used=1, used_by=?, used_at=datetime('now') WHERE id=?",
        (user_id, key_id)
    )
    conn.commit()
    conn.close()

def count_free_keys(product_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM keys WHERE product_id=? AND used=0", (product_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

# ── Orders ────────────────────────────────────────────────
def create_order(user_id, username, product_id, product_name, amount):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO orders (user_id, username, product_id, product_name, amount) VALUES (?,?,?,?,?)",
        (user_id, username, product_id, product_name, amount)
    )
    oid = c.lastrowid
    conn.commit()
    conn.close()
    return oid

def get_order(order_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE id=?", (order_id,))
    row = c.fetchone()
    conn.close()
    return row

def confirm_order(order_id, key_given):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "UPDATE orders SET status='confirmed', confirmed_at=datetime('now'), key_given=? WHERE id=?",
        (key_given, order_id)
    )
    conn.commit()
    conn.close()

def reject_order(order_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE orders SET status='rejected' WHERE id=?", (order_id,))
    conn.commit()
    conn.close()

def get_pending_orders():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE status='pending' ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def get_user_orders(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC LIMIT 10", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

# ── Users ─────────────────────────────────────────────────
def register_user(user_id, username, full_name):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO users (id, username, full_name) VALUES (?,?,?)",
        (user_id, username, full_name)
    )
    conn.commit()
    conn.close()

def get_stats():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM orders WHERE status='confirmed'")
    confirmed = c.fetchone()[0]
    c.execute("SELECT SUM(amount) FROM orders WHERE status='confirmed'")
    revenue = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM orders WHERE status='pending'")
    pending = c.fetchone()[0]
    conn.close()
    return users, confirmed, revenue, pending
