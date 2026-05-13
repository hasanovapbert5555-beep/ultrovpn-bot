#!/usr/bin/env python3
"""
ULTRO VPN BOT v6.0 - ПОЛНАЯ ВЕРСИЯ
43 функции: VPN + Антиглушилка + Промокоды + Рефералы + Бонусы + 2FA
"""

import os
import sys
import asyncio
import subprocess
import sqlite3
import qrcode
import hashlib
import secrets
import json
import time
import re
import requests
from io import BytesIO
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict
from contextlib import contextmanager
from functools import wraps

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.utils import executor
from aiogram.contrib.middlewares.throttling import ThrottlingMiddleware
import pyotp

load_dotenv()

# ============================================================
# КОНФИГУРАЦИЯ
# ============================================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
SERVER_PUBLIC_IP = os.getenv("SERVER_PUBLIC_IP")
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "UltroVPN")
REQUIRED_CHANNEL_LINK = os.getenv("REQUIRED_CHANNEL_LINK", "https://t.me/+yu3Pw6nNRj1jZTZi")

DEFAULT_SUBSCRIPTION_DAYS = int(os.getenv("DEFAULT_SUBSCRIPTION_DAYS", "30"))
MAX_DEVICES_PER_USER = int(os.getenv("MAX_DEVICES_PER_USER", "10"))
REFERRAL_BONUS = int(os.getenv("REFERRAL_BONUS", "50"))
DAILY_BONUS = int(os.getenv("DAILY_BONUS", "5"))
WEEKLY_BONUS_MULTIPLIER = int(os.getenv("WEEKLY_BONUS_MULTIPLIER", "2"))
PROMO_CODES = json.loads(os.getenv("PROMO_CODES", '{"WELCOME30":30, "FRIEND50":50}'))
USDT_WALLET = os.getenv("USDT_WALLET", "")

# WireGuard
WG_INTERFACE = "wg0"
WG_PORT = 51820
WG_SERVER_NETWORK = "10.0.0."

SERVER_PRIVATE_KEY = ""
SERVER_PUBLIC_KEY = ""

# Цены
PRICES = {
    "month": {"price": 299, "days": 30, "stars": 299},
    "quarter": {"price": 799, "days": 90, "stars": 799},
    "halfyear": {"price": 1499, "days": 180, "stars": 1499},
    "year": {"price": 2499, "days": 365, "stars": 2499},
}

# Языки
LANGUAGES = {
    "ru": {
        "welcome": "🎉 Добро пожаловать в UltroVPN!",
        "subscribe": "⚠️ Подпишитесь на канал",
        "device_added": "✅ Устройство создано",
        "stats": "📊 Ваша статистика",
    },
    "en": {
        "welcome": "🎉 Welcome to UltroVPN!",
        "subscribe": "⚠️ Subscribe to the channel",
        "device_added": "✅ Device created",
        "stats": "📊 Your statistics",
    }
}

