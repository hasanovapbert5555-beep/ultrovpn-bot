import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Dict

import aiosqlite

DB_PATH = "vpnbot.db"

CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    created_at TEXT,
    subscription_until TEXT,
    devices INTEGER DEFAULT 0,
    referral_code TEXT,
    referrer_id INTEGER,
    invited_count INTEGER DEFAULT 0,
    activated_count INTEGER DEFAULT 0
)
"""

CREATE_TICKETS = """
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER,
    amount REAL,
    currency TEXT,
    created_at TEXT,
    status TEXT
)
"""

CREATE_DEVICES = """
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER,
    device_name TEXT,
    config_hash TEXT,
    created_at TEXT,
    active INTEGER DEFAULT 1
)
"""

class User:
    def __init__(self, telegram_id: int, pool: aiosqlite.Connection):
        self.telegram_id = telegram_id
        self._pool = pool

    async def exists(self) -> bool:
        async with self._pool.execute("SELECT 1 FROM users WHERE telegram_id = ?", (self.telegram_id,)) as cursor:
            row = await cursor.fetchone()
            return row is not None

    async def create(self):
        await self._pool.execute("INSERT OR IGNORE INTO users (telegram_id, created_at, subscription_until) VALUES (?, ?, ?)",
                                 (self.telegram_id, datetime.utcnow().isoformat(), None))
        await self._pool.commit()

    async def set_referrer(self, ref_code: str):
        # сохраняем ссылку на реферала (реф. код)
        await self._pool.execute("UPDATE users SET referral_code = ? WHERE telegram_id = ?", (ref_code, self.telegram_id))
        await self._pool.commit()

    async def get_profile(self) -> str:
        async with self._pool.execute("SELECT telegram_id, subscription_until, devices, referral_code, invited_count, activated_count FROM users WHERE telegram_id = ?", (self.telegram_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                return "Профиль не найден."
            tid, sub, devs, ref, invited, activated = row
            sub_str = sub if sub else "неактивна"
            return f"ID: {tid}\nПодписка до: {sub_str}\nУстройства: {devs}/5\nРеферер: {ref or '—'}\nПриглашено: {invited}\nАктивировано: {activated}"

    async def has_active_subscription(self) -> bool:
        async with self._pool.execute("SELECT subscription_until FROM users WHERE telegram_id = ?", (self.telegram_id,)) as cur:
            row = await cur.fetchone()
            if not row or not row[0]:
                return False
            until = datetime.fromisoformat(row[0])
            return until > datetime.utcnow()

    async def get_active_devices(self) -> int:
        async with self._pool.execute("SELECT devices FROM users WHERE telegram_id = ?", (self.telegram_id,)) as cur:
            row = await cur.fetchone()
            if row:
                return int(row[0])
            return 0

    async def increment_devices(self):
        await self._pool.execute("UPDATE users SET devices = devices + 1 WHERE telegram_id = ?", (self.telegram_id,))
        await self._pool.commit()

    async def add_invite(self, count: int = 1):
        await self._pool.execute("UPDATE users SET invited_count = invited_count + ? WHERE telegram_id = ?", (count, self.telegram_id))
        await self._pool.commit()

    async def activate_subscription(self, days: int):
        async with self._pool.execute("SELECT subscription_until FROM users WHERE telegram_id = ?", (self.telegram_id,)) as cur:
            row = await cur.fetchone()
        current = datetime.utcnow()
        until = current + timedelta(days=days)
        until_str = until.isoformat()
        await self._pool.execute("UPDATE users SET subscription_until = ? WHERE telegram_id = ?", (until_str, self.telegram_id))
        await self._pool.commit()

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_USERS)
        await db.execute(CREATE_TICKETS)
        await db.execute(CREATE_DEVICES)
        await db.commit()

async def get_or_create_user(telegram_id: int) -> User:
    db = await aiosqlite.connect(DB_PATH)
    await db.execute(CREATE_USERS)
    await db.commit()
    user = User(telegram_id, db)
    if not await user.exists():
        await user.create()
    return user
