import aiosqlite
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json

DATABASE_PATH = 'vpn_bot.db'

async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Пользователи
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                subscription_end INTEGER,
                created_at INTEGER,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                bonus_days_earned INTEGER DEFAULT 0,
                total_referrals INTEGER DEFAULT 0,
                active_referrals INTEGER DEFAULT 0
            )
        ''')
        
        # Устройства
        await db.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                device_name TEXT,
                uuid TEXT,
                config_hash TEXT,
                created_at INTEGER,
                last_used INTEGER,
                FOREIGN KEY (telegram_id) REFERENCES users (telegram_id),
                UNIQUE(telegram_id, device_name)
            )
        ''')
        
        # Платежи
        await db.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id TEXT UNIQUE,
                telegram_id INTEGER,
                tariff_key TEXT,
                amount_usdt REAL,
                status TEXT,
                created_at INTEGER,
                paid_at INTEGER
            )
        ''')
        
        # Реферальные начисления
        await db.execute('''
            CREATE TABLE IF NOT EXISTS referral_bonuses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER,
                bonus_days INTEGER,
                created_at INTEGER
            )
        ''')
        
        await db.commit()

async def register_user(telegram_id: int, username: str = None, first_name: str = None, last_name: str = None, referred_by: int = None) -> Dict[str, Any]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Проверяем, существует ли пользователь
        async with db.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,)) as cursor:
            user = await cursor.fetchone()
            
        if user:
            return {
                'telegram_id': user[0],
                'subscription_end': user[4],
                'referral_code': user[6],
                'referred_by': user[7]
            }
        
        # Создаем нового пользователя
        referral_code = f"ref_{telegram_id}"
        now = int(datetime.now().timestamp())
        
        await db.execute('''
            INSERT INTO users (telegram_id, username, first_name, last_name, subscription_end, created_at, referral_code, referred_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (telegram_id, username, first_name, last_name, 0, now, referral_code, referred_by))
        
        await db.commit()
        
        return {
            'telegram_id': telegram_id,
            'subscription_end': 0,
            'referral_code': referral_code,
            'referred_by': referred_by
        }

async def get_user(telegram_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    'telegram_id': row[0],
                    'username': row[1],
                    'first_name': row[2],
                    'last_name': row[3],
                    'subscription_end': row[4],
                    'created_at': row[5],
                    'referral_code': row[6],
                    'referred_by': row[7],
                    'bonus_days_earned': row[8],
                    'total_referrals': row[9],
                    'active_referrals': row[10]
                }
    return None

async def update_subscription(telegram_id: int, days_to_add: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute('SELECT subscription_end FROM users WHERE telegram_id = ?', (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            current_end = row[0] if row else 0
        
        now = int(datetime.now().timestamp())
        if current_end < now:
            new_end = now + (days_to_add * 86400)
        else:
            new_end = current_end + (days_to_add * 86400)
        
        await db.execute('UPDATE users SET subscription_end = ? WHERE telegram_id = ?', (new_end, telegram_id))
        await db.commit()
        
        return new_end

async def add_device(telegram_id: int, device_name: str, uuid: str, config_hash: str) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Проверяем количество устройств
        async with db.execute('SELECT COUNT(*) FROM devices WHERE telegram_id = ?', (telegram_id,)) as cursor:
            count = await cursor.fetchone()
            if count[0] >= 5:
                return False
        
        now = int(datetime.now().timestamp())
        await db.execute('''
            INSERT INTO devices (telegram_id, device_name, uuid, config_hash, created_at, last_used)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (telegram_id, device_name, uuid, config_hash, now, now))
        await db.commit()
        return True

async def get_devices(telegram_id: int) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute('SELECT id, device_name, uuid, created_at, last_used FROM devices WHERE telegram_id = ?', (telegram_id,)) as cursor:
            rows = await cursor.fetchall()
            return [{'id': row[0], 'device_name': row[1], 'uuid': row[2], 'created_at': row[3], 'last_used': row[4]} for row in rows]

async def remove_device(device_id: int, telegram_id: int) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('DELETE FROM devices WHERE id = ? AND telegram_id = ?', (device_id, telegram_id))
        await db.commit()
        return True

async def add_payment(invoice_id: str, telegram_id: int, tariff_key: str, amount_usdt: float):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        now = int(datetime.now().timestamp())
        await db.execute('''
            INSERT INTO payments (invoice_id, telegram_id, tariff_key, amount_usdt, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (invoice_id, telegram_id, tariff_key, amount_usdt, 'pending', now))
        await db.commit()

async def confirm_payment(invoice_id: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        now = int(datetime.now().timestamp())
        await db.execute('''
            UPDATE payments SET status = 'paid', paid_at = ? WHERE invoice_id = ?
        ''', (now, invoice_id))
        await db.commit()
        
        # Получаем информацию о платеже
        async with db.execute('SELECT telegram_id, tariff_key FROM payments WHERE invoice_id = ?', (invoice_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0], row[1]
    return None, None

async def get_user_by_referral_code(code: str) -> Optional[int]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute('SELECT telegram_id FROM users WHERE referral_code = ?', (code,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def update_referral_stats(referrer_id: int, referred_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Обновляем счетчики реферера
        await db.execute('''
            UPDATE users 
            SET total_referrals = total_referrals + 1,
                active_referrals = active_referrals + 1
            WHERE telegram_id = ?
        ''', (referrer_id,))
        
        # Добавляем бонусные дни
        await db.execute('''
            UPDATE users 
            SET bonus_days_earned = bonus_days_earned + 7,
                subscription_end = subscription_end + (7 * 86400)
            WHERE telegram_id = ?
        ''', (referrer_id,))
        
        # Записываем бонус
        now = int(datetime.now().timestamp())
        await db.execute('''
            INSERT INTO referral_bonuses (referrer_id, referred_id, bonus_days, created_at)
            VALUES (?, ?, ?, ?)
        ''', (referrer_id, referred_id, 7, now))
        
        await db.commit()

async def get_all_users() -> List[int]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute('SELECT telegram_id FROM users') as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def get_stats() -> Dict[str, Any]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Общее число пользователей
        async with db.execute('SELECT COUNT(*) FROM users') as cursor:
            total_users = (await cursor.fetchone())[0]
        
        # Активные подписки
        now = int(datetime.now().timestamp())
        async with db.execute('SELECT COUNT(*) FROM users WHERE subscription_end > ?', (now,)) as cursor:
            active_subscriptions = (await cursor.fetchone())[0]
        
        # Платежи за месяц
        month_ago = now - (30 * 86400)
        async with db.execute('SELECT SUM(amount_usdt) FROM payments WHERE status = "paid" AND paid_at > ?', (month_ago,)) as cursor:
            monthly_payments = (await cursor.fetchone())[0] or 0
        
        return {
            'total_users': total_users,
            'active_subscriptions': active_subscriptions,
            'monthly_payments_usdt': monthly_payments
        }
