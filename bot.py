#!/usr/bin/env python3
"""
ULTROVPN v8.0 — ЭНЕРГИЯ ТВОЕЙ СВОБОДЫ!
Версия: ПОЛНАЯ — БЕЗ ПРОВЕРКИ ПОДПИСКИ
Функции: VPN + Антиглушилка + Партнёрка + API + Промокоды + Стриминг + Аналитика + Автопостинг
"""

import os
import sys
import asyncio
import subprocess
import sqlite3
import qrcode
import secrets
import hashlib
import json
import logging
import shutil
import uuid
import socket
import re
import csv
from io import BytesIO, StringIO
from datetime import datetime, timedelta
from collections import defaultdict
from functools import wraps
from types import SimpleNamespace

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import speedtest
    SPEEDTEST_AVAILABLE = True
except ImportError:
    SPEEDTEST_AVAILABLE = False

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery, Message, CallbackQuery
from aiogram.utils import executor

# ========== НАСТРОЙКИ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден! Создайте файл .env с BOT_TOKEN=ваш_токен")
    sys.exit(1)

try:
    ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "829349232").split(",")]
except ValueError:
    print("❌ ОШИБКА: ADMIN_IDS должен содержать только числа через запятую")
    sys.exit(1)

SERVER_PUBLIC_IP = os.getenv("SERVER_PUBLIC_IP", "")
if not SERVER_PUBLIC_IP:
    print("❌ ОШИБКА: SERVER_PUBLIC_IP не найден в .env")
    sys.exit(1)

AUTO_POST_CHANNEL = os.getenv("AUTO_POST_CHANNEL", "")
AUTO_POST_ENABLED = os.getenv("AUTO_POST_ENABLED", "true").lower() == "true"
AUTO_POST_INTERVAL_HOURS = int(os.getenv("AUTO_POST_INTERVAL_HOURS", "6"))

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ultrovpn.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ========== КОНСТАНТЫ ==========
DEFAULT_SUBSCRIPTION_DAYS = 30
MAX_DEVICES_PER_USER = 10
REFERRAL_BONUS = 50
DAILY_BONUS = 5
WEEKLY_BONUS_MULTIPLIER = 2
WG_INTERFACE = "wg0"
WG_PORT = 51820
WG_SERVER_NETWORK = "10.0.0."

SERVER_PRIVATE_KEY = ""
SERVER_PUBLIC_KEY = ""

# ========== ЦЕНЫ ==========
PRICES = {
    "month": {"price": 299, "days": 30, "stars": 299, "name": "⚡️ 1 МЕСЯЦ"},
    "quarter": {"price": 799, "days": 90, "stars": 799, "name": "⭐️ 3 МЕСЯЦА"},
    "halfyear": {"price": 1499, "days": 180, "stars": 1499, "name": "💎 6 МЕСЯЦЕВ"},
    "year": {"price": 2499, "days": 365, "stars": 2499, "name": "👑 12 МЕСЯЦЕВ"},
    "lifetime": {"price": 4999, "days": 36500, "stars": 4999, "name": "♾️ ПОЖИЗНЕННО"},
}

# ========== СТРИМИНГ-ПАКЕТЫ ==========
STREAMING_PACKS = {
    "netflix": {"price": 99, "days": 30, "name": "🎬 NETFLIX ПАК"},
    "youtube": {"price": 49, "days": 30, "name": "📺 YOUTUBE ПАК"},
    "tiktok": {"price": 49, "days": 30, "name": "🎵 TIKTOK ПАК"},
    "all": {"price": 199, "days": 30, "name": "🌟 ВСЕ ПАКЕТЫ"},
}

# ========== ПРОМОКОДЫ ==========
PROMOCODES_LIST = {
    "WELCOME10": 10,
    "SAVE20": 20,
    "VIP50": 50,
}

# ========== API ТАРИФЫ ==========
API_PLANS = {
    "basic": {"price": 999, "requests": 1000, "days": 30, "name": "📡 BASIC"},
    "pro": {"price": 2999, "requests": 10000, "days": 30, "name": "🚀 PRO"},
    "enterprise": {"price": 9999, "requests": 100000, "days": 30, "name": "🏢 ENTERPRISE"},
}

# ========== ПАРТНЁРСКИЕ УРОВНИ ==========
PARTNER_LEVELS = {
    "bronze": {"min": 0, "percent": 15, "name": "🥉 БРОНЗА"},
    "silver": {"min": 10, "percent": 20, "name": "🥈 СЕРЕБРО"},
    "gold": {"min": 50, "percent": 25, "name": "🥇 ЗОЛОТО"},
    "platinum": {"min": 200, "percent": 30, "name": "💎 ПЛАТИНА"},
}

# ========== TEAM PLAN ==========
TEAM_PLANS = {
    "family": {"users": 5, "price": 999, "days": 30, "name": "👨‍👩‍👧‍👦 СЕМЕЙНЫЙ (5 МЕСТ)"},
    "business": {"users": 10, "price": 1999, "days": 30, "name": "🏢 БИЗНЕС (10 МЕСТ)"},
}

# ========== ДОСТИЖЕНИЯ ==========
ACHIEVEMENTS = {
    "first_week": {"name": "🌟 НОВИЧОК", "desc": "7 дней в VPN", "days": 7, "reward": 10},
    "first_month": {"name": "⚡ ОПЫТНЫЙ", "desc": "30 дней в VPN", "days": 30, "reward": 50},
    "referral_10": {"name": "🤝 ДРУЖЕЛЮБНЫЙ", "desc": "10 друзей", "target": 10, "reward": 100},
    "device_5": {"name": "📱 МУЛЬТИЗАДАЧНИК", "desc": "5 устройств", "target": 5, "reward": 50},
}

# ========== ЦВЕТОВЫЕ ТЕМЫ ==========
THEMES = {
    "dark": {"name": "🌙 ТЁМНАЯ", "bg": "#0f0c29", "text": "#ffffff"},
    "light": {"name": "☀️ СВЕТЛАЯ", "bg": "#f0f0f0", "text": "#000000"},
    "blue": {"name": "💙 СИНЯЯ", "bg": "#1a237e", "text": "#ffffff"},
    "green": {"name": "💚 ЗЕЛЁНАЯ", "bg": "#1b5e20", "text": "#ffffff"},
}

# ========== ЯЗЫКИ ==========
LANGUAGES = {
    "ru": {"welcome": "ДОБРО ПОЖАЛОВАТЬ", "subscribe": "ПОДПИСКА АКТИВИРОВАНА"},
    "en": {"welcome": "WELCOME", "subscribe": "SUBSCRIPTION ACTIVATED"},
    "uz": {"welcome": "XUSH KELIBSIZ", "subscribe": "OBUNA FAOLLASHTIRILDI"},
}

