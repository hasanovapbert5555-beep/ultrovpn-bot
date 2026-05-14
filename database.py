# database.py
import aiosqlite
import json
from typing import Optional, Dict, Any, List
import config
import logging

logger = logging.getLogger(__name__)

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    language TEXT DEFAULT 'ru',
    key_password TEXT,
    key_expiry INTEGER,
    balance REAL DEFAULT 0,
    referrer_id INTEGER,
    referral_code TEXT UNIQUE,
    total_spent REAL DEFAULT 0,
    vmess_id TEXT,
    proxy_pass TEXT,
    created_at INTEGER DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    tariff TEXT,
    days INTEGER,
    price_usd REAL,
    price_rub REAL,
    currency TEXT,
    status TEXT,
    payment_uuid TEXT UNIQUE,
    created_at INTEGER DEFAULT (strftime('%s','now')),
    paid_at INTEGER,
    raw_payment TEXT
);

CREATE TABLE IF NOT EXISTS referral_earnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    from_user_id INTEGER,
    amount REAL,
    level INTEGER,
    paid INTEGER DEFAULT 0,
    created_at INTEGER DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS promocodes (
    code TEXT PRIMARY KEY,
    discount_type TEXT,
    discount_value REAL,
    max_uses INTEGER,
    used_count INTEGER DEFAULT 0,
    expires_at INTEGER
);

CREATE TABLE IF NOT EXISTS broadcasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message TEXT,
    image_file TEXT,
    status TEXT DEFAULT 'pending',
    total_sent INTEGER DEFAULT 0,
    created_at INTEGER DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS withdrawals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    currency TEXT,
    status TEXT DEFAULT 'pending',
    created_at INTEGER DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""

async def init_db(path: str = config.DB_PATH):
    async with aiosqlite.connect(path) as db:
        await db.executescript(SCHEMA)
        await db.commit()

async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        r = await cur.fetchone()
        return dict(r) if r else None

async def ensure_user(user_id: int, username: str = None, full_name: str = None, ref_code: str = None) -> Dict[str, Any]:
    u = await get_user(user_id)
    if u:
        return u
    import uuid
    code = str(uuid.uuid4())[:8]
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            "INSERT INTO users(user_id, username, full_name, referral_code) VALUES (?,?,?,?)",
            (user_id, username, full_name, code)
        )
        if ref_code:
            cur = await db.execute("SELECT user_id FROM users WHERE referral_code = ?", (ref_code,))
            r = await cur.fetchone()
            if r:
                await db.execute("UPDATE users SET referrer_id = ? WHERE user_id = ?", (r[0], user_id))
        await db.commit()
    return await get_user(user_id)

async def set_user_language(user_id: int, lang_code: str):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang_code, user_id))
        await db.commit()

async def credit_user_balance(user_id:int, amount:float):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("UPDATE users SET balance = COALESCE(balance,0) + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

async def create_order(user_id:int, tariff:str, days:int, price_usd:float, price_rub:float, currency:str, payment_uuid:str):
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO orders(user_id, tariff, days, price_usd, price_rub, currency, status, payment_uuid) VALUES (?,?,?,?,?,?,?,?)",
            (user_id, tariff, days, price_usd, price_rub, currency, 'pending', payment_uuid)
        )
        await db.commit()
        return cur.lastrowid

async def get_order_by_uuid(payment_uuid: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM orders WHERE payment_uuid = ?", (payment_uuid,))
        r = await cur.fetchone()
        return dict(r) if r else None

async def set_order_status(payment_uuid: str, status: str):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("UPDATE orders SET status = ? WHERE payment_uuid = ?", (status, payment_uuid))
        await db.commit()

async def set_order_paid_if_pending(payment_uuid: str, payment_info: dict) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM orders WHERE payment_uuid = ?", (payment_uuid,))
        order = await cur.fetchone()
        if not order:
            return None
        order = dict(order)
        if order.get("status") == "paid":
            return {"order": order, "already_paid": True}
        await db.execute(
            "UPDATE orders SET status = ?, paid_at = strftime('%s','now'), raw_payment = ? WHERE payment_uuid = ? AND status != ?",
            ("paid", json.dumps(payment_info, ensure_ascii=False), payment_uuid, "paid")
        )
        await db.commit()
        cur = await db.execute("SELECT * FROM orders WHERE payment_uuid = ?", (payment_uuid,))
        order = await cur.fetchone()
        return {"order": dict(order), "already_paid": False}

async def add_referral_earning(user_id:int, from_user:int, amount:float, level:int):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("INSERT INTO referral_earnings(user_id, from_user_id, amount, level) VALUES (?,?,?,?)",
                         (user_id, from_user, amount, level))
        await db.commit()

async def create_promocode(code: str, discount_type: str, discount_value: float, max_uses: int, expires_at: int):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO promocodes(code, discount_type, discount_value, max_uses, used_count, expires_at) VALUES (?,?,?,?,0,?)",
                         (code, discount_type, discount_value, max_uses, expires_at))
        await db.commit()

async def get_promocode(code: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM promocodes WHERE code = ?", (code,))
        r = await cur.fetchone()
        return dict(r) if r else None

async def use_promocode(code: str):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("UPDATE promocodes SET used_count = used_count + 1 WHERE code = ?", (code,))
        await db.commit()

async def create_broadcast(message: str, image_file: str = None):
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute("INSERT INTO broadcasts(message, image_file) VALUES (?,?)", (message, image_file))
        await db.commit()
        return cur.lastrowid

async def update_broadcast_sent(broadcast_id:int, sent:int):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("UPDATE broadcasts SET total_sent = total_sent + ? WHERE id = ?", (sent, broadcast_id))
        await db.commit()

async def create_withdrawal(user_id:int, amount:float, currency:str = "USDT"):
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute("INSERT INTO withdrawals(user_id, amount, currency) VALUES (?,?,?)", (user_id, amount, currency))
        await db.commit()
        return cur.lastrowid

async def get_withdrawals(status: str = "pending") -> List[Dict[str, Any]]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM withdrawals WHERE status = ?", (status,))
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

async def set_withdrawal_status(withdrawal_id:int, status:str):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("UPDATE withdrawals SET status = ? WHERE id = ?", (status, withdrawal_id))
        await db.commit()

async def update_user_proxy(user_id:int, vmess_id:str = None, proxy_pass:str = None, expiry_ts:int = None):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("UPDATE users SET vmess_id = ?, proxy_pass = ? WHERE user_id = ?", (vmess_id, proxy_pass, user_id))
        await db.commit()

async def get_stats() -> Dict[str, Any]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT COUNT(*) as users FROM users")
        users = (await cur.fetchone())["users"]
        cur = await db.execute("SELECT COUNT(*) as orders FROM orders WHERE status='paid'")
        orders = (await cur.fetchone())["orders"]
        cur = await db.execute("SELECT SUM(price_usd) as revenue FROM orders WHERE status='paid'")
        revenue = (await cur.fetchone())["revenue"] or 0
        return {"users": users, "paid_orders": orders, "revenue_usd": revenue}