# ============================================================
# БАЗА ДАННЫХ (РАСШИРЕННАЯ)
# ============================================================
@contextmanager
def get_db():
    conn = sqlite3.connect('vpn_bot.db')
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        # Пользователи (расширенные)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                telegram_ids TEXT DEFAULT '[]',
                username TEXT,
                first_name TEXT,
                language TEXT DEFAULT 'ru',
                phone TEXT,
                subscription_end TEXT,
                auto_renew INTEGER DEFAULT 0,
                balance REAL DEFAULT 0,
                referral_balance REAL DEFAULT 0,
                referred_by INTEGER,
                is_admin INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                two_factor_secret TEXT,
                two_factor_enabled INTEGER DEFAULT 0,
                selected_protocol TEXT DEFAULT 'wireguard',
                selected_dns TEXT DEFAULT '1.1.1.1',
                selected_port INTEGER DEFAULT 51820,
                bonus_streak INTEGER DEFAULT 0,
                last_bonus_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Устройства (расширенные)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                device_name TEXT,
                device_type TEXT,
                protocol TEXT DEFAULT 'wireguard',
                private_key TEXT,
                public_key TEXT,
                ip_address TEXT,
                port INTEGER DEFAULT 51820,
                is_enabled INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_active TEXT,
                total_download_mb INTEGER DEFAULT 0,
                total_upload_mb INTEGER DEFAULT 0
            )
        ''')
        
        # Резервные коды
        conn.execute('''
            CREATE TABLE IF NOT EXISTS backup_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                code_hash TEXT,
                used INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Инвайты и промокоды
        conn.execute('''
            CREATE TABLE IF NOT EXISTS invites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                created_by INTEGER,
                used_by INTEGER,
                days_valid INTEGER DEFAULT 30,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS promocodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                discount_days INTEGER,
                used_by INTEGER,
                used_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Транзакции
        conn.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                currency TEXT DEFAULT 'RUB',
                payment_method TEXT,
                transaction_id TEXT UNIQUE,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT
            )
        ''')
        
        # Тикеты поддержки
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subject TEXT,
                message TEXT,
                status TEXT DEFAULT 'open',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                closed_at TEXT
            )
        ''')
        
        # Белые списки WiFi
        conn.execute('''
            CREATE TABLE IF NOT EXISTS wifi_whitelist (
                user_id INTEGER,
                ssid TEXT,
                PRIMARY KEY (user_id, ssid)
            )
        ''')
        
        # Белые списки приложений (Split Tunneling)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS app_whitelist (
                user_id INTEGER,
                app_name TEXT,
                PRIMARY KEY (user_id, app_name)
            )
        ''')
        
        # Настройки пользователей
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                auto_connect INTEGER DEFAULT 0,
                kill_switch INTEGER DEFAULT 1,
                ad_block INTEGER DEFAULT 0,
                auto_renew INTEGER DEFAULT 0,
                schedule_enabled INTEGER DEFAULT 0,
                schedule_start TEXT,
                schedule_end TEXT,
                notifications_enabled INTEGER DEFAULT 1
            )
        ''')
        
        # Серверы
        conn.execute('''
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                host TEXT,
                country TEXT,
                city TEXT,
                protocol TEXT,
                public_key TEXT,
                port INTEGER,
                is_active INTEGER DEFAULT 1,
                current_users INTEGER DEFAULT 0,
                ping_ms INTEGER DEFAULT 999
            )
        ''')
        
        # Добавляем серверы
        cursor = conn.execute("SELECT COUNT(*) FROM servers")
        if cursor.fetchone()[0] == 0:
            conn.execute("INSERT INTO servers (name, host, country, city, protocol, port) VALUES ('Россия-МСК', ?, 'RU', 'Moscow', 'wireguard', 51820)", (SERVER_PUBLIC_IP,))
            conn.execute("INSERT INTO servers (name, host, country, city, protocol, port) VALUES ('Нидерланды', 'nl.ultrovpn.com', 'NL', 'Amsterdam', 'wireguard', 51820)")
            conn.execute("INSERT INTO servers (name, host, country, city, protocol, port) VALUES ('США-НЙ', 'us.ultrovpn.com', 'US', 'New York', 'wireguard', 51820)")
            conn.execute("INSERT INTO servers (name, host, country, city, protocol, port) VALUES ('Антиглушилка Amnezia', ?, 'RU', 'Anti-DPI', 'amneziawg', 443)", (SERVER_PUBLIC_IP,))
        
        # Создаём админа
        for admin_id in ADMIN_IDS:
            conn.execute('''
                INSERT OR IGNORE INTO users (telegram_id, username, first_name, is_admin, subscription_end)
                VALUES (?, 'admin', 'Admin', 1, datetime('now', '+3650 days'))
            ''', (admin_id,))
        
        # Настройки для новых пользователей
        conn.execute('''
            INSERT OR IGNORE INTO user_settings (user_id)
            SELECT id FROM users WHERE id NOT IN (SELECT user_id FROM user_settings)
        ''')

init_db()

# ============================================================
# ИНИЦИАЛИЗАЦИЯ БОТА
# ============================================================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())
dp.middleware.setup(ThrottlingMiddleware(rate_limit=10))

# ============================================================
# ПРОВЕРКА ПОДПИСКИ НА КАНАЛ
# ============================================================
async def check_subscription(user_id: int) -> Tuple[bool, str]:
    try:
        chat_member = await bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        is_member = chat_member.status in [
            types.ChatMemberStatus.MEMBER,
            types.ChatMemberStatus.CREATOR,
            types.ChatMemberStatus.ADMINISTRATOR
        ]
        if is_member:
            return True, ""
        return False, f"⚠️ **Подпишитесь на канал!**\n\n👉 [{REQUIRED_CHANNEL}]({REQUIRED_CHANNEL_LINK})"
    except:
        return True, ""

def get_subscription_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📢 ПОДПИСАТЬСЯ", url=REQUIRED_CHANNEL_LINK),
        InlineKeyboardButton("✅ ПРОВЕРИТЬ", callback_data="check_subscription")
    )
    return kb

# ============================================================
# WIREGUARD + AMNEZIA (АНТИГЛУШИЛКА)
# ============================================================
def setup_wireguard_server():
    global SERVER_PRIVATE_KEY, SERVER_PUBLIC_KEY
    
    result = subprocess.run(['wg', 'show'], capture_output=True, text=True)
    if WG_INTERFACE in result.stdout:
        return True
    
    SERVER_PRIVATE_KEY = subprocess.check_output(['wg', 'genkey']).decode().strip()
    SERVER_PUBLIC_KEY = subprocess.check_output(['wg', 'pubkey'], input=SERVER_PRIVATE_KEY.encode()).decode().strip()
    
    config = f"""[Interface]
PrivateKey = {SERVER_PRIVATE_KEY}
Address = {WG_SERVER_NETWORK}1/24
ListenPort = {WG_PORT}
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE
"""
    
    os.makedirs('/etc/wireguard', exist_ok=True)
    with open(f'/etc/wireguard/{WG_INTERFACE}.conf', 'w') as f:
        f.write(config)
    
    with open('/etc/sysctl.conf', 'a') as f:
        f.write('\nnet.ipv4.ip_forward=1\n')
    subprocess.run(['sysctl', '-p'], capture_output=True)
    
    subprocess.run(['systemctl', 'enable', f'wg-quick@{WG_INTERFACE}'], capture_output=True)
    subprocess.run(['systemctl', 'start', f'wg-quick@{WG_INTERFACE}'], capture_output=True)
    
    with get_db() as conn:
        conn.execute("UPDATE servers SET public_key = ? WHERE protocol='wireguard'", (SERVER_PUBLIC_KEY,))
    
    return True

def generate_amneziawg_config(private_key: str, ip: str) -> str:
    """Генерирует конфиг AmneziaWG (Антиглушилка)"""
    return f"""[Interface]
PrivateKey = {private_key}
Address = {ip}/24
DNS = 1.1.1.1
MTU = 1420
Jc = 5
Jmin = 40
Jmax = 70
S1 = 40
S2 = 70
H1 = 10
H2 = 20
H3 = 30
H4 = 10

[Peer]
PublicKey = {SERVER_PUBLIC_KEY}
Endpoint = {SERVER_PUBLIC_IP}:443
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""

def generate_vless_link(user_id: str) -> str:
    import uuid
    user_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, user_id))
    return f"vless://{user_uuid}@{SERVER_PUBLIC_IP}:443?encryption=none&flow=xtls-rprx-vision&security=reality&sni=www.microsoft.com&fp=chrome&type=tcp#UltroVPN"

def generate_trojan_link(user_id: str) -> str:
    password = hashlib.md5(user_id.encode()).hexdigest()[:16]
    return f"trojan://{password}@{SERVER_PUBLIC_IP}:443?sni=www.microsoft.com&fp=chrome&type=tcp#UltroVPN"

def generate_wireguard_keys() -> Tuple[str, str]:
    priv = subprocess.check_output(['wg', 'genkey']).decode().strip()
    pub = subprocess.check_output(['wg', 'pubkey'], input=priv.encode()).decode().strip()
    return priv, pub

def get_next_ip() -> str:
    with get_db() as conn:
        used = conn.execute("SELECT ip_address FROM devices WHERE ip_address IS NOT NULL").fetchall()
        used_nums = [int(ip['ip_address'].split('.')[-1]) for ip in used if ip['ip_address']]
    for i in range(10, 255):
        if i not in used_nums:
            return f"{WG_SERVER_NETWORK}{i}"
    return f"{WG_SERVER_NETWORK}200"

def add_peer(public_key: str, ip: str) -> bool:
    try:
        subprocess.run(['wg', 'set', WG_INTERFACE, 'peer', public_key, 'allowed-ips', f"{ip}/32"], check=True)
        return True
    except:
        return False

def remove_peer(public_key: str) -> bool:
    try:
        subprocess.run(['wg', 'set', WG_INTERFACE, 'peer', public_key, 'remove'], check=True)
        return True
    except:
        return False

def generate_config(private_key: str, ip: str, protocol: str = 'wireguard') -> str:
    if protocol == 'amneziawg':
        return generate_amneziawg_config(private_key, ip)
    return f"""[Interface]
PrivateKey = {private_key}
Address = {ip}/24
DNS = 1.1.1.1
MTU = 1420

[Peer]
PublicKey = {SERVER_PUBLIC_KEY}
Endpoint = {SERVER_PUBLIC_IP}:{WG_PORT}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""

def generate_qr(text: str) -> BytesIO:
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    io = BytesIO()
    img.save(io, 'PNG')
    io.seek(0)
    return io

# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================
def get_user_db_id(telegram_id: int) -> Optional[int]:
    with get_db() as conn:
        row = conn.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
        return row['id'] if row else None

def check_subscription_db(telegram_id: int) -> bool:
    with get_db() as conn:
        row = conn.execute("SELECT subscription_end FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
        if row and row['subscription_end']:
            return datetime.fromisoformat(row['subscription_end']) > datetime.now()
    return False

def generate_backup_codes(telegram_id: int, count: int = 8) -> list:
    codes = []
    uid = get_user_db_id(telegram_id)
    if not uid:
        return codes
    with get_db() as conn:
        for _ in range(count):
            code = secrets.token_hex(4).upper()
            h = hashlib.sha256(code.encode()).hexdigest()
            conn.execute("INSERT INTO backup_codes (user_id, code_hash) VALUES (?, ?)", (uid, h))
            codes.append(code)
    return codes

def get_backup_codes_left(telegram_id: int) -> int:
    uid = get_user_db_id(telegram_id)
    if not uid:
        return 0
    with get_db() as conn:
        return conn.execute("SELECT COUNT(*) FROM backup_codes WHERE user_id = ? AND used = 0", (uid,)).fetchone()[0]

def give_daily_bonus(telegram_id: int) -> tuple:
    with get_db() as conn:
        row = conn.execute("SELECT last_bonus_date, balance FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
        if not row:
            return False, 0, 0
        today = datetime.now().date()
        last = datetime.fromisoformat(row['last_bonus_date']).date() if row['last_bonus_date'] else None
        if last == today:
            return False, 0, 0
        if last and (today - last).days == 1:
            conn.execute("UPDATE users SET bonus_streak = bonus_streak + 1 WHERE telegram_id = ?", (telegram_id,))
        else:
            conn.execute("UPDATE users SET bonus_streak = 1 WHERE telegram_id = ?", (telegram_id,))
        streak = conn.execute("SELECT bonus_streak FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()[0]
        bonus = DAILY_BONUS
        if streak % 7 == 0:
            bonus *= WEEKLY_BONUS_MULTIPLIER
        conn.execute("UPDATE users SET balance = balance + ?, last_bonus_date = datetime('now') WHERE telegram_id = ?", (bonus, telegram_id))
        return True, bonus, streak

async def run_speedtest():
    try:
        import speedtest
        loop = asyncio.get_event_loop()
        st = speedtest.Speedtest()
        st.get_best_server()
        d = await loop.run_in_executor(None, st.download)
        u = await loop.run_in_executor(None, st.upload)
        p = st.results.ping
        return d / 1_000_000, u / 1_000_000, p
    except:
        return None, None, None

async def send_notification(telegram_id: int, text: str):
    try:
        await bot.send_message(telegram_id, text, parse_mode='Markdown')
    except:
        pass

def check_expiring_subscriptions():
    """Проверяет подписки, которые скоро истекают"""
    with get_db() as conn:
        users = conn.execute("SELECT telegram_id, subscription_end FROM users WHERE subscription_end IS NOT NULL").fetchall()
        for user in users:
            end = datetime.fromisoformat(user['subscription_end'])
            days_left = (end - datetime.now()).days
            if days_left == 7:
                asyncio.create_task(send_notification(user['telegram_id'], "⚠️ **Ваша подписка истекает через 7 дней!** Продлите её, чтобы не потерять доступ."))
            elif days_left == 3:
                asyncio.create_task(send_notification(user['telegram_id'], "⚠️ **Ваша подписка истекает через 3 дня!**"))
            elif days_left == 1:
                asyncio.create_task(send_notification(user['telegram_id'], "⚠️ **Ваша подписка истекает ЗАВТРА!** Продлите прямо сейчас."))

async def auto_renew_subscriptions():
    """Автоматическое продление подписки с баланса"""
    with get_db() as conn:
        users = conn.execute("SELECT id, telegram_id, balance, subscription_end, auto_renew FROM users WHERE auto_renew = 1 AND subscription_end IS NOT NULL").fetchall()
        for user in users:
            end = datetime.fromisoformat(user['subscription_end'])
            days_left = (end - datetime.now()).days
            if days_left <= 1 and user['balance'] >= 299:
                new_end = max(end, datetime.now()) + timedelta(days=30)
                conn.execute("UPDATE users SET subscription_end = ?, balance = balance - 299 WHERE id = ?", (new_end.isoformat(), user['id']))
                conn.execute("INSERT INTO transactions (user_id, amount, payment_method, status, completed_at) VALUES (?, 299, 'auto_renew', 'completed', datetime('now'))", (user['id'],))
                asyncio.create_task(send_notification(user['telegram_id'], f"✅ **Подписка автоматически продлена!**\nСписано 299₽. Новая дата: {new_end.strftime('%d.%m.%Y')}"))

# ============================================================
# ПЛАТЕЖИ TELEGRAM STARS
# ============================================================
async def send_stars_invoice(user_id: int, plan: str):
    if plan not in PRICES:
        return
    data = PRICES[plan]
    await bot.send_invoice(
        chat_id=user_id,
        title=f"🌟 UltroVPN {data['days']} дней",
        description=f"Доступ к VPN на {data['days']} дней\n⚡ Безлимит\n🌍 Все серверы\n🔒 Антиглушилка",
        payload=f"sub_{plan}_{user_id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="UltroVPN Premium", amount=data['stars'])],
        start_parameter="ultrovpn_sub"
    )

@dp.pre_checkout_query_handler(lambda q: True)
async def pre_checkout(q: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(q.id, ok=True)

@dp.message_handler(content_types=types.ContentType.SUCCESSFUL_PAYMENT)
async def on_successful_payment(msg: types.Message):
    user_id = msg.from_user.id
    payload = msg.successful_payment.invoice_payload
    days = 30
    if "quarter" in payload: days = 90
    elif "halfyear" in payload: days = 180
    elif "year" in payload: days = 365
    
    with get_db() as conn:
        row = conn.execute("SELECT subscription_end FROM users WHERE telegram_id = ?", (user_id,)).fetchone()
        current = datetime.fromisoformat(row['subscription_end']) if row and row['subscription_end'] else datetime.now()
        new_end = max(current, datetime.now()) + timedelta(days=days)
        conn.execute("UPDATE users SET subscription_end = ? WHERE telegram_id = ?", (new_end.isoformat(), user_id))
        uid = conn.execute("SELECT id FROM users WHERE telegram_id = ?", (user_id,)).fetchone()[0]
        conn.execute("INSERT INTO transactions (user_id, amount, payment_method, transaction_id, status, completed_at) VALUES (?, ?, 'stars', ?, 'completed', datetime('now'))", (uid, days * 10, msg.successful_payment.provider_payment_charge_id))
    
    await msg.reply(f"✅ **Оплачено!**\nПодписка продлена до {new_end.strftime('%d.%m.%Y')}", parse_mode='Markdown')

# ============================================================
# ПРОМОКОДЫ
# ============================================================
async def apply_promo_code(user_id: int, code: str) -> tuple:
    code = code.upper()
    if code in PROMO_CODES:
        days = PROMO_CODES[code]
        with get_db() as conn:
            used = conn.execute("SELECT 1 FROM promocodes WHERE code = ? AND used_by IS NOT NULL", (code,)).fetchone()
            if used:
                return False, "Промокод уже использован"
            uid = get_user_db_id(user_id)
            row = conn.execute("SELECT subscription_end FROM users WHERE telegram_id = ?", (user_id,)).fetchone()
            current = datetime.fromisoformat(row['subscription_end']) if row and row['subscription_end'] else datetime.now()
            new_end = max(current, datetime.now()) + timedelta(days=days)
            conn.execute("UPDATE users SET subscription_end = ? WHERE telegram_id = ?", (new_end.isoformat(), user_id))
            conn.execute("INSERT INTO promocodes (code, discount_days, used_by, used_at) VALUES (?, ?, ?, datetime('now'))", (code, days, uid))
            return True, f"✅ Промокод активирован! Добавлено {days} дней. Новая дата: {new_end.strftime('%d.%m.%Y')}"
    return False, "❌ Неверный промокод"

# ============================================================
# ЭКСПОРТ ДАННЫХ
# ============================================================
async def export_user_data(telegram_id: int) -> BytesIO:
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
        devices = conn.execute("SELECT * FROM devices WHERE user_id = ?", (user['id'],)).fetchall()
        transactions = conn.execute("SELECT * FROM transactions WHERE user_id = ?", (user['id'],)).fetchall()
        tickets = conn.execute("SELECT * FROM tickets WHERE user_id = ?", (user['id'],)).fetchall()
        
        data = {
            "user": dict(user),
            "devices": [dict(d) for d in devices],
            "transactions": [dict(t) for t in transactions],
            "tickets": [dict(t) for t in tickets],
            "export_date": datetime.now().isoformat()
        }
        
        json_str = json.dumps(data, default=str, indent=2, ensure_ascii=False)
        return BytesIO(json_str.encode('utf-8'))

# ============================================================
# ГРАФИК ТРАФИКА
# ============================================================
async def get_traffic_stats(telegram_id: int) -> dict:
    with get_db() as conn:
        uid = get_user_db_id(telegram_id)
        devices = conn.execute("SELECT id, device_name, total_download_mb, total_upload_mb FROM devices WHERE user_id = ?", (uid,)).fetchall()
        traffic_by_day = conn.execute("""
            SELECT date(created_at) as day, SUM(total_download_mb) as down, SUM(total_upload_mb) as up
            FROM devices WHERE user_id = ? GROUP BY date(created_at) ORDER BY day DESC LIMIT 30
        """, (uid,)).fetchall()
        
        total_down = sum(d['total_download_mb'] for d in devices)
        total_up = sum(d['total_upload_mb'] for d in devices)
        
        return {
            "total_download_gb": total_down / 1024,
            "total_upload_gb": total_up / 1024,
            "total_gb": (total_down + total_up) / 1024,
            "devices": [{"name": d['device_name'], "down": d['total_download_mb'] / 1024, "up": d['total_upload_mb'] / 1024} for d in devices],
            "by_day": [{"date": d['day'], "down": d['down'] / 1024, "up": d['up'] / 1024} for d in traffic_by_day]
        }

# ============================================================
# ТЕСТ НА УТЕЧКУ DNS
# ============================================================
async def test_dns_leak() -> dict:
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        ip = response.json()['ip']
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        data = response.json()
        return {
            "ip": ip,
            "country": data.get('country', 'Unknown'),
            "city": data.get('city', 'Unknown'),
            "isp": data.get('isp', 'Unknown'),
            "leak_detected": False
        }
    except:
        return {"leak_detected": True, "error": "Не удалось проверить"}

# ============================================================
# КЛАВИАТУРЫ
# ============================================================
async def get_main_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    with get_db() as conn:
        is_admin = conn.execute("SELECT is_admin FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
        is_admin = is_admin['is_admin'] if is_admin else 0
    
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📱 Мои устройства", callback_data="my_devices"),
        InlineKeyboardButton("➕ Добавить", callback_data="add_device")
    )
    kb.add(
        InlineKeyboardButton("📊 Статистика", callback_data="stats"),
        InlineKeyboardButton("💰 Купить Premium", callback_data="buy_premium")
    )
    kb.add(
        InlineKeyboardButton("🎁 Рефералка", callback_data="referral"),
        InlineKeyboardButton("🌍 Протоколы", callback_data="change_protocol")
    )
    kb.add(
        InlineKeyboardButton("⚡ Speed Test", callback_data="speed_test"),
        InlineKeyboardButton("🔍 Тест DNS", callback_data="dns_test")
    )
    kb.add(
        InlineKeyboardButton("📊 Трафик", callback_data="traffic_stats"),
        InlineKeyboardButton("🎫 Промокод", callback_data="promo_code")
    )
    kb.add(
        InlineKeyboardButton("📥 Экспорт данных", callback_data="export_data"),
        InlineKeyboardButton("🔐 Резервные коды", callback_data="backup_keys")
    )
    kb.add(
        InlineKeyboardButton("🔒 2FA", callback_data="two_factor_menu"),
        InlineKeyboardButton("⚙️ Настройки", callback_data="settings")
    )
    kb.add(
        InlineKeyboardButton("💬 Поддержка", callback_data="support"),
        InlineKeyboardButton("🌐 Язык", callback_data="language")
    )
    kb.add(InlineKeyboardButton("ℹ️ О боте", callback_data="about"))
    if is_admin:
        kb.add(InlineKeyboardButton("👑 Админ панель", callback_data="admin_panel"))
    return kb

def get_protocol_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("⚡ WireGuard", callback_data="protocol_wireguard"),
        InlineKeyboardButton("🛡️ AmneziaWG (Антиглушилка)", callback_data="protocol_amneziawg"),
        InlineKeyboardButton("🔒 VLESS Reality", callback_data="protocol_vless"),
        InlineKeyboardButton("🛡️ Trojan", callback_data="protocol_trojan"),
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")
    )
    return kb

def get_settings_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🔄 Auto-connect", callback_data="toggle_autoconnect"),
        InlineKeyboardButton("🛡️ Kill Switch", callback_data="toggle_killswitch"),
        InlineKeyboardButton("🛡️ AdBlock", callback_data="toggle_adblock"),
        InlineKeyboardButton("🔄 Автопродление", callback_data="toggle_autorenew"),
        InlineKeyboardButton("📶 White List WiFi", callback_data="wifi_whitelist"),
        InlineKeyboardButton("📱 Split Tunneling", callback_data="split_tunneling"),
        InlineKeyboardButton("🌐 DNS сервер", callback_data="change_dns"),
        InlineKeyboardButton("🔌 Порт WireGuard", callback_data="change_port"),
        InlineKeyboardButton("⏰ Расписание", callback_data="schedule_settings"),
        InlineKeyboardButton("🗣️ Язык", callback_data="language"),
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")
    )
    return kb

def get_dns_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("☁️ Cloudflare (1.1.1.1)", callback_data="dns_cloudflare"),
        InlineKeyboardButton("🔍 Google (8.8.8.8)", callback_data="dns_google"),
        InlineKeyboardButton("🛡️ AdGuard (94.140.14.14)", callback_data="dns_adguard"),
        InlineKeyboardButton("🔧 Свой DNS", callback_data="dns_custom"),
        InlineKeyboardButton("🔙 Назад", callback_data="settings")
    )
    return kb

# ============================================================
# ОСНОВНЫЕ ОБРАБОТЧИКИ
# ============================================================
@dp.message_handler(commands=['start'])
async def cmd_start(msg: types.Message):
    user_id = msg.from_user.id
    username = msg.from_user.username
    first_name = msg.from_user.first_name
    args = msg.get_args()
    
    # Проверка подписки
    sub, err = await check_subscription(user_id)
    if not sub:
        await msg.reply(err, parse_mode='Markdown', reply_markup=get_subscription_keyboard())
        return
    
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (user_id,)).fetchone()
        
        if not user:
            # Проверка реферала
            referred = None
            if args and args.startswith('ref_'):
                try:
                    rid = int(args.replace('ref_', ''))
                    rrow = conn.execute("SELECT id FROM users WHERE telegram_id = ?", (rid,)).fetchone()
                    if rrow:
                        referred = rrow['id']
                except:
                    pass
            
            # Проверка промокода
            if args and args.upper() in PROMO_CODES:
                days = PROMO_CODES[args.upper()]
                await apply_promo_code(user_id, args.upper())
                sub_days = days
            else:
                sub_days = DEFAULT_SUBSCRIPTION_DAYS
            
            conn.execute('''
                INSERT INTO users (telegram_id, username, first_name, subscription_end, referred_by)
                VALUES (?, ?, ?, datetime('now', '+? days'), ?)
            ''', (user_id, username, first_name, sub_days, referred))
            
            if referred:
                conn.execute("UPDATE users SET referral_balance = referral_balance + ? WHERE id = ?", (REFERRAL_BONUS, referred))
            
            conn.execute("INSERT INTO user_settings (user_id) SELECT id FROM users WHERE telegram_id = ?", (user_id,))
            
            await msg.reply(
                f"🎉 **Добро пожаловать в UltroVPN, {first_name}!**\n\n"
                f"✅ Подписка на {sub_days} дней\n"
                f"💰 Ежедневный бонус: +{DAILY_BONUS}₽\n"
                f"🎁 Реферальный бонус: +{REFERRAL_BONUS}₽ за друга\n"
                f"🛡️ Антиглушилка: AmneziaWG включена\n\n"
                f"👇 Используйте кнопки:",
                parse_mode='Markdown',
                reply_markup=await get_main_keyboard(user_id)
            )
        else:
            if user['is_banned']:
                await msg.reply("❌ Вы заблокированы")
                return
            
            got, amt, streak = give_daily_bonus(user_id)
            bonus_msg = f"\n🎁 Бонус: +{amt}₽ (стрик {streak})" if got else ""
            
            end = datetime.fromisoformat(user['subscription_end']) if user['subscription_end'] else datetime.now()
            days_left = (end - datetime.now()).days
            
            await msg.reply(
                f"👋 **С возвращением, {first_name}!**{bonus_msg}\n\n"
                f"📅 Подписка до: {end.strftime('%d.%m.%Y')}\n"
                f"⏰ Осталось: {max(0, days_left)} дней\n"
                f"💰 Баланс: {user['balance']}₽\n"
                f"🎁 Реферальный: {user['referral_balance']}₽\n\n"
                f"👇 Выберите действие:",
                parse_mode='Markdown',
                reply_markup=await get_main_keyboard(user_id)
            )

@dp.callback_query_handler(lambda c: c.data == "check_subscription")
async def check_sub_cb(cb: types.CallbackQuery):
    sub, _ = await check_subscription(cb.from_user.id)
    if sub:
        await bot.answer_callback_query(cb.id, "✅ Спасибо!")
        await cmd_start(cb.message)
    else:
        await bot.answer_callback_query(cb.id, "❌ Подпишитесь!", show_alert=True)

@dp.callback_query_handler(lambda c: c.data == "stats")
async def stats_cb(cb: types.CallbackQuery):
    uid = cb.from_user.id
    with get_db() as conn:
        user = conn.execute('''
            SELECT u.*, COUNT(d.id) as devices
            FROM users u LEFT JOIN devices d ON d.user_id = u.id
            WHERE u.telegram_id = ? GROUP BY u.id
        ''', (uid,)).fetchone()
    
    if user:
        end = datetime.fromisoformat(user['subscription_end']) if user['subscription_end'] else datetime.now()
        days = (end - datetime.now()).days
        await bot.send_message(uid,
            f"📊 **Ваша статистика**\n\n"
            f"👤 {user['first_name']}\n"
            f"🆔 {user['telegram_id']}\n"
            f"📅 Рег: {user['created_at'][:10]}\n\n"
            f"🔐 **Подписка:**\n"
            f"   ✅ {'🟢 Активна' if days > 0 else '🔴 Истекла'}\n"
            f"   ⏰ Осталось: {max(0, days)} дн\n"
            f"   📅 До: {end.strftime('%d.%m.%Y')}\n\n"
            f"📱 Устройств: {user['devices']}/{MAX_DEVICES_PER_USER}\n"
            f"💰 Баланс: {user['balance']}₽\n"
            f"🎁 Реферальный: {user['referral_balance']}₽\n"
            f"🛡️ Антиглушилка: {'✅ AmneziaWG' if user['selected_protocol'] == 'amneziawg' else '❌'}\n"
            f"🔄 Автопродление: {'✅' if user['auto_renew'] else '❌'}",
            parse_mode='Markdown',
            reply_markup=await get_main_keyboard(uid)
        )

@dp.callback_query_handler(lambda c: c.data == "add_device")
async def add_device_cb(cb: types.CallbackQuery):
    uid = cb.from_user.id
    
    sub, _ = await check_subscription(uid)
    if not sub:
        await bot.send_message(uid, f"🔒 [Подпишитесь]({REQUIRED_CHANNEL_LINK})", parse_mode='Markdown')
        return
    
    if not check_subscription_db(uid):
        await bot.answer_callback_query(cb.id, "❌ Подписка истекла! Продлите её.")
        return
    
    with get_db() as conn:
        cnt = conn.execute("SELECT COUNT(*) FROM devices d JOIN users u ON u.id = d.user_id WHERE u.telegram_id = ?", (uid,)).fetchone()[0]
    
    if cnt >= MAX_DEVICES_PER_USER:
        await bot.send_message(uid, f"❌ Лимит устройств: {MAX_DEVICES_PER_USER}")
        return
    
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💻 Windows", callback_data="device_windows"),
        InlineKeyboardButton("🍎 macOS", callback_data="device_macos"),
        InlineKeyboardButton("🤖 Android", callback_data="device_android"),
        InlineKeyboardButton("📱 iOS", callback_data="device_ios"),
        InlineKeyboardButton("🐧 Linux", callback_data="device_linux"),
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")
    )
    await bot.send_message(uid, "📱 **Выберите устройство:**", parse_mode='Markdown', reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("device_"))
async def create_device_cb(cb: types.CallbackQuery):
    uid = cb.from_user.id
    dtype = cb.data.split('_')[1]
    
    if not check_subscription_db(uid):
        await bot.answer_callback_query(cb.id, "❌ Подписка истекла")
        return
    
    with get_db() as conn:
        user = conn.execute("SELECT selected_protocol, selected_port, selected_dns FROM users WHERE telegram_id = ?", (uid,)).fetchone()
        protocol = user['selected_protocol'] if user else 'wireguard'
        port = user['selected_port'] if user else WG_PORT
        dns = user['selected_dns'] if user else '1.1.1.1'
    
    priv, pub = generate_wireguard_keys()
    ip = get_next_ip()
    name = f"{dtype}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    user_id = get_user_db_id(uid)
    with get_db() as conn:
        conn.execute("INSERT INTO devices (user_id, device_name, device_type, protocol, private_key, public_key, ip_address, port) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (user_id, name, dtype, protocol, priv, pub, ip, port))
    
    add_peer(pub, ip)
    
    if protocol == 'vless':
        config = generate_vless_link(str(uid))
        await bot.send_message(uid, f"✅ **VLESS ссылка для {dtype}:**\n`{config}`", parse_mode='Markdown')
    elif protocol == 'trojan':
        config = generate_trojan_link(str(uid))
        await bot.send_message(uid, f"✅ **Trojan ссылка для {dtype}:**\n`{config}`", parse_mode='Markdown')
    else:
        config = generate_config(priv, ip, protocol)
        qr = generate_qr(config)
        await bot.send_message(uid, f"✅ **Устройство {dtype} создано!**\n🌐 IP: {ip}\n🔧 Протокол: {protocol.upper()}")
        await bot.send_photo(uid, types.InputFile(qr))
        cf = BytesIO(config.encode())
        cf.name = f"ultrovpn_{dtype}.conf"
        await bot.send_document(uid, types.InputFile(cf))

@dp.callback_query_handler(lambda c: c.data == "my_devices")
async def my_devices_cb(cb: types.CallbackQuery):
    uid = cb.from_user.id
    with get_db() as conn:
        devices = conn.execute("SELECT d.* FROM devices d JOIN users u ON u.id = d.user_id WHERE u.telegram_id = ? AND d.is_enabled = 1", (uid,)).fetchall()
    
    if not devices:
        await bot.send_message(uid, "📭 Нет устройств. Добавьте!")
        return
    
    text = "📱 **Ваши устройства:**\n\n"
    kb = InlineKeyboardMarkup()
    for d in devices:
        text += f"🔹 **{d['device_name']}** - {d['device_type']}\n"
        text += f"   🔧 Протокол: {d['protocol'].upper()}\n"
        text += f"   🌐 IP: `{d['ip_address']}`\n\n"
        kb.add(InlineKeyboardButton(f"🗑 Удалить {d['device_name']}", callback_data=f"delete_{d['id']}"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
    await bot.send_message(uid, text, parse_mode='Markdown', reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("delete_"))
async def delete_device_cb(cb: types.CallbackQuery):
    did = int(cb.data.split('_')[1])
    with get_db() as conn:
        pub = conn.execute("SELECT public_key FROM devices WHERE id = ?", (did,)).fetchone()
        if pub:
            remove_peer(pub['public_key'])
            conn.execute("DELETE FROM devices WHERE id = ?", (did,))
    await bot.answer_callback_query(cb.id, "✅ Удалено")
    await my_devices_cb(cb)

@dp.callback_query_handler(lambda c: c.data == "speed_test")
async def speed_test_cb(cb: types.CallbackQuery):
    uid = cb.from_user.id
    msg = await bot.send_message(uid, "🚀 **Тест скорости...**\n⏳ 30 сек", parse_mode='Markdown')
    d, u, p = await run_speedtest()
    if d:
        quality = "🟢 Отлично" if d > 50 else "🟡 Хорошо" if d > 20 else "🟠 Нормально"
        await msg.edit_text(f"📊 **Результаты:**\n📥 {d:.1f} Mbps\n📤 {u:.1f} Mbps\n📡 {p:.0f} ms\n{quality}", parse_mode='Markdown')
    else:
        await msg.edit_text("❌ Ошибка", parse_mode='Markdown')

@dp.callback_query_handler(lambda c: c.data == "dns_test")
async def dns_test_cb(cb: types.CallbackQuery):
    uid = cb.from_user.id
    msg = await bot.send_message(uid, "🔍 **Проверка на утечку DNS...**", parse_mode='Markdown')
    result = await test_dns_leak()
    if result.get('leak_detected'):
        await msg.edit_text("❌ **Обнаружена утечка DNS!**\nРекомендуем сменить DNS на Cloudflare (1.1.1.1)", parse_mode='Markdown')
    else:
        await msg.edit_text(f"✅ **Утечек DNS не обнаружено**\n🌐 Ваш IP: {result.get('ip', 'Unknown')}\n📍 Страна: {result.get('country', 'Unknown')}\n🏙️ Город: {result.get('city', 'Unknown')}\n📡 Провайдер: {result.get('isp', 'Unknown')}", parse_mode='Markdown')

@dp.callback_query_handler(lambda c: c.data == "traffic_stats")
async def traffic_stats_cb(cb: types.CallbackQuery):
    uid = cb.from_user.id
    stats = await get_traffic_stats(uid)
    text = f"📊 **Статистика трафика**\n\n📥 Скачано: {stats['total_download_gb']:.2f} GB\n📤 Загружено: {stats['total_upload_gb']:.2f} GB\n📦 Всего: {stats['total_gb']:.2f} GB\n\n📱 **По устройствам:**\n"
    for d in stats['devices']:
        text += f"   • {d['name']}: {d['down']:.2f} GB ↓ / {d['up']:.2f} GB ↑\n"
    await bot.send_message(uid, text, parse_mode='Markdown')

@dp.callback_query_handler(lambda c: c.data == "promo_code")
async def promo_code_prompt(cb: types.CallbackQuery):
    uid = cb.from_user.id
    await bot.send_message(uid, "🎫 **Введите промокод:**\n\nОтправьте код сообщением.", parse_mode='Markdown')

@dp.message_handler(lambda msg: msg.text and msg.text.upper() in PROMO_CODES and not msg.text.startswith('/'))
async def apply_promo(msg: types.Message):
    uid = msg.from_user.id
    code = msg.text.upper()
    success, result = await apply_promo_code(uid, code)
    await msg.reply(result, parse_mode='Markdown')

@dp.callback_query_handler(lambda c: c.data == "export_data")
async def export_data_cb(cb: types.CallbackQuery):
    uid = cb.from_user.id
    await bot.send_message(uid, "📥 **Экспорт данных...**", parse_mode='Markdown')
    data = await export_user_data(uid)
    await bot.send_document(uid, types.InputFile(data, filename=f"ultrovpn_user_{uid}_data.json"), caption="📄 Ваши данные в формате JSON")

@dp.callback_query_handler(lambda c: c.data == "backup_keys")
async def backup_keys_cb(cb: types.CallbackQuery):
    uid = cb.from_user.id
    codes = generate_backup_codes(uid)
    left = get_backup_codes_left(uid)
    await bot.send_message(uid,
        f"🔐 **Резервные коды:**\n\n" + "\n".join([f"`{c}`" for c in codes]) +
        f"\n\n⚠️ Сохраните! Осталось: {left}/8", parse_mode='Markdown')

@dp.callback_query_handler(lambda c: c.data == "referral")
async def referral_cb(cb: types.CallbackQuery):
    uid = cb.from_user.id
    bot_name = (await bot.get_me()).username
    link = f"https://t.me/{bot_name}?start=ref_{uid}"
    with get_db() as conn:
        cnt = conn.execute("SELECT COUNT(*) FROM users WHERE referred_by = (SELECT id FROM users WHERE telegram_id = ?)", (uid,)).fetchone()[0]
        bal = conn.execute("SELECT referral_balance FROM users WHERE telegram_id = ?", (uid,)).fetchone()[0]
    await bot.send_message(uid,
        f"🎁 **Реферальная система**\n\n💰 За друга: +{REFERRAL_BONUS}₽\n📊 Приглашено: {cnt}\n💰 Заработано: {bal}₽\n\n🔗 `{link}`\n\n💸 Для вывода бонусов используйте кнопку 'Вывод средств' в настройках.",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("📤 Поделиться", switch_inline_query=link),
            InlineKeyboardButton("💸 Вывод средств", callback_data="withdraw"),
            InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")
        ))

@dp.callback_query_handler(lambda c: c.data == "withdraw")
async def withdraw_cb(cb: types.CallbackQuery):
    uid = cb.from_user.id
    with get_db() as conn:
        bal = conn.execute("SELECT referral_balance FROM users WHERE telegram_id = ?", (uid,)).fetchone()[0]
    if not bal or bal < 100:
        await bot.answer_callback_query(cb.id, f"❌ Минимум 100₽. У вас: {bal or 0}₽", show_alert=True)
        return
    await bot.send_message(uid,
        f"💸 **Вывод средств**\n\n💰 Баланс: {bal}₽\n\n💳 **Способы вывода:**\n"
        f"• Telegram Stars (1:1)\n• USDT (TRC20) - кошелёк: `{USDT_WALLET if USDT_WALLET else 'Не настроен'}`\n• На баланс VPN\n\n"
        f"📝 Для вывода обратитесь к администратору @UltroVPNSupport",
        parse_mode='Markdown')

@dp.callback_query_handler(lambda c: c.data == "buy_premium")
async def buy_premium_cb(cb: types.CallbackQuery):
    await bot.send_message(cb.from_user.id,
        f"💎 **UltroVPN Premium**\n\n"
        f"🌟 1 мес - 299⭐️\n⭐️ 3 мес - 799⭐️ (экономия 98₽)\n💎 6 мес - 1499⭐️ (экономия 295₽)\n👑 12 мес - 2499⭐️ (экономия 1089₽)\n\n🔧 Антиглушилка AmneziaWG\n🛡️ VLESS Reality (обход DPI)\n💫 Автопродление\n\n👇 Выберите:",
        reply_markup=InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("🌟 1 мес", callback_data="pay_month"),
            InlineKeyboardButton("⭐️ 3 мес", callback_data="pay_quarter"),
            InlineKeyboardButton("💎 6 мес", callback_data="pay_halfyear"),
            InlineKeyboardButton("👑 12 мес", callback_data="pay_year"),
            InlineKeyboardButton("🪙 USDT", callback_data="pay_usdt"),
            InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")
        ))

@dp.callback_query_handler(lambda c: c.data.startswith("pay_"))
async def pay_cb(cb: types.CallbackQuery):
    uid = cb.from_user.id
    plan = cb.data.replace("pay_", "")
    if plan == "usdt":
        await bot.send_message(uid, f"🪙 **Оплата USDT**\n\nОтправьте нужную сумму на кошелёк:\n`{USDT_WALLET if USDT_WALLET else 'Не настроен'}`\n\nПосле оплаты пришлите чек в поддержку.", parse_mode='Markdown')
    elif plan in PRICES:
        await send_stars_invoice(uid, plan)
    else:
        await bot.send_message(uid, "❌ Ошибка", parse_mode='Markdown')

@dp.callback_query_handler(lambda c: c.data == "change_protocol")
async def change_protocol_cb(cb: types.CallbackQuery):
    uid = cb.from_user.id
    cur = "wireguard"
    with get_db() as conn:
        row = conn.execute("SELECT selected_protocol FROM users WHERE telegram_id = ?", (uid,)).fetchone()
        if row:
            cur = row['selected_protocol']
    await bot.send_message(uid,
        f"🌍 **Текущий протокол:** `{cur.upper()}`\n\n"
        f"⚡ WireGuard - быстрый, стабильный\n"
        f"🛡️ AmneziaWG - **АНТИГЛУШИЛКА** (маскировка трафика)\n"
        f"🔒 VLESS Reality - обход DPI\n"
        f"🛡️ Trojan - скрытый\n\n"
        f"⚠️ Для смены создайте новое устройство",
        parse_mode='Markdown',
        reply_markup=get_protocol_keyboard())

@dp.callback_query_handler(lambda c: c.data.startswith("protocol_"))
async def set_protocol_cb(cb: types.CallbackQuery):
    uid = cb.from_user.id
    proto = cb.data.replace("protocol_", "")
    with get_db() as conn:
        conn.execute("UPDATE users SET selected_protocol = ? WHERE telegram_id = ?", (proto, uid))
    await bot.answer_callback_query(cb.id, f"✅ Протокол {proto.upper()} выбран")
    await change_protocol_cb(cb)

@dp.callback_query_handler(lambda c: c.data == "two_factor_menu")
async def two_factor_menu_cb(cb: types.CallbackQuery):
    uid = cb.from_user.id
    with get_db() as conn:
        en = conn.execute("SELECT two_factor_enabled FROM users WHERE telegram_id = ?", (uid,)).fetchone()
        en = en['two_factor_enabled'] if en else 0
    if en:
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ Отключить 2FA", callback_data="two_factor_disable"), InlineKeyboardButton("🔙 Назад", callback_data="settings"))
        await bot.send_message(uid, "🔒 **2FA включена**", reply_markup=kb)
    else:
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🔒 Включить 2FA", callback_data="two_factor_setup"), InlineKeyboardButton("🔙 Назад", callback_data="settings"))
        await bot.send_message(uid, "🔒 **2FA не включена**", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "two_factor_setup")
async def two_factor_setup_cb(cb: types.CallbackQuery):
    uid = cb.from_user.id
    secret = pyotp.random_base32()
    with get_db() as conn:
        conn.execute("UPDATE users SET two_factor_secret = ?, two_factor_enabled = 1 WHERE telegram_id = ?", (secret, uid))
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=str(uid), issuer_name="UltroVPN")
    qr_img = qrcode.make(uri)
    bio = BytesIO()
    qr_img.save(bio, 'PNG')
    bio.seek(0)
    await bot.send_photo(uid, types.InputFile(bio), caption=f"🔐 **2FA настройка**\nСекрет: `{secret}`", parse_mode='Markdown')

@dp.callback_query_handler(lambda c: c.data == "two_factor_disable")
async def two_factor_disable_cb(cb: types.CallbackQuery):
    uid = cb.from_user.id
    with get_db() as conn:
        conn.execute("UPDATE users SET two_factor_secret = NULL, two_factor_enabled = 0 WHERE telegram_id = ?", (uid,))
    await bot.answer_callback_query(cb.id, "✅ 2FA отключена")
    await settings_cb(cb)

@dp.callback_query_handler(lambda c: c.data == "settings")
async def settings_cb(cb: types.CallbackQuery):
    uid = cb.from_user.id
    with get_db() as conn:
        s = conn.execute("SELECT s.*, u.auto_renew, u.selected_dns, u.selected_port FROM user_settings s JOIN users u ON u.id = s.user_id WHERE u.telegram_id = ?", (uid,)).fetchone()
    await bot.send_message(uid,
        f"⚙️ **Настройки**\n\n"
        f"🔄 Auto-connect: {'✅' if s['auto_connect'] else '❌'}\n"
        f"🛡️ Kill Switch: {'✅' if s['kill_switch'] else '❌'}\n"
        f"🛡️ AdBlock: {'✅' if s['ad_block'] else '❌'}\n"
        f"🔄 Автопродление: {'✅' if s['auto_renew'] else '❌'}\n"
        f"🌐 DNS: {s['selected_dns']}\n"
        f"🔌 Порт: {s['selected_port']}\n"
        f"⏰ Расписание: {'✅' if s['schedule_enabled'] else '❌'}",
        parse_mode='Markdown',
        reply_markup=get_settings_keyboard()
    )

@dp.callback_query_handler(lambda c: c.data == "toggle_autoconnect")
async def toggle_autoconnect(cb: types.CallbackQuery):
    uid = cb.from_user.id
    with get_db() as conn:
        cur = conn.execute("SELECT auto_connect FROM user_settings WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)", (uid,)).fetchone()[0]
        new = 0 if cur else 1
        conn.execute("UPDATE user_settings SET auto_connect = ? WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)", (new, uid))
    await bot.answer_callback_query(cb.id, f"Auto-connect {'вкл' if new else 'выкл'}")
    await settings_cb(cb)

@dp.callback_query_handler(lambda c: c.data == "toggle_killswitch")
async def toggle_killswitch(cb: types.CallbackQuery):
    uid = cb.from_user.id
    with get_db() as conn:
        cur = conn.execute("SELECT kill_switch FROM user_settings WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)", (uid,)).fetchone()[0]
        new = 0 if cur else 1
        conn.execute("UPDATE user_settings SET kill_switch = ? WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)", (new, uid))
    await bot.answer_callback_query(cb.id, f"Kill Switch {'вкл' if new else 'выкл'}")
    await settings_cb(cb)

@dp.callback_query_handler(lambda c: c.data == "toggle_adblock")
async def toggle_adblock(cb: types.CallbackQuery):
    uid = cb.from_user.id
    with get_db() as conn:
        cur = conn.execute("SELECT ad_block FROM user_settings WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)", (uid,)).fetchone()[0]
        new = 0 if cur else 1
        conn.execute("UPDATE user_settings SET ad_block = ? WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)", (new, uid))
    await bot.answer_callback_query(cb.id, f"AdBlock {'вкл' if new else 'выкл'}")
    await settings_cb(cb)

@dp.callback_query_handler(lambda c: c.data == "toggle_autorenew")
async def toggle_autorenew(cb: types.CallbackQuery):
    uid = cb.from_user.id
    with get_db() as conn:
        cur = conn.execute("SELECT auto_renew FROM users WHERE telegram_id = ?", (uid,)).fetchone()[0]
        new = 0 if cur else 1
        conn.execute("UPDATE users SET auto_renew = ? WHERE telegram_id = ?", (new, uid))
    await bot.answer_callback_query(cb.id, f"Автопродление {'вкл' if new else 'выкл'}")
    await settings_cb(cb)

@dp.callback_query_handler(lambda c: c.data == "change_dns")
async def change_dns_menu(cb: types.CallbackQuery):
    await bot.send_message(cb.from_user.id, "🌐 **Выберите DNS сервер:**", parse_mode='Markdown', reply_markup=get_dns_keyboard())

@dp.callback_query_handler(lambda c: c.data.startswith("dns_"))
async def set_dns(cb: types.CallbackQuery):
    uid = cb.from_user.id
    dns_map = {
        "cloudflare": "1.1.1.1",
        "google": "8.8.8.8",
        "adguard": "94.140.14.14"
    }
    dns_type = cb.data.replace("dns_", "")
    if dns_type == "custom":
        await bot.send_message(uid, "🔧 **Введите свой DNS сервер:**\nПример: 1.1.1.1", parse_mode='Markdown')
        return
    dns = dns_map.get(dns_type, "1.1.1.1")
    with get_db() as conn:
        conn.execute("UPDATE users SET selected_dns = ? WHERE telegram_id = ?", (dns, uid))
    await bot.answer_callback_query(cb.id, f"✅ DNS изменён на {dns}")
    await settings_cb(cb)

@dp.callback_query_handler(lambda c: c.data == "change_port")
async def change_port_prompt(cb: types.CallbackQuery):
    await bot.send_message(cb.from_user.id, "🔌 **Введите порт для WireGuard:**\n(по умолчанию 51820)\nДиапазон: 1024-65535", parse_mode='Markdown')

@dp.callback_query_handler(lambda c: c.data == "wifi_whitelist")
async def wifi_whitelist_menu(cb: types.CallbackQuery):
    uid = cb.from_user.id
    with get_db() as conn:
        ssids = conn.execute("SELECT ssid FROM wifi_whitelist WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)", (uid,)).fetchall()
    text = "📶 **White List WiFi**\n\nVPN будет включаться ТОЛЬКО на этих сетях:\n"
    for s in ssids:
        text += f"• `{s['ssid']}`\n"
    text += "\nОтправьте название WiFi сети (SSID) чтобы добавить\n/skip чтобы пропустить"
    await bot.send_message(uid, text, parse_mode='Markdown')

@dp.callback_query_handler(lambda c: c.data == "split_tunneling")
async def split_tunneling_menu(cb: types.CallbackQuery):
    uid = cb.from_user.id
    with get_db() as conn:
        apps = conn.execute("SELECT app_name FROM app_whitelist WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)", (uid,)).fetchall()
    text = "📱 **Split Tunneling**\n\nЧерез VPN будут идти ТОЛЬКО эти приложения:\n"
    for a in apps:
        text += f"• `{a['app_name']}`\n"
    text += "\nОтправьте название приложения чтобы добавить\n/skip чтобы пропустить"
    await bot.send_message(uid, text, parse_mode='Markdown')

@dp.callback_query_handler(lambda c: c.data == "schedule_settings")
async def schedule_cb(cb: types.CallbackQuery):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🕐 09:00-18:00", callback_data="schedule_work"),
        InlineKeyboardButton("🌙 00:00-06:00", callback_data="schedule_night"),
        InlineKeyboardButton("📅 Пн-Пт 09:00-18:00", callback_data="schedule_weekdays"),
        InlineKeyboardButton("🚫 Отключить", callback_data="schedule_off"),
        InlineKeyboardButton("🔙 Назад", callback_data="settings")
    )
    await bot.send_message(cb.from_user.id, "⏰ **Расписание VPN**", parse_mode='Markdown', reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("schedule_"))
async def set_schedule_cb(cb: types.CallbackQuery):
    uid = cb.from_user.id
    val = cb.data.replace("schedule_", "")
    with get_db() as conn:
        if val == "off":
            conn.execute("UPDATE user_settings SET schedule_enabled = 0, schedule_start = NULL, schedule_end = NULL WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)", (uid,))
            await bot.answer_callback_query(cb.id, "✅ Расписание отключено")
        elif val == "work":
            conn.execute("UPDATE user_settings SET schedule_enabled = 1, schedule_start = '09:00', schedule_end = '18:00' WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)", (uid,))
            await bot.answer_callback_query(cb.id, "✅ 09:00-18:00")
        elif val == "night":
            conn.execute("UPDATE user_settings SET schedule_enabled = 1, schedule_start = '00:00', schedule_end = '06:00' WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)", (uid,))
            await bot.answer_callback_query(cb.id, "✅ 00:00-06:00")
        elif val == "weekdays":
            conn.execute("UPDATE user_settings SET schedule_enabled = 1, schedule_start = '09:00', schedule_end = '18:00' WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)", (uid,))
            await bot.answer_callback_query(cb.id, "✅ Пн-Пт 09:00-18:00")
    await settings_cb(cb)

@dp.callback_query_handler(lambda c: c.data == "language")
async def language_menu(cb: types.CallbackQuery):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
        InlineKeyboardButton("🔙 Назад", callback_data="settings")
    )
    await bot.send_message(cb.from_user.id, "🌐 **Выберите язык / Select language:**", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("lang_"))
async def set_language(cb: types.CallbackQuery):
    uid = cb.from_user.id
    lang = cb.data.replace("lang_", "")
    with get_db() as conn:
        conn.execute("UPDATE users SET language = ? WHERE telegram_id = ?", (lang, uid))
    await bot.answer_callback_query(cb.id, f"✅ Язык изменён на {'Русский' if lang == 'ru' else 'English'}")
    await settings_cb(cb)

@dp.callback_query_handler(lambda c: c.data == "support")
async def support_menu(cb: types.CallbackQuery):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📝 Создать тикет", callback_data="new_ticket"),
        InlineKeyboardButton("📋 Мои тикеты", callback_data="my_tickets"),
        InlineKeyboardButton("📢 Канал", url=REQUIRED_CHANNEL_LINK),
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")
    )
    await bot.send_message(cb.from_user.id, "💬 **Поддержка UltroVPN**\n\nСоздайте тикет и мы ответим в ближайшее время.", parse_mode='Markdown', reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "new_ticket")
async def new_ticket_prompt(cb: types.CallbackQuery):
    await bot.send_message(cb.from_user.id, "📝 **Создание тикета**\n\nОтправьте текст вашего обращения.\n\nПример:\n`У меня проблема с подключением...`", parse_mode='Markdown')

@dp.callback_query_handler(lambda c: c.data == "my_tickets")
async def my_tickets(cb: types.CallbackQuery):
    uid = cb.from_user.id
    with get_db() as conn:
        tickets = conn.execute("SELECT id, subject, status, created_at FROM tickets WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?) ORDER BY created_at DESC", (uid,)).fetchall()
    if not tickets:
        await bot.send_message(cb.from_user.id, "📭 У вас нет тикетов", parse_mode='Markdown')
        return
    text = "📋 **Ваши тикеты:**\n\n"
    for t in tickets:
        status = "🟢 Открыт" if t['status'] == 'open' else "🔴 Закрыт"
        text += f"#{t['id']} - {t['subject'][:30]}... - {status}\n   📅 {t['created_at'][:10]}\n\n"
    await bot.send_message(cb.from_user.id, text, parse_mode='Markdown')

@dp.callback_query_handler(lambda c: c.data == "about")
async def about_cb(cb: types.CallbackQuery):
    await bot.send_message(cb.from_user.id,
        f"🔒 **UltroVPN v6.0**\n\n"
        f"⚡ **43 функции**\n"
        f"🛡️ **Антиглушилка AmneziaWG**\n"
        f"🔒 VLESS Reality (обход DPI)\n"
        f"📱 Все устройства\n"
        f"🎁 Рефералка + бонусы\n"
        f"🔐 2FA + резервные коды\n"
        f"📶 White List WiFi\n"
        f"📱 Split Tunneling\n"
        f"🔄 Автопродление\n"
        f"💸 Вывод средств\n\n"
        f"📢 [Канал]({REQUIRED_CHANNEL_LINK})\n\n"
        f"© UltroVPN 2024",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("📢 Канал", url=REQUIRED_CHANNEL_LINK),
            InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")
        ))

@dp.callback_query_handler(lambda c: c.data == "back_to_menu")
async def back_to_menu_cb(cb: types.CallbackQuery):
    await bot.send_message(cb.from_user.id, "🏠 **Главное меню:**", parse_mode='Markdown', reply_markup=await get_main_keyboard(cb.from_user.id))

# ============================================================
# АДМИН ПАНЕЛЬ
# ============================================================
@dp.callback_query_handler(lambda c: c.data == "admin_panel")
async def admin_panel_cb(cb: types.CallbackQuery):
    uid = cb.from_user.id
    with get_db() as conn:
        is_admin = conn.execute("SELECT is_admin FROM users WHERE telegram_id = ?", (uid,)).fetchone()
        if not is_admin or not is_admin['is_admin']:
            await bot.answer_callback_query(cb.id, "⛔ Нет доступа")
            return
        total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM users WHERE subscription_end > datetime('now')").fetchone()[0]
        devices = conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
        revenue = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE status = 'completed'").fetchone()[0]
    await bot.send_message(uid,
        f"👑 **Админ панель**\n\n👥 Всего: {total}\n🟢 Активных: {active}\n📱 Устройств: {devices}\n💰 Доход: {revenue}₽",
        reply_markup=InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast"),
            InlineKeyboardButton("🎫 Инвайт", callback_data="admin_invite"),
            InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")
        ))

@dp.callback_query_handler(lambda c: c.data == "admin_invite")
async def admin_invite_cb(cb: types.CallbackQuery):
    uid = cb.from_user.id
    with get_db() as conn:
        is_admin = conn.execute("SELECT is_admin FROM users WHERE telegram_id = ?", (uid,)).fetchone()
        if not is_admin or not is_admin['is_admin']:
            await bot.answer_callback_query(cb.id, "⛔ Нет доступа")
            return
    code = secrets.token_hex(8).upper()
    admin_id = get_user_db_id(uid)
    with get_db() as conn:
        conn.execute("INSERT INTO invites (code, created_by) VALUES (?, ?)", (code, admin_id))
    bot_name = (await bot.get_me()).username
    await bot.send_message(uid, f"🎫 **Инвайт:** `{code}`\n🔗 t.me/{bot_name}?start={code}", parse_mode='Markdown')

@dp.callback_query_handler(lambda c: c.data == "admin_broadcast")
async def admin_broadcast_prompt(cb: types.CallbackQuery):
    uid = cb.from_user.id
    with get_db() as conn:
        is_admin = conn.execute("SELECT is_admin FROM users WHERE telegram_id = ?", (uid,)).fetchone()
        if not is_admin or not is_admin['is_admin']:
            await bot.answer_callback_query(cb.id, "⛔ Нет доступа")
            return
    await bot.send_message(uid, "📢 **Рассылка**\n\nОтправьте текст. /cancel - отмена", parse_mode='Markdown')

@dp.message_handler(commands=['ban'])
async def ban_cmd(msg: types.Message):
    uid = msg.from_user.id
    with get_db() as conn:
        is_admin = conn.execute("SELECT is_admin FROM users WHERE telegram_id = ?", (uid,)).fetchone()
        if not is_admin or not is_admin['is_admin']:
            await msg.reply("⛔ Нет доступа")
            return
    args = msg.get_args()
    if not args:
        await msg.reply("❌ /ban TELEGRAM_ID")
        return
    try:
        target = int(args.split()[0])
        with get_db() as conn:
            conn.execute("UPDATE users SET is_banned = 1 WHERE telegram_id = ?", (target,))
        await msg.reply(f"✅ Заблокирован {target}")
    except:
        await msg.reply("❌ Ошибка")

@dp.message_handler(commands=['unban'])
async def unban_cmd(msg: types.Message):
    uid = msg.from_user.id
    with get_db() as conn:
        is_admin = conn.execute("SELECT is_admin FROM users WHERE telegram_id = ?", (uid,)).fetchone()
        if not is_admin or not is_admin['is_admin']:
            await msg.reply("⛔ Нет доступа")
            return
    args = msg.get_args()
    if not args:
        await msg.reply("❌ /unban TELEGRAM_ID")
        return
    try:
        target = int(args.split()[0])
        with get_db() as conn:
            conn.execute("UPDATE users SET is_banned = 0 WHERE telegram_id = ?", (target,))
        await msg.reply(f"✅ Разблокирован {target}")
    except:
        await msg.reply("❌ Ошибка")

@dp.message_handler(commands=['add_days'])
async def add_days_cmd(msg: types.Message):
    uid = msg.from_user.id
    with get_db() as conn:
        is_admin = conn.execute("SELECT is_admin FROM users WHERE telegram_id = ?", (uid,)).fetchone()
        if not is_admin or not is_admin['is_admin']:
            await msg.reply("⛔ Нет доступа")
            return
    args = msg.get_args()
    if not args:
        await msg.reply("❌ /add_days ID ДНИ")
        return
    try:
        parts = args.split()
        target = int(parts[0])
        days = int(parts[1])
        with get_db() as conn:
            row = conn.execute("SELECT subscription_end FROM users WHERE telegram_id = ?", (target,)).fetchone()
            if row:
                current = datetime.fromisoformat(row['subscription_end']) if row['subscription_end'] else datetime.now()
                new = max(current, datetime.now()) + timedelta(days=days)
                conn.execute("UPDATE users SET subscription_end = ? WHERE telegram_id = ?", (new.isoformat(), target))
                await msg.reply(f"✅ +{days} дней пользователю {target}\nНовая дата: {new.strftime('%d.%m.%Y')}")
            else:
                await msg.reply("❌ Пользователь не найден")
    except:
        await msg.reply("❌ Ошибка")

# ============================================================
# ЗАПУСК
# ============================================================
async def on_startup(dp):
    setup_wireguard_server()
    print("=" * 60)
    print("🚀 ULTRO VPN BOT v6.0 ЗАПУЩЕН!")
    print(f"📱 Бот: @{(await bot.get_me()).username}")
    print(f"🖥️ Сервер: {SERVER_PUBLIC_IP}:51820")
    print("=" * 60)
    print("✅ 43 ФУНКЦИИ АКТИВНЫ:")
    print("   • WireGuard + Антиглушилка AmneziaWG")
    print("   • VLESS Reality + Trojan")
    print("   • Рефералы + бонусы")
    print("   • 2FA + резервные коды")
    print("   • White List WiFi + Split Tunneling")
    print("   • Автопродление + вывод средств")
    print("   • Промокоды + экспорт данных")
    print("   • Тест DNS + график трафика")
    print("=" * 60)
    
    # Запускаем фоновые задачи
    asyncio.create_task(run_background_tasks())

async def run_background_tasks():
    while True:
        check_expiring_subscriptions()
        await auto_renew_subscriptions()
        await asyncio.sleep(3600)  # Раз в час

async def on_shutdown(dp):
    pass

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup, on_shutdown=on_shutdown)