# ========== КОМАНДЫ ЭКСТРЕННОГО ОТКЛЮЧЕНИЯ ==========
EMERGENCY_COMMANDS = ["!off", "/stop", "выключить", "отключить"]

# ========== РЕКЛАМА ==========
SPONSOR_BUTTON_ENABLED = True
SPONSOR_BUTTON_TEXT = "🌟 НАШ ПАРТНЁР"
SPONSOR_BUTTON_URL = "https://t.me/UltroVPNSupport"

# ========== ШАБЛОНЫ ДЛЯ АВТОПОСТИНГА ==========
AUTO_POST_TEMPLATES = [
    {
        "text": """
⚡️ **ULTROVPN — ЭНЕРГИЯ ТВОЕЙ СВОБОДЫ!**

🔥 НОВЫЙ СЕРВЕР В НИДЕРЛАНДАХ!
🚀 Скорость увеличена на 50%

✅ БЕЗЛИМИТ
✅ АНТИГЛУШИЛКА
✅ 10 УСТРОЙСТВ

👉 @UltroVPNBot
        """,
        "parse_mode": "Markdown"
    },
    {
        "text": """
📊 **СТАТИСТИКА ULTROVPN**

👥 Новых пользователей сегодня: {new_users}
🟢 Активных прямо сейчас: {active_users}
💰 Доход за сегодня: {revenue}₽
🚀 Онлайн-устройств: {devices}

Стань частью статистики → @UltroVPNBot
        """,
        "parse_mode": "Markdown"
    },
]

# ========== ЭНЕРГИЧНЫЕ ТЕКСТЫ ==========
ENERGY_TEXTS = {
    "welcome": "⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️\n\n🔥 ДОБРО ПОЖАЛОВАТЬ В ULTROVPN!\n💪 ЭНЕРГИЯ ТВОЕЙ СВОБОДЫ!\n\n⚡️ ТВОЙ ИНТЕРНЕТ — ТВОИ ПРАВИЛА!\n🚀 БЕЗ ТОРМОЗОВ, БЕЗ БЛОКИРОВОК.\n\n✅ ТЕСТ-ДРАЙВ: 30 ДНЕЙ\n💪 ЗАРЯДИСЬ НА 100%!\n\n⚡️ НАЖМИ /start ⚡️\n\n⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️",
    "back": "⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️\n\n🔥 ВЫБЕРИ СВОЙ ЗАРЯД!\n\n⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️",
    "device_added": "⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️\n\n✅ УСТРОЙСТВО ЗАРЯЖЕНО!\n\n💪 IP: {}\n🔥 ПРОТОКОЛ: {}\n⚡️ QR-КОД ГОТОВ!\n\n1️⃣ СКАЧАЙ WIREGUARD\n2️⃣ ОТСКАНИРУЙ QR\n3️⃣ ЖМИ \"ПОДКЛЮЧИТЬСЯ\"\n\n🚀 ТЫ В ИГРЕ!\n\n⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️",
}

# ========== ЗАЩИТА ОТ ФЛУДА ==========
promo_attempts = defaultdict(int)
command_attempts = defaultdict(list)

def rate_limit(limit: int, per: int):
    def decorator(func):
        @wraps(func)
        async def wrapper(message, *args, **kwargs):
            user_id = message.from_user.id
            now = datetime.now()
            
            command_attempts[user_id] = [t for t in command_attempts[user_id] if now - t < timedelta(seconds=per)]
            
            if len(command_attempts[user_id]) >= limit:
                await message.reply(f"⏳ СЛИШКОМ МНОГО ЗАПРОСОВ! ПОДОЖДИТЕ {per} СЕКУНД")
                return
            
            command_attempts[user_id].append(now)
            return await func(message, *args, **kwargs)
        return wrapper
    return decorator

def admin_only(func):
    @wraps(func)
    async def wrapper(message_or_callback):
        uid = message_or_callback.from_user.id
        with get_db() as conn:
            cursor = conn.execute("SELECT is_admin FROM users WHERE telegram_id = ?", (uid,))
            row = cursor.fetchone()
            is_admin = row[0] if row else 0
            
            if not is_admin:
                if isinstance(message_or_callback, CallbackQuery):
                    await message_or_callback.answer("⛔ ДОСТУП ЗАПРЕЩЁН", show_alert=True)
                else:
                    await message_or_callback.reply("⛔ ДОСТУП ЗАПРЕЩЁН")
                return
        
        return await func(message_or_callback)
    return wrapper

# ========== БАЗА ДАННЫХ ==========
def get_db():
    return sqlite3.connect('ultrovpn.db')

def get_db_with_row():
    conn = sqlite3.connect('ultrovpn.db')
    conn.row_factory = sqlite3.Row
    return conn

def backup_db():
    try:
        os.makedirs('backups', exist_ok=True)
        backup_name = f"backups/ultrovpn_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2('ultrovpn.db', backup_name)
        for f in os.listdir('backups'):
            f_path = os.path.join('backups', f)
            if os.path.isfile(f_path) and datetime.fromtimestamp(os.path.getmtime(f_path)) < datetime.now() - timedelta(days=30):
                os.remove(f_path)
        logger.info(f"Бэкап БД создан: {backup_name}")
    except Exception as e:
        logger.error(f"Ошибка создания бэкапа БД: {e}")

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            username TEXT,
            first_name TEXT,
            subscription_end TEXT,
            balance REAL DEFAULT 0,
            referral_balance REAL DEFAULT 0,
            referred_by INTEGER,
            is_admin INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            selected_protocol TEXT DEFAULT 'wireguard',
            selected_dns TEXT DEFAULT '1.1.1.1',
            selected_port INTEGER DEFAULT 51820,
            last_bonus_date TEXT,
            bonus_streak INTEGER DEFAULT 0,
            auto_renew INTEGER DEFAULT 0,
            language TEXT DEFAULT 'ru',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS devices (
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
            total_download_mb INTEGER DEFAULT 0,
            total_upload_mb INTEGER DEFAULT 0
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            autoconnect INTEGER DEFAULT 0,
            killswitch INTEGER DEFAULT 1,
            adblock INTEGER DEFAULT 0,
            schedule_enabled INTEGER DEFAULT 0,
            schedule_start TEXT,
            schedule_end TEXT
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            payment_method TEXT,
            transaction_id TEXT UNIQUE,
            status TEXT DEFAULT 'pending',
            completed_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS promocodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            discount INTEGER,
            used_by INTEGER,
            used_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS partner_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            code TEXT UNIQUE,
            clicks INTEGER DEFAULT 0,
            registrations INTEGER DEFAULT 0,
            earnings REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS partner_levels (
            user_id INTEGER PRIMARY KEY,
            level TEXT DEFAULT 'bronze',
            referrals INTEGER DEFAULT 0,
            earnings REAL DEFAULT 0
        )''')
        
        cursor = conn.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
        if cursor.fetchone()[0] == 0:
            for aid in ADMIN_IDS:
                conn.execute("INSERT OR IGNORE INTO users (telegram_id, username, first_name, is_admin, subscription_end) VALUES (?, 'admin', 'Admin', 1, datetime('now', '+3650 days'))", (aid,))
        
        conn.execute("INSERT OR IGNORE INTO user_settings (user_id) SELECT id FROM users WHERE id NOT IN (SELECT user_id FROM user_settings)")
        
        logger.info("База данных инициализирована")
        backup_db()

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def get_user_db_id(tg_id):
    with get_db() as conn:
        cursor = conn.execute("SELECT id FROM users WHERE telegram_id = ?", (tg_id,))
        row = cursor.fetchone()
        return row[0] if row else None

def is_sub_active(tg_id):
    with get_db() as conn:
        cursor = conn.execute("SELECT subscription_end FROM users WHERE telegram_id = ?", (tg_id,))
        row = cursor.fetchone()
        if row and row[0]:
            try:
                return datetime.fromisoformat(row[0]) > datetime.now()
            except:
                return False
    return False

def give_daily_bonus(tg_id):
    with get_db() as conn:
        cursor = conn.execute("SELECT last_bonus_date, balance, bonus_streak FROM users WHERE telegram_id = ?", (tg_id,))
        row = cursor.fetchone()
        if not row:
            return False, 0, 0
        
        last_bonus = row[0]
        current_balance = row[1]
        current_streak = row[2] if row[2] else 0
        
        today = datetime.now().date()
        last = datetime.fromisoformat(last_bonus).date() if last_bonus else None
        
        if last == today:
            return False, 0, 0
        
        if last and (today - last).days == 1:
            new_streak = current_streak + 1
            conn.execute("UPDATE users SET bonus_streak = ? WHERE telegram_id = ?", (new_streak, tg_id))
        else:
            new_streak = 1
            conn.execute("UPDATE users SET bonus_streak = 1 WHERE telegram_id = ?", (tg_id,))
        
        bonus = DAILY_BONUS
        if new_streak % 7 == 0:
            bonus *= WEEKLY_BONUS_MULTIPLIER
        
        conn.execute("UPDATE users SET balance = balance + ?, last_bonus_date = datetime('now') WHERE telegram_id = ?", (bonus, tg_id))
        return True, bonus, new_streak

def update_partner_level(telegram_id):
    with get_db() as conn:
        uid = get_user_db_id(telegram_id)
        if not uid:
            return
        cursor = conn.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (uid,))
        referrals = cursor.fetchone()[0]
        level = "bronze"
        for lvl, data in PARTNER_LEVELS.items():
            if referrals >= data["min"]:
                level = lvl
        conn.execute("INSERT OR REPLACE INTO partner_levels (user_id, level, referrals) VALUES (?, ?, ?)", (uid, level, referrals))

def get_partner_percent(telegram_id):
    with get_db() as conn:
        uid = get_user_db_id(telegram_id)
        cursor = conn.execute("SELECT level FROM partner_levels WHERE user_id = ?", (uid,))
        row = cursor.fetchone()
        if row:
            return PARTNER_LEVELS[row[0]]["percent"]
    return 15

def apply_promocode(telegram_id, code):
    code = code.upper()
    
    if promo_attempts[telegram_id] >= 3:
        return False, "⏳ СЛИШКОМ МНОГО ПОПЫТОК! ПОДОЖДИТЕ 1 ЧАС"
    
    if code not in PROMOCODES_LIST:
        promo_attempts[telegram_id] += 1
        return False, "❌ НЕВЕРНЫЙ ПРОМОКОД"
    
    with get_db() as conn:
        cursor = conn.execute("SELECT 1 FROM promocodes WHERE code = ?", (code,))
        if cursor.fetchone():
            promo_attempts[telegram_id] += 1
            return False, "❌ ПРОМОКОД УЖЕ ИСПОЛЬЗОВАН"
        
        discount = PROMOCODES_LIST[code]
        uid = get_user_db_id(telegram_id)
        conn.execute("INSERT INTO promocodes (code, discount, used_by, used_at) VALUES (?, ?, ?, datetime('now'))", (code, discount, uid))
        conn.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (discount * 10, uid))
        
        promo_attempts[telegram_id] = 0
        return True, f"✅ ПРОМОКОД АКТИВИРОВАН! +{discount * 10}₽ НА БАЛАНС"

def generate_keys():
    try:
        priv = subprocess.check_output(['wg', 'genkey']).decode().strip()
        pub = subprocess.check_output(['wg', 'pubkey'], input=priv.encode()).decode().strip()
        return priv, pub
    except Exception as e:
        logger.error(f"Ошибка генерации ключей: {e}")
        return None, None

def get_next_ip():
    with get_db() as conn:
        cursor = conn.execute("SELECT ip_address FROM devices WHERE ip_address IS NOT NULL")
        used_ips = cursor.fetchall()
        used_nums = []
        for row in used_ips:
            if row[0]:
                try:
                    used_nums.append(int(row[0].split('.')[-1]))
                except:
                    pass
    
    for i in range(10, 255):
        if i not in used_nums:
            return f"{WG_SERVER_NETWORK}{i}"
    return f"{WG_SERVER_NETWORK}200"

def add_peer(pub, ip):
    try:
        subprocess.run(['wg', 'set', WG_INTERFACE, 'peer', pub, 'allowed-ips', f"{ip}/32"], check=True, capture_output=True)
        logger.info(f"Пир добавлен: {pub[:8]}... -> {ip}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка добавления пира: {e}")
        return False

def remove_peer(pub):
    try:
        subprocess.run(['wg', 'set', WG_INTERFACE, 'peer', pub, 'remove'], check=True, capture_output=True)
        logger.info(f"Пир удалён: {pub[:8]}...")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка удаления пира: {e}")
        return False

def generate_config(priv, ip, protocol='wireguard', dns='1.1.1.1', port=51820):
    if protocol == 'amneziawg':
        return f"""[Interface]
PrivateKey = {priv}
Address = {ip}/24
DNS = 1.1.1.1
MTU = 1420

[Peer]
PublicKey = {SERVER_PUBLIC_KEY}
Endpoint = {SERVER_PUBLIC_IP}:443
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25"""
    
    return f"""[Interface]
PrivateKey = {priv}
Address = {ip}/24
DNS = {dns}
MTU = 1420

[Peer]
PublicKey = {SERVER_PUBLIC_KEY}
Endpoint = {SERVER_PUBLIC_IP}:{port}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25"""

def gen_qr(text):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio

# ========== КЛАВИАТУРЫ ==========
async def main_kb(tg_id):
    with get_db() as conn:
        cursor = conn.execute("SELECT is_admin FROM users WHERE telegram_id = ?", (tg_id,))
        row = cursor.fetchone()
        is_admin = row[0] if row else 0
    
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🔋 МОЙ ЗАРЯД", callback_data="stats"),
        InlineKeyboardButton("⚡️ ВЗЛЕТАЙ", callback_data="add_device")
    )
    kb.add(
        InlineKeyboardButton("📱 МОИ УСТРОЙСТВА", callback_data="my_devices"),
        InlineKeyboardButton("💪 СТАНЬ СИЛЬНЕЕ", callback_data="buy_premium")
    )
    kb.add(
        InlineKeyboardButton("🎁 ЗАРЯДИ ДРУГА", callback_data="referral"),
        InlineKeyboardButton("🔥 АНТИГЛУШИЛКА", callback_data="change_protocol")
    )
    kb.add(
        InlineKeyboardButton("🎫 ПРОМОКОД", callback_data="enter_promo"),
        InlineKeyboardButton("⚡️ СПИД ТЕСТ", callback_data="speed_test")
    )
    kb.add(
        InlineKeyboardButton("⚙️ ТУРБО НАСТРОЙКИ", callback_data="settings"),
        InlineKeyboardButton("🔙 МЕНЮ", callback_data="back_to_menu")
    )
    if is_admin:
        kb.add(InlineKeyboardButton("👑 АДМИН", callback_data="admin_panel"))
    return kb

def protocol_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("⚡ WIREGUARD", callback_data="protocol_wireguard"),
        InlineKeyboardButton("🛡️ AMNEZIAWG", callback_data="protocol_amneziawg"),
        InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")
    )
    return kb

def settings_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🔄 AUTO-CONNECT", callback_data="toggle_autoconnect"),
        InlineKeyboardButton("🛡️ KILL SWITCH", callback_data="toggle_killswitch"),
        InlineKeyboardButton("🚫 ADBLOCK", callback_data="toggle_adblock"),
        InlineKeyboardButton("🔄 АВТОПРОДЛЕНИЕ", callback_data="toggle_autorenew"),
        InlineKeyboardButton("🌐 DNS", callback_data="change_dns"),
        InlineKeyboardButton("🔌 ПОРТ", callback_data="change_port"),
        InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")
    )
    return kb

def dns_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("☁️ CLOUDFLARE", callback_data="dns_cloudflare"),
        InlineKeyboardButton("🔍 GOOGLE", callback_data="dns_google"),
        InlineKeyboardButton("🔙 НАЗАД", callback_data="settings")
    )
    return kb

# ========== ПЛАТЕЖИ TELEGRAM STARS ==========
async def star_invoice(uid, plan):
    if plan not in PRICES:
        return
    p = PRICES[plan]
    try:
        await bot.send_invoice(
            uid, 
            title=f"ULTROVPN {p['days']} ДНЕЙ",
            description=f"ЭНЕРГИЯ ТВОЕЙ СВОБОДЫ!\nБЕЗЛИМИТ | ВСЕ СЕРВЕРЫ | АНТИГЛУШИЛКА",
            payload=f"sub_{plan}_{uid}",
            provider_token="", 
            currency="XTR",
            prices=[LabeledPrice(label="ULTROVPN PREMIUM", amount=p['stars'])],
            start_parameter="ultrovpn_sub"
        )
    except Exception as e:
        logger.error(f"Ошибка отправки инвойса: {e}")

# ========== ОСНОВНЫЕ ОБРАБОТЧИКИ ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def cmd_start(message: Message):
    uid = message.from_user.id
    name = message.from_user.first_name
    uname = message.from_user.username
    args = message.get_args()

    try:
        with get_db() as conn:
            cursor = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (uid,))
            user = cursor.fetchone()
            
            if not user:
                referred = None
                if args and args.startswith("ref_"):
                    ref_code = args.replace("ref_", "")
                    cursor = conn.execute("SELECT user_id FROM partner_links WHERE code = ?", (ref_code,))
                    partner = cursor.fetchone()
                    if partner:
                        referred = partner[0]
                        conn.execute("UPDATE partner_links SET registrations = registrations + 1 WHERE code = ?", (ref_code,))
                
                subscription_end = (datetime.now() + timedelta(days=DEFAULT_SUBSCRIPTION_DAYS)).isoformat()
                conn.execute('''INSERT INTO users (telegram_id, username, first_name, subscription_end, referred_by)
                                VALUES (?, ?, ?, ?, ?)''',
                             (uid, uname, name, subscription_end, referred))
                
                if referred:
                    conn.execute("UPDATE users SET referral_balance = referral_balance + ? WHERE id = ?", (REFERRAL_BONUS, referred))
                    update_partner_level(referred)
                
                conn.execute("INSERT INTO user_settings (user_id) SELECT id FROM users WHERE telegram_id = ?", (uid,))
                
                await message.reply(ENERGY_TEXTS["welcome"], parse_mode='Markdown', reply_markup=await main_kb(uid))
                logger.info(f"Новый пользователь: {uid} ({name})")
            else:
                if user[9] == 1:
                    await message.reply("🔴 **ДОСТУП ОГРАНИЧЕН!**\nОБРАТИСЬ В ПОДДЕРЖКУ @UltroVPNSupport", parse_mode='Markdown')
                    return
                
                got, amt, streak = give_daily_bonus(uid)
                bonus = f"\n🎁 +{amt}₽ (СТРИК {streak})" if got else ""
                
                end = datetime.fromisoformat(user[4]) if user[4] else datetime.now()
                left = max(0, (end - datetime.now()).days)
                
                cursor = conn.execute("SELECT COUNT(*) FROM devices WHERE user_id = ?", (user[0],))
                cnt = cursor.fetchone()[0]
                
                await message.reply(
                    f"⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️\n\n"
                    f"🔥 {name}, ТВОЙ ЗАРЯД: {left} ДНЕЙ!{bonus}\n"
                    f"💪 БАЛАНС: {user[5]}₽\n"
                    f"🎁 РЕФЕРАЛЫ: {user[6]}₽\n"
                    f"📱 УСТРОЙСТВ: {cnt}/{MAX_DEVICES_PER_USER}\n\n"
                    f"⚡️ ГЛАВНОЕ МЕНЮ:\n\n"
                    f"⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️",
                    parse_mode='Markdown', reply_markup=await main_kb(uid)
                )
    except Exception as e:
        logger.error(f"Ошибка в cmd_start: {e}")
        await message.reply("❌ ПРОИЗОШЛА ОШИБКА. ПОПРОБУЙТЕ ПОЗЖЕ")

@dp.callback_query_handler(lambda c: c.data == "stats")
async def stats_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    try:
        with get_db() as conn:
            u = conn.execute('''SELECT u.*, COUNT(d.id) as devs 
                                FROM users u 
                                LEFT JOIN devices d ON d.user_id = u.id 
                                WHERE u.telegram_id = ? 
                                GROUP BY u.id''', (uid,)).fetchone()
            
            cursor = conn.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM devices")
            total_devices = cursor.fetchone()[0]
        
        if u:
            end = datetime.fromisoformat(u[4]) if u[4] else datetime.now()
            left = max(0, (end - datetime.now()).days)
            devs = u[-1]
            
            with get_db() as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) + 1 FROM users u2
                    WHERE (SELECT COUNT(*) FROM users WHERE referred_by = u2.id) >
                          (SELECT COUNT(*) FROM users WHERE referred_by = ?)
                """, (u[0],))
                rank = cursor.fetchone()[0]
            
            text = f"""
💪 **МОЙ ЗАРЯД** 💪
━━━━━━━━━━━━━━━━━━━━━
👤 {u[3]}
🔋 ДО ЗАРЯДКИ: {left} ДНЕЙ
📱 УСТРОЙСТВ: {devs}/{MAX_DEVICES_PER_USER}
💰 БАЛАНС: {u[5]}₽
🎁 РЕФЕРАЛЫ: {u[6]}₽
🏆 МЕСТО В РЕЙТИНГЕ: #{rank}

━━━━━━━━━━━━━━━━━━━━━
📊 **СТАТИСТИКА СЕРВИСА:**
👥 ВСЕГО ПОЛЬЗОВАТЕЛЕЙ: {total_users}
📱 ВСЕГО УСТРОЙСТВ: {total_devices}

━━━━━━━━━━━━━━━━━━━━━
⚡️ ЗАРЯЖАЙСЯ ЕЩЁ! ⚡️
"""
            await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=await main_kb(uid))
    except Exception as e:
        logger.error(f"Ошибка в stats_cb: {e}")
        await callback.answer("❌ ОШИБКА ПОЛУЧЕНИЯ СТАТИСТИКИ", show_alert=True)

@dp.callback_query_handler(lambda c: c.data == "add_device")
async def add_device_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    
    if not is_sub_active(uid):
        await callback.answer("❌ ПОДПИСКА ИСТЕКЛА! ЗАРЯДИСЬ ЗАНОВО!", show_alert=True)
        return
    
    with get_db() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM devices d JOIN users u ON u.id = d.user_id WHERE u.telegram_id = ?", (uid,))
        cnt = cursor.fetchone()[0]
    
    if cnt >= MAX_DEVICES_PER_USER:
        await callback.answer(f"❌ ЛИМИТ {MAX_DEVICES_PER_USER} УСТРОЙСТВ!", show_alert=True)
        return
    
    kb = InlineKeyboardMarkup(row_width=2)
    for t in ["windows", "macos", "android", "ios", "linux"]:
        kb.add(InlineKeyboardButton(f"💻 {t.upper()}", callback_data=f"device_{t}"))
    kb.add(InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu"))
    
    await callback.message.edit_text("⚡️ **ВЫБЕРИ УСТРОЙСТВО ДЛЯ ЗАРЯДКИ** ⚡️", parse_mode='Markdown', reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("device_"))
async def create_device_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    dtype = callback.data.split('_')[1]
    
    if not is_sub_active(uid):
        await callback.answer("❌ ПОДПИСКА ИСТЕКЛА", show_alert=True)
        return
    
    try:
        with get_db() as conn:
            cursor = conn.execute("SELECT selected_protocol, selected_port, selected_dns FROM users WHERE telegram_id = ?", (uid,))
            u = cursor.fetchone()
            proto = u[0] if u else 'wireguard'
            port = u[1] if u else 51820
            dns = u[2] if u else '1.1.1.1'
        
        priv, pub = generate_keys()
        if not priv:
            await callback.answer("❌ ОШИБКА ГЕНЕРАЦИИ КЛЮЧЕЙ", show_alert=True)
            return
        
        ip = get_next_ip()
        name = f"{dtype}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        uidb = get_user_db_id(uid)
        
        with get_db() as conn:
            conn.execute("""INSERT INTO devices (user_id, device_name, device_type, protocol, private_key, public_key, ip_address, port) 
                           VALUES (?,?,?,?,?,?,?,?)""",
                         (uidb, name, dtype, proto, priv, pub, ip, port))
        
        add_peer(pub, ip)
        
        cfg = generate_config(priv, ip, proto, dns, port)
        qr = gen_qr(cfg)
        await callback.message.delete()
        await callback.message.bot.send_photo(uid, types.InputFile(qr), caption=ENERGY_TEXTS["device_added"].format(ip, proto.upper()), parse_mode='Markdown')
        cf = BytesIO(cfg.encode())
        cf.name = f"ultrovpn_{dtype}.conf"
        await callback.message.bot.send_document(uid, types.InputFile(cf))
        
        await callback.answer("✅ УСТРОЙСТВО СОЗДАНО!")
        logger.info(f"Создано устройство для {uid}: {name}")
        
    except Exception as e:
        logger.error(f"Ошибка создания устройства: {e}")
        await callback.answer("❌ ОШИБКА СОЗДАНИЯ УСТРОЙСТВА", show_alert=True)

@dp.callback_query_handler(lambda c: c.data == "my_devices")
async def my_devices_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    
    with get_db() as conn:
        cursor = conn.execute("SELECT d.* FROM devices d JOIN users u ON u.id = d.user_id WHERE u.telegram_id = ? AND d.is_enabled = 1", (uid,))
        devs = cursor.fetchall()
    
    if not devs:
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("⚡️ ВЗЛЕТАЙ", callback_data="add_device"))
        kb.add(InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu"))
        await callback.message.edit_text("⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️\n\n🔋 **ТВОИ УСТРОЙСТВА:**\n📭 ПОКА ПУСТО!\n\n⚡️ НАЖМИ «ВЗЛЕТАЙ» И ЗАРЯДИСЬ! ⚡️\n\n⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️", parse_mode='Markdown', reply_markup=kb)
        return
    
    txt = "🔋 **ТВОИ УСТРОЙСТВА:**\n━━━━━━━━━━━━━━━━━━━━━\n"
    kb = InlineKeyboardMarkup()
    for d in devs:
        txt += f"🔥 {d[2]} — {d[4].upper()}\n   🌐 IP: `{d[7]}`\n\n"
        kb.add(InlineKeyboardButton(f"🗑 УДАЛИТЬ {d[2]}", callback_data=f"delete_{d[0]}"))
    kb.add(InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu"))
    
    await callback.message.edit_text(txt, parse_mode='Markdown', reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("delete_"))
async def delete_device_cb(callback: CallbackQuery):
    did = int(callback.data.split('_')[1])
    
    with get_db() as conn:
        cursor = conn.execute("SELECT public_key FROM devices WHERE id = ?", (did,))
        pub = cursor.fetchone()
        if pub:
            remove_peer(pub[0])
            conn.execute("DELETE FROM devices WHERE id = ?", (did,))
    
    await callback.answer("✅ УСТРОЙСТВО УДАЛЕНО!")
    await my_devices_cb(callback)

@dp.callback_query_handler(lambda c: c.data == "referral")
async def referral_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    update_partner_level(uid)
    botname = (await bot.get_me()).username
    link = f"https://t.me/{botname}?start=ref_{uid}"
    
    with get_db() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM users WHERE referred_by = (SELECT id FROM users WHERE telegram_id = ?)", (uid,))
        cnt = cursor.fetchone()[0]
        cursor = conn.execute("SELECT referral_balance FROM users WHERE telegram_id = ?", (uid,))
        bal = cursor.fetchone()[0]
        percent = get_partner_percent(uid)
    
    text = f"🎁 **ЗАРЯДИ ДРУГА!** 🎁\n━━━━━━━━━━━━━━━━━━━━━\n🔥 ЗА КАЖДОГО ДРУГА: {REFERRAL_BONUS}₽\n⭐️ ТВОЯ СТАВКА: {percent}%\n📊 ПРИГЛАСИЛ: {cnt}\n💰 НА ЗАРЯДЕ: {bal}₽\n━━━━━━━━━━━━━━━━━━━━━\n⚡️ **ТВОЯ ССЫЛКА:**\n`{link}`\n\n💪 ДЕЛИСЬ ЭНЕРГИЕЙ! 💪"
    
    await callback.message.edit_text(text, parse_mode='Markdown', 
                               reply_markup=InlineKeyboardMarkup().add(
                                   InlineKeyboardButton("📤 ПОДЕЛИТЬСЯ", switch_inline_query=link),
                                   InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")))

@dp.callback_query_handler(lambda c: c.data == "enter_promo")
async def enter_promo_cb(callback: CallbackQuery):
    text = "🎫 **ВВЕДИ ПРОМОКОД:**\n━━━━━━━━━━━━━━━━━━━━━\n🔥 ДОСТУПНЫЕ ПРОМОКОДЫ:\n• `WELCOME10` — +100₽\n• `SAVE20` — +200₽\n• `VIP50` — +500₽\n━━━━━━━━━━━━━━━━━━━━━\n📝 ОТПРАВЬ КОД СООБЩЕНИЕМ"
    
    await callback.message.edit_text(text, parse_mode='Markdown', 
                               reply_markup=InlineKeyboardMarkup().add(
                                   InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")))

@dp.message_handler(lambda m: m.text and m.text.upper() in PROMOCODES_LIST)
@rate_limit(3, 3600)
async def use_promo_handler(message: Message):
    success, result = apply_promocode(message.from_user.id, message.text)
    await message.reply(result, parse_mode='Markdown')

@dp.callback_query_handler(lambda c: c.data == "buy_premium")
async def buy_premium_cb(callback: CallbackQuery):
    text = "💪 **СТАНЬ СИЛЬНЕЕ!** 💪\n━━━━━━━━━━━━━━━━━━━━━\n"
    for k, p in PRICES.items():
        text += f"{p['name']} — {p['price']}⭐️ / {p['days']} ДНЕЙ\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n🔥 ВЫБИРАЙ СВОЙ ЗАРЯД!"
    
    kb = InlineKeyboardMarkup(row_width=2)
    for k in PRICES:
        kb.add(InlineKeyboardButton(PRICES[k]["name"], callback_data=f"pay_{k}"))
    kb.add(InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu"))
    
    await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("pay_"))
async def pay_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    plan = callback.data.replace("pay_", "")
    await star_invoice(uid, plan)
    await callback.answer()

@dp.pre_checkout_query_handler(lambda q: True)
async def pre_checkout_query_handler(q: PreCheckoutQuery):
    try:
        await bot.answer_pre_checkout_query(q.id, ok=True)
    except Exception as e:
        logger.error(f"Ошибка pre-checkout: {e}")
        await bot.answer_pre_checkout_query(q.id, ok=False, error_message="Ошибка платежа")

@dp.message_handler(content_types=types.ContentType.SUCCESSFUL_PAYMENT)
async def successful_payment_handler(message: Message):
    uid = message.from_user.id
    payload = message.successful_payment.invoice_payload
    
    days_map = {"month": 30, "quarter": 90, "halfyear": 180, "year": 365, "lifetime": 36500}
    days = 30
    for key, d in days_map.items():
        if key in payload:
            days = d
            break
    
    try:
        with get_db() as conn:
            cursor = conn.execute("SELECT subscription_end FROM users WHERE telegram_id = ?", (uid,))
            row = cursor.fetchone()
            cur = datetime.fromisoformat(row[0]) if row and row[0] else datetime.now()
            new_end = max(cur, datetime.now()) + timedelta(days=days)
            conn.execute("UPDATE users SET subscription_end = ? WHERE telegram_id = ?", (new_end.isoformat(), uid))
            uidb = get_user_db_id(uid)
            conn.execute("""INSERT INTO transactions (user_id, amount, payment_method, transaction_id, status, completed_at) 
                           VALUES (?, ?, 'stars', ?, 'completed', datetime('now'))""",
                         (uidb, days * 10, message.successful_payment.provider_payment_charge_id))
            
            cursor = conn.execute("SELECT referred_by FROM users WHERE id = ?", (uidb,))
            referred_by = cursor.fetchone()
            if referred_by and referred_by[0]:
                conn.execute("UPDATE users SET referral_balance = referral_balance + ? WHERE id = ?", 
                           (REFERRAL_BONUS, referred_by[0]))
                update_partner_level(referred_by[0])
        
        await message.reply(f"✅ ОПЛАЧЕНО! ПОДПИСКА ДО {new_end.strftime('%d.%m.%Y')}\n🔥 ТВОЙ ЗАРЯД АКТИВЕН!", parse_mode='Markdown')
        logger.info(f"Платеж успешен: {uid} на {days} дней")
    except Exception as e:
        logger.error(f"Ошибка обработки платежа: {e}")
        await message.reply("❌ ОШИБКА АКТИВАЦИИ ПОДПИСКИ! ОБРАТИТЕСЬ В ПОДДЕРЖКУ")

@dp.callback_query_handler(lambda c: c.data == "change_protocol")
async def change_protocol_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    with get_db() as conn:
        cursor = conn.execute("SELECT selected_protocol FROM users WHERE telegram_id = ?", (uid,))
        r = cursor.fetchone()
        cur = r[0] if r else 'wireguard'
    
    text = f"🌍 **ТЕКУЩИЙ ПРОТОКОЛ:** `{cur.upper()}`\n━━━━━━━━━━━━━━━━━━━━━\n⚡ WIREGUARD — БЫСТРЫЙ\n🛡️ AMNEZIAWG — АНТИГЛУШИЛКА\n━━━━━━━━━━━━━━━━━━━━━\n⚠️ ДЛЯ СМЕНЫ ПРОТОКОЛА СОЗДАЙ НОВОЕ УСТРОЙСТВО"
    
    await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=protocol_kb())

@dp.callback_query_handler(lambda c: c.data.startswith("protocol_"))
async def set_protocol_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    proto = callback.data.replace("protocol_", "")
    
    with get_db() as conn:
        conn.execute("UPDATE users SET selected_protocol = ? WHERE telegram_id = ?", (proto, uid))
    
    await callback.answer(f"✅ ПРОТОКОЛ {proto.upper()} ВЫБРАН!", show_alert=True)
    await change_protocol_cb(callback)

@dp.callback_query_handler(lambda c: c.data == "settings")
async def settings_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    
    with get_db() as conn:
        cursor = conn.execute("""SELECT s.autoconnect, s.killswitch, s.adblock, u.auto_renew, u.selected_dns, u.selected_port 
                                FROM user_settings s 
                                JOIN users u ON u.id = s.user_id 
                                WHERE u.telegram_id = ?""", (uid,))
        s = cursor.fetchone()
    
    if s:
        txt = f"⚙️ **ТУРБО НАСТРОЙКИ** ⚙️\n━━━━━━━━━━━━━━━━━━━━━\n"
        txt += f"🔄 AUTO-CONNECT: {'✅' if s[0] else '❌'}\n"
        txt += f"🛡️ KILL SWITCH: {'✅' if s[1] else '❌'}\n"
        txt += f"🚫 ADBLOCK: {'✅' if s[2] else '❌'}\n"
        txt += f"🔄 АВТОПРОДЛЕНИЕ: {'✅' if s[3] else '❌'}\n"
        txt += f"🌐 DNS: {s[4]}\n"
        txt += f"🔌 ПОРТ: {s[5]}\n"
        txt += "━━━━━━━━━━━━━━━━━━━━━\n🔥 НАСТРОЙ ПОД СЕБЯ!"
        
        await callback.message.edit_text(txt, parse_mode='Markdown', reply_markup=settings_kb())

@dp.callback_query_handler(lambda c: c.data.startswith("toggle_"))
async def toggle_setting_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    setting = callback.data.replace("toggle_", "")
    
    with get_db() as conn:
        if setting in ['autoconnect', 'killswitch', 'adblock']:
            cursor = conn.execute(f"SELECT {setting} FROM user_settings WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)", (uid,))
            cur = cursor.fetchone()[0]
            new = 0 if cur else 1
            conn.execute(f"UPDATE user_settings SET {setting} = ? WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)", (new, uid))
        elif setting == 'autorenew':
            cursor = conn.execute("SELECT auto_renew FROM users WHERE telegram_id = ?", (uid,))
            cur = cursor.fetchone()[0]
            new = 0 if cur else 1
            conn.execute("UPDATE users SET auto_renew = ? WHERE telegram_id = ?", (new, uid))
    
    await callback.answer(f"✅ {setting.upper()} ИЗМЕНЁН!", show_alert=True)
    await settings_cb(callback)

@dp.callback_query_handler(lambda c: c.data == "change_dns")
async def change_dns_menu_cb(callback: CallbackQuery):
    text = "🌐 **ВЫБЕРИ DNS СЕРВЕР** 🌐\n━━━━━━━━━━━━━━━━━━━━━\n☁️ CLOUDFLARE (1.1.1.1)\n🔍 GOOGLE (8.8.8.8)\n━━━━━━━━━━━━━━━━━━━━━\n⚡️ ВЫБЕРИ ДЛЯ МАКСИМАЛЬНОЙ СКОРОСТИ"
    
    await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=dns_kb())

@dp.callback_query_handler(lambda c: c.data.startswith("dns_"))
async def set_dns_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    dns_map = {"cloudflare": "1.1.1.1", "google": "8.8.8.8"}
    t = callback.data.replace("dns_", "")
    
    dns = dns_map.get(t, "1.1.1.1")
    with get_db() as conn:
        conn.execute("UPDATE users SET selected_dns = ? WHERE telegram_id = ?", (dns, uid))
    
    await callback.answer(f"✅ DNS ИЗМЕНЁН НА {dns}!", show_alert=True)
    await settings_cb(callback)

@dp.callback_query_handler(lambda c: c.data == "change_port")
async def change_port_prompt_cb(callback: CallbackQuery):
    text = "🔌 **ИЗМЕНЕНИЕ ПОРТА**\n━━━━━━━━━━━━━━━━━━━━━\n📝 ВВЕДИ НОВЫЙ ПОРТ (1024-65535)\n\n⚠️ ПОСЛЕ ИЗМЕНЕНИЯ НУЖНО ПЕРЕСОЗДАТЬ УСТРОЙСТВА"
    
    await callback.message.edit_text(text, parse_mode='Markdown', 
                               reply_markup=InlineKeyboardMarkup().add(
                                   InlineKeyboardButton("🔙 НАЗАД", callback_data="settings")))

@dp.callback_query_handler(lambda c: c.data == "speed_test")
async def speed_test_cb(callback: CallbackQuery):
    await callback.answer("🚀 СПИД ТЕСТ ДОСТУПЕН В PRO ВЕРСИИ!", show_alert=True)

@dp.callback_query_handler(lambda c: c.data == "back_to_menu")
async def back_to_menu_cb(callback: CallbackQuery):
    await callback.message.edit_text(ENERGY_TEXTS["back"], parse_mode='Markdown', 
                               reply_markup=await main_kb(callback.from_user.id))

@dp.callback_query_handler(lambda c: c.data == "admin_panel")
@admin_only
async def admin_panel_cb(callback: CallbackQuery):
    text = "👑 **АДМИН ПАНЕЛЬ** 👑\n━━━━━━━━━━━━━━━━━━━━━\n📌 **КОМАНДЫ:**\n\n`/users` — СПИСОК ПОЛЬЗОВАТЕЛЕЙ\n`/deluser ID` — УДАЛИТЬ\n`/add_days ID ДНИ` — ДОБАВИТЬ ДНИ\n`/broadcast` — РАССЫЛКА\n\n━━━━━━━━━━━━━━━━━━━━━\n🔥 УПРАВЛЯЙ ЭНЕРГИЕЙ!"
    
    await callback.message.edit_text(text, parse_mode='Markdown', 
                               reply_markup=InlineKeyboardMarkup().add(
                                   InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")))

@dp.message_handler(commands=['users'])
@admin_only
async def users_cmd(message: Message):
    try:
        with get_db() as conn:
            cursor = conn.execute("SELECT telegram_id, first_name, subscription_end FROM users ORDER BY id DESC LIMIT 50")
            users = cursor.fetchall()
        
        if not users:
            await message.reply("📭 НЕТ ПОЛЬЗОВАТЕЛЕЙ")
            return
        
        text = "👥 **ПОЛЬЗОВАТЕЛИ (50):**\n━━━━━━━━━━━━━━━━━━━━━\n"
        for u in users:
            end = u[2][:10] if u[2] else "НЕТ"
            text += f"• `{u[0]}` — {u[1][:15]} | ДО {end}\n"
        
        await message.reply(text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Ошибка в users_cmd: {e}")
        await message.reply("❌ ОШИБКА ПОЛУЧЕНИЯ СПИСКА")

@dp.message_handler(commands=['deluser'])
@admin_only
async def deluser_cmd(message: Message):
    args = message.get_args().split()
    if not args:
        await message.reply("❌ /deluser TELEGRAM_ID")
        return
    
    try:
        target = int(args[0])
        with get_db() as conn:
            cursor = conn.execute("SELECT id FROM users WHERE telegram_id = ?", (target,))
            uidb = cursor.fetchone()
            if uidb:
                conn.execute("DELETE FROM devices WHERE user_id = ?", (uidb[0],))
                conn.execute("DELETE FROM users WHERE telegram_id = ?", (target,))
                await message.reply(f"✅ ПОЛЬЗОВАТЕЛЬ `{target}` УДАЛЁН", parse_mode='Markdown')
            else:
                await message.reply(f"❌ ПОЛЬЗОВАТЕЛЬ `{target}` НЕ НАЙДЕН", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Ошибка в deluser_cmd: {e}")
        await message.reply("❌ ОШИБКА УДАЛЕНИЯ")

@dp.message_handler(commands=['add_days'])
@admin_only
async def add_days_cmd(message: Message):
    args = message.get_args().split()
    if len(args) < 2:
        await message.reply("❌ /add_days ID ДНИ")
        return
    
    try:
        target = int(args[0])
        days = int(args[1])
        
        with get_db() as conn:
            cursor = conn.execute("SELECT subscription_end FROM users WHERE telegram_id = ?", (target,))
            row = cursor.fetchone()
            if row:
                current = datetime.fromisoformat(row[0]) if row[0] else datetime.now()
                new_end = max(current, datetime.now()) + timedelta(days=days)
                conn.execute("UPDATE users SET subscription_end = ? WHERE telegram_id = ?", (new_end.isoformat(), target))
                await message.reply(f"✅ +{days} ДНЕЙ ПОЛЬЗОВАТЕЛЮ `{target}`\n📅 НОВАЯ ДАТА: {new_end.strftime('%d.%m.%Y')}", parse_mode='Markdown')
            else:
                await message.reply(f"❌ ПОЛЬЗОВАТЕЛЬ `{target}` НЕ НАЙДЕН", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Ошибка в add_days_cmd: {e}")
        await message.reply("❌ ОШИБКА ДОБАВЛЕНИЯ ДНЕЙ")

@dp.message_handler(commands=['broadcast'])
@admin_only
async def broadcast_cmd(message: Message):
    text = message.get_args()
    if not text:
        await message.reply("❌ /broadcast ТЕКСТ")
        return
    
    try:
        with get_db() as conn:
            cursor = conn.execute("SELECT telegram_id FROM users")
            users = cursor.fetchall()
        
        sent = 0
        await message.reply(f"⏳ НАЧАЛА РАССЫЛКИ {len(users)} ПОЛЬЗОВАТЕЛЕЙ...")
        
        for u in users:
            try:
                await bot.send_message(u[0], f"⚡️ **НОВОСТЬ ULTROVPN** ⚡️\n━━━━━━━━━━━━━━━━━━━━━\n{text}\n━━━━━━━━━━━━━━━━━━━━━", parse_mode='Markdown')
                sent += 1
                await asyncio.sleep(0.05)
            except:
                pass
        
        await message.reply(f"✅ РАССЫЛКА ЗАВЕРШЕНА!\n📨 ОТПРАВЛЕНО: {sent}")
        logger.info(f"Рассылка завершена. Отправлено: {sent}")
    except Exception as e:
        logger.error(f"Ошибка в broadcast_cmd: {e}")
        await message.reply("❌ ОШИБКА РАССЫЛКИ")

# ========== ЗАПУСК ==========
async def on_startup(dp):
    try:
        me = await bot.get_me()
        logger.info("=" * 60)
        logger.info("⚡️ ULTROVPN v8.0 — ЭНЕРГИЯ ТВОЕЙ СВОБОДЫ! ⚡️")
        logger.info(f"🔥 БОТ ЗАПУЩЕН: @{me.username}")
        logger.info("=" * 60)
        
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, 
                    "⚡️ **ULTROVPN БОТ ЗАПУЩЕН!** ⚡️\n"
                    f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
                    "🔥 ВСЕ СИСТЕМЫ ГОТОВЫ!", parse_mode='Markdown')
            except:
                pass
                
    except Exception as e:
        logger.error(f"Ошибка при запуске: {e}")

def main():
    init_db()
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)

if __name__ == '__main__':
    main()
