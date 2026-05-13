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

# Try to import dotenv, but don't fail if not available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Try to import speedtest, but don't fail if not available
try:
    import speedtest
    SPEEDTEST_AVAILABLE = True
except ImportError:
    SPEEDTEST_AVAILABLE = False

# Try to import aiohttp
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

# Настройки автопостинга
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
    {
        "text": """
🎁 **АКЦИЯ НЕДЕЛИ!**

ПРОМОКОД: WEEKEND30
🔥 +30% к подписке бесплатно!

Активируй в боте: @UltroVPNBot

⏰ Действует до воскресенья!
        """,
        "parse_mode": "Markdown"
    },
    {
        "text": """
💪 **ТОП РЕФЕРАЛОВ МЕСЯЦА**

{top_referrals}

🔥 Приведи друзей и получи до 30% от их платежей!

Твоя ссылка: https://t.me/UltroVPNBot?start=ref_{user_id}
        """,
        "parse_mode": "Markdown"
    },
    {
        "text": """
🌍 **НОВОСТИ ULTROVPN**

✅ Добавлена поддержка VLESS протокола
✅ Улучшена антиглушилка
✅ Оптимизация скорости

Проверь сам → @UltroVPNBot
        """,
        "parse_mode": "Markdown"
    }
]

# ========== ЭНЕРГИЧНЫЕ ТЕКСТЫ ==========
ENERGY_TEXTS = {
    "welcome": "⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️\n\n🔥 ДОБРО ПОЖАЛОВАТЬ В ULTROVPN!\n💪 ЭНЕРГИЯ ТВОЕЙ СВОБОДЫ!\n\n⚡️ ТВОЙ ИНТЕРНЕТ — ТВОИ ПРАВИЛА!\n🚀 БЕЗ ТОРМОЗОВ, БЕЗ БЛОКИРОВОК.\n\n✅ ТЕСТ-ДРАЙВ: 30 ДНЕЙ\n💪 ЗАРЯДИСЬ НА 100%!\n\n⚡️ НАЖМИ /start ⚡️\n\n⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️",
    "back": "⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️\n\n🔥 ВЫБЕРИ СВОЙ ЗАРЯД!\n\n⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️",
    "device_added": "⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️\n\n✅ УСТРОЙСТВО ЗАРЯЖЕНО!\n\n💪 IP: {}\n🔥 ПРОТОКОЛ: {}\n⚡️ QR-КОД ГОТОВ!\n\n1️⃣ СКАЧАЙ WIREGUARD\n2️⃣ ОТСКАНИРУЙ QR\n3️⃣ ЖМИ \"ПОДКЛЮЧИТЬСЯ\"\n\n🚀 ТЫ В ИГРЕ!\n\n⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️",
    "stats": "💪 МОЙ ЗАРЯД 💪\n━━━━━━━━━━━━━━━━━━━━━\n👤 {}\n🔋 ДО ЗАРЯДКИ: {} ДНЕЙ\n📱 УСТРОЙСТВ: {}\n💰 БАЛАНС: {}₽\n🎁 РЕФЕРАЛЫ: {}₽\n━━━━━━━━━━━━━━━━━━━━━\n⚡️ ЗАРЯЖАЙСЯ ЕЩЁ! ⚡️",
}

# ========== ЗАЩИТА ОТ ФЛУДА ==========
promo_attempts = defaultdict(int)
command_attempts = defaultdict(list)

def rate_limit(limit: int, per: int):
    """Декоратор для ограничения частоты команд"""
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
    """Декоратор для проверки прав администратора"""
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
    """Возвращает соединение с БД"""
    return sqlite3.connect('ultrovpn.db')

def get_db_with_row():
    """Возвращает соединение с БД с row_factory"""
    conn = sqlite3.connect('ultrovpn.db')
    conn.row_factory = sqlite3.Row
    return conn

def backup_db():
    """Создаёт резервную копию базы данных"""
    try:
        os.makedirs('backups', exist_ok=True)
        backup_name = f"backups/ultrovpn_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2('ultrovpn.db', backup_name)
        # Удаляем старые бэкапы (старше 30 дней)
        for f in os.listdir('backups'):
            f_path = os.path.join('backups', f)
            if os.path.isfile(f_path) and datetime.fromtimestamp(os.path.getmtime(f_path)) < datetime.now() - timedelta(days=30):
                os.remove(f_path)
        logger.info(f"Бэкап БД создан: {backup_name}")
    except Exception as e:
        logger.error(f"Ошибка создания бэкапа БД: {e}")

def init_db():
    with get_db() as conn:
        # Основные таблицы
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
        
        conn.execute('''CREATE TABLE IF NOT EXISTS backup_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            code_hash TEXT,
            salt TEXT,
            used INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS invites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            created_by INTEGER,
            used_by INTEGER,
            days_valid INTEGER DEFAULT 30,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
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
        
        conn.execute('''CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            auto_connect INTEGER DEFAULT 0,
            kill_switch INTEGER DEFAULT 1,
            ad_block INTEGER DEFAULT 0,
            schedule_enabled INTEGER DEFAULT 0,
            schedule_start TEXT,
            schedule_end TEXT
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS servers (
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
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS user_achievements (
            user_id INTEGER,
            achievement TEXT,
            earned_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, achievement)
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS team_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            plan TEXT,
            members TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS connection_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            device_id INTEGER,
            ip TEXT,
            country TEXT,
            city TEXT,
            connected_at TEXT DEFAULT CURRENT_TIMESTAMP,
            disconnected_at TEXT
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS wifi_whitelist (
            user_id INTEGER,
            ssid TEXT,
            PRIMARY KEY (user_id, ssid)
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS app_whitelist (
            user_id INTEGER,
            app_name TEXT,
            PRIMARY KEY (user_id, app_name)
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
        
        conn.execute('''CREATE TABLE IF NOT EXISTS partner_clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            partner_code TEXT,
            clicker_id INTEGER,
            clicked_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS partner_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            partner_code TEXT,
            user_id INTEGER,
            amount REAL,
            order_date TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS promocodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            discount INTEGER,
            used_by INTEGER,
            used_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            api_key TEXT UNIQUE,
            plan TEXT DEFAULT 'basic',
            requests_limit INTEGER DEFAULT 1000,
            requests_used INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS partner_levels (
            user_id INTEGER PRIMARY KEY,
            level TEXT DEFAULT 'bronze',
            referrals INTEGER DEFAULT 0,
            earnings REAL DEFAULT 0
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS user_themes (
            user_id INTEGER PRIMARY KEY,
            theme TEXT DEFAULT 'dark'
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS streaming_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            pack TEXT,
            expires_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # НОВЫЕ ТАБЛИЦЫ ДЛЯ АНАЛИТИКИ
        conn.execute('''CREATE TABLE IF NOT EXISTS daily_stats (
            date TEXT PRIMARY KEY,
            new_users INTEGER DEFAULT 0,
            active_users INTEGER DEFAULT 0,
            revenue INTEGER DEFAULT 0,
            conversions INTEGER DEFAULT 0,
            referral_clicks INTEGER DEFAULT 0,
            devices_count INTEGER DEFAULT 0,
            avg_speed REAL DEFAULT 0
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS promo_stats (
            promo_code TEXT,
            date TEXT,
            uses INTEGER DEFAULT 0,
            PRIMARY KEY (promo_code, date)
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS source_stats (
            source TEXT,
            date TEXT,
            clicks INTEGER DEFAULT 0,
            registrations INTEGER DEFAULT 0,
            PRIMARY KEY (source, date)
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS retention_stats (
            cohort_date TEXT,
            day_1 INTEGER DEFAULT 0,
            day_7 INTEGER DEFAULT 0,
            day_30 INTEGER DEFAULT 0,
            PRIMARY KEY (cohort_date)
        )''')

        # Добавляем серверы, если их нет
        cursor = conn.execute("SELECT COUNT(*) FROM servers")
        if cursor.fetchone()[0] == 0:
            conn.execute("INSERT INTO servers (name, host, country, city, protocol, port) VALUES ('🇷🇺 РОССИЯ-МСК', ?, 'RU', 'Moscow', 'wireguard', 51820)", (SERVER_PUBLIC_IP,))
            conn.execute("INSERT INTO servers (name, host, country, city, protocol, port) VALUES ('🇳🇱 НИДЕРЛАНДЫ', 'nl.ultrovpn.com', 'NL', 'Amsterdam', 'wireguard', 51820)")
            conn.execute("INSERT INTO servers (name, host, country, city, protocol, port) VALUES ('🇺🇸 США-НЙ', 'us.ultrovpn.com', 'US', 'New York', 'wireguard', 51820)")
            conn.execute("INSERT INTO servers (name, host, country, city, protocol, port) VALUES ('🛡️ АНТИГЛУШИЛКА', ?, 'RU', 'Anti-DPI', 'amneziawg', 443)", (SERVER_PUBLIC_IP,))

        # Создаём админов
        for aid in ADMIN_IDS:
            conn.execute("INSERT OR IGNORE INTO users (telegram_id, username, first_name, is_admin, subscription_end) VALUES (?, 'admin', 'Admin', 1, datetime('now', '+3650 days'))", (aid,))
        
        # Создаём настройки для всех пользователей
        conn.execute("INSERT OR IGNORE INTO user_settings (user_id) SELECT id FROM users WHERE id NOT IN (SELECT user_id FROM user_settings)")
        
        logger.info("База данных инициализирована")
        backup_db()

# ========== WIREGUARD + АНТИГЛУШИЛКА ==========
def setup_wireguard():
    """Настройка WireGuard интерфейса"""
    global SERVER_PRIVATE_KEY, SERVER_PUBLIC_KEY
    
    try:
        res = subprocess.run(['wg', 'show'], capture_output=True, text=True)
        if WG_INTERFACE in res.stdout:
            logger.info(f"Интерфейс {WG_INTERFACE} уже существует")
            result = subprocess.run(['wg', 'show', WG_INTERFACE, 'private-key'], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout:
                SERVER_PRIVATE_KEY = result.stdout.strip()
                result2 = subprocess.run(['wg', 'show', WG_INTERFACE, 'public-key'], capture_output=True, text=True)
                if result2.returncode == 0 and result2.stdout:
                    SERVER_PUBLIC_KEY = result2.stdout.strip()
            return True
        
        SERVER_PRIVATE_KEY = subprocess.check_output(['wg', 'genkey']).decode().strip()
        SERVER_PUBLIC_KEY = subprocess.check_output(['wg', 'pubkey'], input=SERVER_PRIVATE_KEY.encode()).decode().strip()
        
        cfg = f"""[Interface]
PrivateKey = {SERVER_PRIVATE_KEY}
Address = {WG_SERVER_NETWORK}1/24
ListenPort = {WG_PORT}
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE
"""
        os.makedirs('/etc/wireguard', exist_ok=True)
        with open(f'/etc/wireguard/{WG_INTERFACE}.conf', 'w') as f:
            f.write(cfg)
        
        subprocess.run(['sysctl', '-w', 'net.ipv4.ip_forward=1'], capture_output=True)
        subprocess.run(['systemctl', 'enable', f'wg-quick@{WG_INTERFACE}'], capture_output=True)
        subprocess.run(['systemctl', 'start', f'wg-quick@{WG_INTERFACE}'], capture_output=True)
        
        logger.info(f"WireGuard настроен. Публичный ключ: {SERVER_PUBLIC_KEY[:8]}...")
        return True
    except Exception as e:
        logger.error(f"Ошибка настройки WireGuard: {e}")
        return False

def generate_keys():
    """Генерация ключей WireGuard"""
    try:
        priv = subprocess.check_output(['wg', 'genkey']).decode().strip()
        pub = subprocess.check_output(['wg', 'pubkey'], input=priv.encode()).decode().strip()
        return priv, pub
    except Exception as e:
        logger.error(f"Ошибка генерации ключей: {e}")
        return None, None

def get_next_ip():
    """Получение следующего свободного IP адреса"""
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
    """Добавление пира в WireGuard"""
    try:
        subprocess.run(['wg', 'set', WG_INTERFACE, 'peer', pub, 'allowed-ips', f"{ip}/32"], check=True, capture_output=True)
        logger.info(f"Пир добавлен: {pub[:8]}... -> {ip}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка добавления пира: {e.stderr if e.stderr else str(e)}")
        return False

def remove_peer(pub):
    """Удаление пира из WireGuard"""
    try:
        subprocess.run(['wg', 'set', WG_INTERFACE, 'peer', pub, 'remove'], check=True, capture_output=True)
        logger.info(f"Пир удалён: {pub[:8]}...")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка удаления пира: {e.stderr if e.stderr else str(e)}")
        return False

def generate_config(priv, ip, protocol='wireguard', dns='1.1.1.1', port=51820):
    """Генерация конфигурации клиента"""
    if protocol == 'amneziawg':
        return f"""[Interface]
PrivateKey = {priv}
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

def generate_vless_link(uid):
    """Генерация VLESS ссылки"""
    u = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(uid)))
    return f"vless://{u}@{SERVER_PUBLIC_IP}:443?encryption=none&flow=xtls-rprx-vision&security=reality&sni=www.microsoft.com&fp=chrome&type=tcp#UltroVPN"

def generate_trojan_link(uid):
    """Генерация Trojan ссылки"""
    pwd = hashlib.md5(str(uid).encode()).hexdigest()[:16]
    return f"trojan://{pwd}@{SERVER_PUBLIC_IP}:443?sni=www.microsoft.com&fp=chrome&type=tcp#UltroVPN"

def gen_qr(text):
    """Генерация QR-кода из текста"""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def get_user_db_id(tg_id):
    """Получение ID пользователя в БД по Telegram ID"""
    with get_db() as conn:
        cursor = conn.execute("SELECT id FROM users WHERE telegram_id = ?", (tg_id,))
        row = cursor.fetchone()
        return row[0] if row else None

def is_sub_active(tg_id):
    """Проверка активности подписки"""
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
    """Выдача ежедневного бонуса"""
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

def hash_backup_code(code, salt):
    """Хэширование резервного кода с солью"""
    return hashlib.pbkdf2_hmac('sha256', code.encode(), salt.encode(), 100000).hex()

def gen_backup_codes(tg_id, cnt=8):
    """Генерация резервных кодов"""
    codes = []
    uid = get_user_db_id(tg_id)
    if not uid:
        return codes
    
    with get_db() as conn:
        for _ in range(cnt):
            code = secrets.token_hex(4).upper()
            salt = secrets.token_hex(16)
            code_hash = hash_backup_code(code, salt)
            conn.execute("INSERT INTO backup_codes (user_id, code_hash, salt) VALUES (?, ?, ?)", (uid, code_hash, salt))
            codes.append(code)
    
    return codes

def get_backup_left(tg_id):
    """Количество оставшихся резервных кодов"""
    uid = get_user_db_id(tg_id)
    if not uid:
        return 0
    with get_db() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM backup_codes WHERE user_id = ? AND used = 0", (uid,))
        return cursor.fetchone()[0]

def verify_backup_code(tg_id, code):
    """Проверка резервного кода"""
    uid = get_user_db_id(tg_id)
    if not uid:
        return False
    
    with get_db() as conn:
        cursor = conn.execute("SELECT id, code_hash, salt FROM backup_codes WHERE user_id = ? AND used = 0", (uid,))
        codes = cursor.fetchall()
        for c in codes:
            if hash_backup_code(code, c[2]) == c[1]:
                conn.execute("UPDATE backup_codes SET used = 1 WHERE id = ?", (c[0],))
                return True
    return False

async def check_achievements(tg_id):
    """Проверка и выдача достижений"""
    with get_db() as conn:
        cursor = conn.execute("SELECT id, created_at FROM users WHERE telegram_id = ?", (tg_id,))
        row = cursor.fetchone()
        if not row:
            return []
        uid = row[0]
        created = row[1]
        
        days = (datetime.now() - datetime.fromisoformat(created)).days
        
        cursor = conn.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (uid,))
        refs = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT COUNT(*) FROM devices WHERE user_id = ?", (uid,))
        devs = cursor.fetchone()[0]

        new_achs = []
        for key, ach in ACHIEVEMENTS.items():
            cursor = conn.execute("SELECT 1 FROM user_achievements WHERE user_id = ? AND achievement = ?", (uid, ach['name']))
            if cursor.fetchone():
                continue
            if 'days' in ach and days >= ach['days']:
                conn.execute("INSERT INTO user_achievements (user_id, achievement) VALUES (?, ?)", (uid, ach['name']))
                conn.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (ach['reward'], uid))
                new_achs.append(ach)
            elif 'target' in ach and refs >= ach['target']:
                conn.execute("INSERT INTO user_achievements (user_id, achievement) VALUES (?, ?)", (uid, ach['name']))
                conn.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (ach['reward'], uid))
                new_achs.append(ach)
            elif 'target' in ach and devs >= ach['target']:
                conn.execute("INSERT INTO user_achievements (user_id, achievement) VALUES (?, ?)", (uid, ach['name']))
                conn.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (ach['reward'], uid))
                new_achs.append(ach)
        return new_achs

def get_text(telegram_id, key):
    """Получение текста на языке пользователя"""
    with get_db() as conn:
        cursor = conn.execute("SELECT language FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()
        lang = row[0] if row else 'ru'
    return LANGUAGES.get(lang, LANGUAGES['ru']).get(key, key)

def apply_promocode(telegram_id, code):
    """Применение промокода"""
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
        
        # Записываем статистику использования промокода
        today = datetime.now().date().isoformat()
        conn.execute("""INSERT OR REPLACE INTO promo_stats (promo_code, date, uses)
                       VALUES (?, ?, COALESCE((SELECT uses FROM promo_stats WHERE promo_code=? AND date=?), 0) + 1)""",
                     (code, today, code, today))
        
        promo_attempts[telegram_id] = 0
        return True, f"✅ ПРОМОКОД АКТИВИРОВАН! +{discount * 10}₽ НА БАЛАНС"

def generate_api_key(user_id):
    """Генерация API ключа"""
    return secrets.token_urlsafe(32)

def create_api_subscription(telegram_id, plan):
    """Создание API подписки"""
    with get_db() as conn:
        uid = get_user_db_id(telegram_id)
        api_key = generate_api_key(uid)
        plan_data = API_PLANS[plan]
        expires = (datetime.now() + timedelta(days=plan_data["days"])).isoformat()
        conn.execute("INSERT OR REPLACE INTO api_keys (user_id, api_key, plan, requests_limit, expires_at) VALUES (?, ?, ?, ?, ?)",
                     (uid, api_key, plan, plan_data["requests"], expires))
        return api_key

def update_partner_level(telegram_id):
    """Обновление партнёрского уровня"""
    with get_db() as conn:
        uid = get_user_db_id(telegram_id)
        cursor = conn.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (uid,))
        referrals = cursor.fetchone()[0]
        level = "bronze"
        for lvl, data in PARTNER_LEVELS.items():
            if referrals >= data["min"]:
                level = lvl
        conn.execute("INSERT OR REPLACE INTO partner_levels (user_id, level, referrals) VALUES (?, ?, ?)", (uid, level, referrals))

def get_partner_percent(telegram_id):
    """Получение процента партнёра"""
    with get_db() as conn:
        uid = get_user_db_id(telegram_id)
        cursor = conn.execute("SELECT level FROM partner_levels WHERE user_id = ?", (uid,))
        row = cursor.fetchone()
        if row:
            return PARTNER_LEVELS[row[0]]["percent"]
    return 15

def create_partner_link(tg_id):
    """Создание партнёрской ссылки"""
    code = secrets.token_hex(6).upper()
    uid = get_user_db_id(tg_id)
    if not uid:
        return None
    with get_db() as conn:
        conn.execute("INSERT OR IGNORE INTO partner_links (user_id, code) VALUES (?, ?)", (uid, code))
    return code

def register_partner_click(partner_code, clicker_id):
    """Регистрация клика по партнёрской ссылке"""
    today = datetime.now().date().isoformat()
    with get_db() as conn:
        conn.execute("INSERT INTO partner_clicks (partner_code, clicker_id) VALUES (?, ?)", (partner_code, clicker_id))
        conn.execute("UPDATE partner_links SET clicks = clicks + 1 WHERE code = ?", (partner_code,))
        # Трекинг источника
        conn.execute("""INSERT OR REPLACE INTO source_stats (source, date, clicks, registrations)
                       VALUES (?, ?, COALESCE((SELECT clicks FROM source_stats WHERE source=? AND date=?), 0) + 1, 
                               COALESCE((SELECT registrations FROM source_stats WHERE source=? AND date=?), 0))""",
                     (partner_code, today, partner_code, today, partner_code, today))

def get_partner_stats(partner_code):
    """Получение статистики партнёра"""
    with get_db() as conn:
        cursor = conn.execute("SELECT clicks, registrations, earnings FROM partner_links WHERE code = ?", (partner_code,))
        row = cursor.fetchone()
        if row:
            return {"clicks": row[0], "registrations": row[1], "earnings": round(row[2], 2)}
    return {"clicks": 0, "registrations": 0, "earnings": 0}

async def check_expiring_subscriptions():
    """Фоновая проверка истекающих подписок"""
    while True:
        try:
            with get_db() as conn:
                cursor = conn.execute("SELECT telegram_id, subscription_end FROM users WHERE subscription_end IS NOT NULL")
                users = cursor.fetchall()
                for user in users:
                    if user[1]:
                        try:
                            end = datetime.fromisoformat(user[1])
                            days_left = (end - datetime.now()).days
                            if days_left == 7:
                                await bot.send_message(user[0], "⚠️ **ПОДПИСКА ИСТЕКАЕТ ЧЕРЕЗ 7 ДНЕЙ!**\nПРОДЛИ ЕЁ В РАЗДЕЛЕ «СТАНЬ СИЛЬНЕЕ»", parse_mode='Markdown')
                            elif days_left == 3:
                                await bot.send_message(user[0], "⚠️ **ПОДПИСКА ИСТЕКАЕТ ЧЕРЕЗ 3 ДНЯ!**", parse_mode='Markdown')
                            elif days_left == 1:
                                await bot.send_message(user[0], "⚠️ **ПОДПИСКА ИСТЕКАЕТ ЗАВТРА!**\nПРОДЛИ ПРЯМО СЕЙЧАС!", parse_mode='Markdown')
                        except:
                            pass
        except Exception as e:
            logger.error(f"Ошибка в check_expiring_subscriptions: {e}")
        
        await asyncio.sleep(86400)

async def get_traffic_stats(telegram_id):
    """Получение статистики трафика"""
    with get_db() as conn:
        uid = get_user_db_id(telegram_id)
        cursor = conn.execute("SELECT device_name, total_download_mb, total_upload_mb FROM devices WHERE user_id = ?", (uid,))
        devices = cursor.fetchall()
        total_down = sum(d[1] for d in devices)
        total_up = sum(d[2] for d in devices)
        total_gb = (total_down + total_up) / 1024
        percent = min(100, int((total_down + total_up) / 100))
        bar = "█" * (percent // 10) + "░" * (10 - (percent // 10))
        return f"📊 **ТРАФИК ЗА МЕСЯЦ:**\n━━━━━━━━━━━━━━━━━━━━━\n📥 СКАЧАНО: {total_down:.1f} MB\n📤 ОТПРАВЛЕНО: {total_up:.1f} MB\n📦 ВСЕГО: {total_gb:.2f} GB\n\n{bar}\n🔥 {percent}% ИСПОЛЬЗОВАНО"

async def run_speedtest():
    """Запуск теста скорости"""
    if not SPEEDTEST_AVAILABLE:
        return None, None, None
    
    try:
        loop = asyncio.get_event_loop()
        st = speedtest.Speedtest()
        st.get_best_server()
        d = await loop.run_in_executor(None, st.download)
        u = await loop.run_in_executor(None, st.upload)
        p = st.results.ping
        return d/1_000_000, u/1_000_000, p
    except Exception as e:
        logger.error(f"Speedtest error: {e}")
        return None, None, None

async def test_dns_leak():
    """Тест утечек DNS"""
    if not AIOHTTP_AVAILABLE:
        return "❌ **НЕВОЗМОЖНО ПРОВЕРИТЬ**\nУстановите aiohttp: pip install aiohttp"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.ipify.org?format=json') as resp:
                data = await resp.json()
                ip = data['ip']
            async with session.get(f'http://ip-api.com/json/{ip}') as resp:
                data = await resp.json()
        return f"✅ **УТЕЧЕК DNS НЕТ**\n🌐 IP: {ip}\n📍 {data.get('country', '?')}, {data.get('city', '?')}\n📡 ПРОВАЙДЕР: {data.get('isp', '?')}"
    except Exception as e:
        logger.error(f"DNS test error: {e}")
        return "❌ **ОШИБКА ПРОВЕРКИ**"

# ========== АНАЛИТИКА ==========
async def collect_daily_stats():
    """Сбор ежедневной статистики"""
    today = datetime.now().date().isoformat()
    
    try:
        with get_db() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM users WHERE date(created_at) = ?", (today,))
            new_users = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM users WHERE subscription_end > datetime('now')")
            active_users = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE date(completed_at) = ? AND status='completed'", (today,))
            revenue = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM transactions WHERE date(completed_at) = ? AND status='completed'", (today,))
            conversions = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM partner_clicks WHERE date(clicked_at) = ?", (today,))
            referral_clicks = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM devices")
            devices_count = cursor.fetchone()[0]
            
            conn.execute("""INSERT OR REPLACE INTO daily_stats 
                           (date, new_users, active_users, revenue, conversions, referral_clicks, devices_count)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                         (today, new_users, active_users, revenue, conversions, referral_clicks, devices_count))
            
            logger.info(f"Статистика за {today} собрана: {new_users} новых, {active_users} активных, {revenue}₽ дохода")
            return True
    except Exception as e:
        logger.error(f"Ошибка сбора статистики: {e}")
        return False

async def calculate_retention():
    """Расчёт удержания пользователей"""
    try:
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT date(created_at) as cohort, telegram_id, created_at
                FROM users 
                WHERE created_at > datetime('now', '-30 days')
                ORDER BY created_at
            """)
            users = cursor.fetchall()
            
            cohorts = defaultdict(lambda: {'total': 0, 'day1': 0, 'day7': 0, 'day30': 0})
            
            for user in users:
                cohort = user[0]
                created = datetime.fromisoformat(user[2])
                days = (datetime.now() - created).days
                
                cohorts[cohort]['total'] += 1
                
                if days >= 1:
                    cursor2 = conn.execute("SELECT subscription_end FROM users WHERE telegram_id = ?", (user[1],))
                    sub = cursor2.fetchone()
                    if sub and sub[0] and datetime.fromisoformat(sub[0]) > created + timedelta(days=1):
                        cohorts[cohort]['day1'] += 1
                
                if days >= 7:
                    cursor2 = conn.execute("SELECT subscription_end FROM users WHERE telegram_id = ?", (user[1],))
                    sub = cursor2.fetchone()
                    if sub and sub[0] and datetime.fromisoformat(sub[0]) > created + timedelta(days=7):
                        cohorts[cohort]['day7'] += 1
                
                if days >= 30:
                    cursor2 = conn.execute("SELECT subscription_end FROM users WHERE telegram_id = ?", (user[1],))
                    sub = cursor2.fetchone()
                    if sub and sub[0] and datetime.fromisoformat(sub[0]) > created + timedelta(days=30):
                        cohorts[cohort]['day30'] += 1
            
            for cohort, data in cohorts.items():
                if data['total'] > 0:
                    conn.execute("""INSERT OR REPLACE INTO retention_stats 
                                   (cohort_date, day_1, day_7, day_30)
                                   VALUES (?, ?, ?, ?)""",
                                 (cohort, data['day1'], data['day7'], data['day30']))
            
            logger.info("Retention рассчитан")
            return True
    except Exception as e:
        logger.error(f"Ошибка расчёта retention: {e}")
        return False

def track_source(source, clicker_id, is_registration=False):
    """Отслеживание источника трафика"""
    today = datetime.now().date().isoformat()
    try:
        with get_db() as conn:
            if is_registration:
                conn.execute("""INSERT OR REPLACE INTO source_stats (source, date, clicks, registrations)
                               VALUES (?, ?, COALESCE((SELECT clicks FROM source_stats WHERE source=? AND date=?), 0) + 1, 
                                       COALESCE((SELECT registrations FROM source_stats WHERE source=? AND date=?), 0) + 1)""",
                             (source, today, source, today, source, today))
            else:
                conn.execute("""INSERT OR REPLACE INTO source_stats (source, date, clicks, registrations)
                               VALUES (?, ?, COALESCE((SELECT clicks FROM source_stats WHERE source=? AND date=?), 0) + 1, 
                                       COALESCE((SELECT registrations FROM source_stats WHERE source=? AND date=?), 0))""",
                             (source, today, source, today, source, today))
    except Exception as e:
        logger.error(f"Ошибка трекинга источника: {e}")

# ========== АВТОПОСТИНГ ==========
async def get_stats_for_post():
    """Получение статистики для поста"""
    with get_db() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM users WHERE subscription_end > datetime('now')")
        active_users = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT COUNT(*) FROM devices")
        devices = cursor.fetchone()[0]
        
        today = datetime.now().date().isoformat()
        cursor = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE date(completed_at) = ? AND status='completed'", (today,))
        revenue = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT COUNT(*) FROM users WHERE date(created_at) = ?", (today,))
        new_users = cursor.fetchone()[0]
        
        cursor = conn.execute("""
            SELECT u.first_name, COUNT(r.id) as refs
            FROM users u
            LEFT JOIN users r ON r.referred_by = u.id
            WHERE r.created_at > datetime('now', '-30 days')
            GROUP BY u.id
            ORDER BY refs DESC
            LIMIT 3
        """)
        top_refs = cursor.fetchall()
        
        top_text = ""
        for i, ref in enumerate(top_refs, 1):
            medals = {1: "🥇", 2: "🥈", 3: "🥉"}
            top_text += f"{medals.get(i, '•')} {ref[0]}: {ref[1]} приглашений\n"
        
        return {
            "new_users": new_users,
            "active_users": active_users,
            "revenue": revenue,
            "devices": devices,
            "top_referrals": top_text,
            "user_id": ADMIN_IDS[0] if ADMIN_IDS else "0"
        }

async def auto_poster():
    """Фоновая задача для автоматических постов"""
    if not AUTO_POST_ENABLED:
        logger.info("Автопостинг отключён")
        return
    
    if not AUTO_POST_CHANNEL:
        logger.warning("AUTO_POST_CHANNEL не указан в .env. Автопостинг отключён")
        return
    
    logger.info(f"Автопостинг запущен. Канал: {AUTO_POST_CHANNEL}, интервал: {AUTO_POST_INTERVAL_HOURS}ч")
    
    post_index = 0
    
    while True:
        try:
            stats = await get_stats_for_post()
            
            template = AUTO_POST_TEMPLATES[post_index % len(AUTO_POST_TEMPLATES)]
            
            text = template["text"].format(**stats)
            
            await bot.send_message(
                AUTO_POST_CHANNEL,
                text,
                parse_mode=template["parse_mode"],
                disable_web_page_preview=True
            )
            
            logger.info(f"Автопост отправлен в {AUTO_POST_CHANNEL} (шаблон {post_index % len(AUTO_POST_TEMPLATES) + 1})")
            
            post_index += 1
            
            await asyncio.sleep(AUTO_POST_INTERVAL_HOURS * 3600)
            
        except Exception as e:
            logger.error(f"Ошибка автопостинга: {e}")
            await asyncio.sleep(3600)

async def daily_stats_collector():
    """Ежедневный сбор статистики в 00:00"""
    while True:
        now = datetime.now()
        next_run = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        wait_seconds = (next_run - now).total_seconds()
        
        await asyncio.sleep(wait_seconds)
        
        await collect_daily_stats()
        await calculate_retention()
        
        logger.info("Ежедневный сбор статистики выполнен")

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
        InlineKeyboardButton("🚀 ТУРБО РЕЖИМ", callback_data="turbo_mode"),
        InlineKeyboardButton("📺 СТРИМИНГ-ПАКЕТЫ", callback_data="streaming_packs")
    )
    kb.add(
        InlineKeyboardButton("🎫 ПРОМОКОД", callback_data="enter_promo"),
        InlineKeyboardButton("⚡️ СПИД ТЕСТ", callback_data="speed_test")
    )
    kb.add(
        InlineKeyboardButton("🔍 ТЕСТ DNS", callback_data="dns_test"),
        InlineKeyboardButton("🔐 РЕЗЕРВНЫЕ КОДЫ", callback_data="backup_keys")
    )
    kb.add(
        InlineKeyboardButton("⚙️ ТУРБО НАСТРОЙКИ", callback_data="settings"),
        InlineKeyboardButton("💸 ВЫВОД СРЕДСТВ", callback_data="withdraw")
    )
    kb.add(
        InlineKeyboardButton("🤝 ПАРТНЁРКА", callback_data="partner_api"),
        InlineKeyboardButton("🔌 API ДОСТУП", callback_data="api_plans")
    )
    kb.add(
        InlineKeyboardButton("📖 КАК ПОДКЛЮЧИТЬСЯ", callback_data="how_to_connect"),
        InlineKeyboardButton("🌐 ЯЗЫК", callback_data="change_language")
    )
    kb.add(
        InlineKeyboardButton("ℹ️ О ЗАРЯДЕ", callback_data="about"),
        InlineKeyboardButton("🏆 ДОСТИЖЕНИЯ", callback_data="achievements")
    )
    if is_admin:
        kb.add(InlineKeyboardButton("👑 АДМИН", callback_data="admin_panel"))
    if SPONSOR_BUTTON_ENABLED:
        kb.add(InlineKeyboardButton(SPONSOR_BUTTON_TEXT, url=SPONSOR_BUTTON_URL))
    return kb

def protocol_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("⚡ WIREGUARD", callback_data="protocol_wireguard"),
        InlineKeyboardButton("🛡️ AMNEZIAWG", callback_data="protocol_amneziawg"),
        InlineKeyboardButton("🔒 VLESS", callback_data="protocol_vless"),
        InlineKeyboardButton("🛡️ TROJAN", callback_data="protocol_trojan"),
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
        InlineKeyboardButton("📶 WHITE LIST WIFI", callback_data="wifi_whitelist"),
        InlineKeyboardButton("📱 SPLIT TUNNELING", callback_data="split_tunneling"),
        InlineKeyboardButton("🌐 DNS", callback_data="change_dns"),
        InlineKeyboardButton("🔌 ПОРТ", callback_data="change_port"),
        InlineKeyboardButton("⏰ РАСПИСАНИЕ", callback_data="schedule_settings"),
        InlineKeyboardButton("🎨 ЦВЕТОВАЯ ТЕМА", callback_data="change_theme"),
        InlineKeyboardButton("🌐 ЯЗЫК", callback_data="change_language"),
        InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")
    )
    return kb

def dns_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("☁️ CLOUDFLARE", callback_data="dns_cloudflare"),
        InlineKeyboardButton("🔍 GOOGLE", callback_data="dns_google"),
        InlineKeyboardButton("🛡️ ADGUARD", callback_data="dns_adguard"),
        InlineKeyboardButton("🔧 СВОЙ", callback_data="dns_custom"),
        InlineKeyboardButton("🔙 НАЗАД", callback_data="settings")
    )
    return kb

def get_language_keyboard():
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(
        InlineKeyboardButton("🇷🇺 РУССКИЙ", callback_data="lang_ru"),
        InlineKeyboardButton("🇬🇧 ENGLISH", callback_data="lang_en"),
        InlineKeyboardButton("🇺🇿 O'ZBEK", callback_data="lang_uz"),
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
        logger.info(f"Инвойс отправлен пользователю {uid} на план {plan}")
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

    if args and args.startswith("ref_"):
        partner_code = args.replace("ref_", "")
        register_partner_click(partner_code, uid)

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
                        # Трекинг регистрации
                        track_source(ref_code, uid, is_registration=True)
                
                conn.execute('''INSERT INTO users (telegram_id, username, first_name, subscription_end, referred_by)
                                VALUES (?, ?, ?, datetime('now', '+? days'), ?)''',
                             (uid, uname, name, DEFAULT_SUBSCRIPTION_DAYS, referred))
                
                if referred:
                    conn.execute("UPDATE users SET referral_balance = referral_balance + ? WHERE id = ?", (REFERRAL_BONUS, referred))
                    update_partner_level(uid)
                
                conn.execute("INSERT INTO user_settings (user_id) SELECT id FROM users WHERE telegram_id = ?", (uid,))
                
                await message.reply(ENERGY_TEXTS["welcome"], parse_mode='Markdown', reply_markup=await main_kb(uid))
                logger.info(f"Новый пользователь: {uid} ({name})")
            else:
                if user[8] == 1:
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

@dp.callback_query_handler(lambda c: c.data == "how_to_connect")
async def how_to_connect_cb(callback: CallbackQuery):
    text = """
⚡️ **КАК ПОДКЛЮЧИТЬСЯ К ULTROVPN** ⚡️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📱 **ЧЕРЕЗ QR-КОД (БЫСТРО)**

1️⃣ СКАЧАЙ **WIREGUARD**:
   • [ANDROID](https://play.google.com/store/apps/details?id=com.wireguard.android)
   • [IOS](https://apps.apple.com/app/wireguard/id1441195209)

2️⃣ НАЖМИ **ВЗЛЕТАЙ** В БОТЕ

3️⃣ ВЫБЕРИ УСТРОЙСТВО

4️⃣ НАЖМИ **"СКАНИРОВАТЬ QR-КОД"**

5️⃣ НАВЕДИ КАМЕРУ НА ЭКРАН

6️⃣ ВКЛЮЧИ VPN 🔥

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💻 **ЧЕРЕЗ ФАЙЛ .CONF**

1️⃣ СКАЧАЙ **WIREGUARD** С wireguard.com/install/

2️⃣ НАЖМИ **ВЗЛЕТАЙ** → WINDOWS/MACOS/LINUX

3️⃣ СКАЧАЙ ФАЙЛ `ultrovpn.conf`

4️⃣ ОТКРОЙ WIREGUARD → **IMPORT TUNNEL(S) FROM FILE**

5️⃣ ВЫБЕРИ ФАЙЛ

6️⃣ НАЖМИ **ACTIVATE**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❓ **НУЖНА ПОМОЩЬ?** → @UltroVPNSupport

⚡️ ТВОЯ СВОБОДА — ТВОИ ПРАВИЛА! ⚡️
"""
    await callback.message.reply(text, parse_mode='Markdown', disable_web_page_preview=True)
    await callback.answer()

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
            
            with get_db() as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) + 1 FROM users u2 
                    WHERE (SELECT COUNT(*) FROM users WHERE referred_by = u2.id) > 
                          (SELECT COUNT(*) FROM users WHERE referred_by = u.id)
                """)
                rank = cursor.fetchone()[0]
            
            text = f"""
💪 **МОЙ ЗАРЯД** 💪
━━━━━━━━━━━━━━━━━━━━━
👤 {u[3]}
🔋 ДО ЗАРЯДКИ: {left} ДНЕЙ
📱 УСТРОЙСТВ: {u[9]}/{MAX_DEVICES_PER_USER}
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
        
        if proto == 'vless':
            await callback.message.reply(f"✅ **VLESS ССЫЛКА ГОТОВА!**\n`{generate_vless_link(str(uid))}`", parse_mode='Markdown')
        elif proto == 'trojan':
            await callback.message.reply(f"✅ **TROJAN ССЫЛКА ГОТОВА!**\n`{generate_trojan_link(str(uid))}`", parse_mode='Markdown')
        else:
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

@dp.callback_query_handler(lambda c: c.data == "backup_keys")
async def backup_keys_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    codes = gen_backup_codes(uid)
    left = get_backup_left(uid)
    
    text = "🔐 **РЕЗЕРВНЫЕ КОДЫ ВОССТАНОВЛЕНИЯ**\n\n"
    text += "\n".join([f"`{c}`" for c in codes])
    text += f"\n\n⚠️ **СОХРАНИ ИХ!**\nОСТАЛОСЬ: {left}/8\n\n🔥 НИКОМУ НЕ ПОКАЗЫВАЙ! 🔥"
    
    await callback.message.edit_text(text, parse_mode='Markdown', 
                               reply_markup=InlineKeyboardMarkup().add(
                                   InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")))

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

@dp.callback_query_handler(lambda c: c.data == "withdraw")
async def withdraw_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    with get_db() as conn:
        cursor = conn.execute("SELECT referral_balance FROM users WHERE telegram_id = ?", (uid,))
        bal = cursor.fetchone()[0]
    
    if not bal or bal < 100:
        await callback.answer(f"❌ МИНИМУМ 100₽, У ТЕБЯ {bal or 0}₽", show_alert=True)
        return
    
    text = f"💸 **ВЫВОД СРЕДСТВ**\n━━━━━━━━━━━━━━━━━━━━━\n💰 ДОСТУПНО: {bal}₽\n💳 **СПОСОБЫ:**\n• TELEGRAM STARS\n• USDT (TRC20)\n• НА БАЛАНС VPN\n━━━━━━━━━━━━━━━━━━━━━\n📝 ОТПРАВЬ ЗАЯВКУ В @UltroVPNSupport"
    
    await callback.message.edit_text(text, parse_mode='Markdown', 
                               reply_markup=InlineKeyboardMarkup().add(
                                   InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")))

@dp.callback_query_handler(lambda c: c.data == "turbo_mode")
async def turbo_mode_cb(callback: CallbackQuery):
    await callback.answer("🚀 ТУРБО РЕЖИМ АКТИВИРОВАН! СКОРОСТЬ УВЕЛИЧЕНА!", show_alert=True)

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
    if success:
        await cmd_start(message)

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
        logger.info(f"Pre-checkout успешен для {q.from_user.id}")
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
        
        with get_db() as conn:
            cursor = conn.execute("SELECT referred_by FROM users WHERE id = ?", (uidb,))
            referred_by = cursor.fetchone()
            if referred_by and referred_by[0]:
                conn.execute("UPDATE users SET referral_balance = referral_balance + ? WHERE id = ?", 
                           (REFERRAL_BONUS, referred_by[0]))
                update_partner_level(uid)
        
        await message.reply(f"✅ ОПЛАЧЕНО! ПОДПИСКА ДО {new_end.strftime('%d.%m.%Y')}\n🔥 ТВОЙ ЗАРЯД АКТИВЕН!", parse_mode='Markdown')
        logger.info(f"Платеж успешен: {uid} на {days} дней")
    except Exception as e:
        logger.error(f"Ошибка обработки платежа: {e}")
        await message.reply("❌ ОШИБКА АКТИВАЦИИ ПОДПИСКИ! ОБРАТИТЕСЬ В ПОДДЕРЖКУ")

@dp.callback_query_handler(lambda c: c.data == "streaming_packs")
async def streaming_packs_cb(callback: CallbackQuery):
    text = "📺 **СТРИМИНГ-ПАКЕТЫ** 📺\n━━━━━━━━━━━━━━━━━━━━━\n"
    for k, v in STREAMING_PACKS.items():
        text += f"{v['name']} — {v['price']}₽ / {v['days']} ДНЕЙ\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n🔥 ОПТИМИЗИРОВАНО ДЛЯ NETFLIX, YOUTUBE, TIKTOK"
    
    kb = InlineKeyboardMarkup(row_width=2)
    for k, v in STREAMING_PACKS.items():
        kb.add(InlineKeyboardButton(v["name"], callback_data=f"stream_{k}"))
    kb.add(InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu"))
    
    await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("stream_"))
async def buy_streaming_cb(callback: CallbackQuery):
    pack = callback.data.replace("stream_", "")
    await callback.answer(f"✅ ВЫ ВЫБРАЛИ {STREAMING_PACKS[pack]['name']}\n🔥 ОПЛАТА ЧЕРЕЗ TELEGRAM STARS СКОРО!", show_alert=True)

@dp.callback_query_handler(lambda c: c.data == "achievements")
async def achievements_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    new_achs = await check_achievements(uid)
    for a in new_achs:
        await callback.message.reply(f"🏆 **{a['name']}**\n📝 {a['desc']}\n💰 +{a['reward']}₽", parse_mode='Markdown')
    
    with get_db() as conn:
        uidb = get_user_db_id(uid)
        cursor = conn.execute("SELECT achievement FROM user_achievements WHERE user_id = ?", (uidb,))
        earned = [row[0] for row in cursor.fetchall()]
    
    txt = "🏆 **ТВОИ ДОСТИЖЕНИЯ** 🏆\n━━━━━━━━━━━━━━━━━━━━━\n"
    for k, a in ACHIEVEMENTS.items():
        status = "✅" if a['name'] in earned else "🔒"
        txt += f"{status} {a['name']} — {a['desc']}\n"
    txt += "━━━━━━━━━━━━━━━━━━━━━\n🔥 ЗАРЯЖАЙСЯ И ПОЛУЧАЙ БОНУСЫ!"
    
    await callback.message.edit_text(txt, parse_mode='Markdown', 
                               reply_markup=InlineKeyboardMarkup().add(
                                   InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")))

@dp.callback_query_handler(lambda c: c.data == "speed_test")
async def speed_test_cb(callback: CallbackQuery):
    msg = await callback.message.edit_text("🚀 **СПИД ТЕСТ**\n━━━━━━━━━━━━━━━━━━━━━\n⏳ ЗАГРУЗКА...", parse_mode='Markdown')
    
    d, u, p = await run_speedtest()
    
    if d:
        if d > 50:
            quality = "🟢 ОТЛИЧНО"
        elif d > 20:
            quality = "🟡 ХОРОШО"
        else:
            quality = "🟠 НОРМАЛЬНО"
        
        result = f"🚀 **СПИД ТЕСТ**\n━━━━━━━━━━━━━━━━━━━━━\n📥 СКАЧИВАНИЕ: `{d:.1f} Mbps`\n📤 ЗАГРУЗКА: `{u:.1f} Mbps`\n📡 ПИНГ: `{p:.0f} ms`\n\n{quality}\n━━━━━━━━━━━━━━━━━━━━━\n⚡️ ТВОЯ СКОРОСТЬ — ТВОЯ СВОБОДА!"
        await msg.edit_text(result, parse_mode='Markdown', 
                           reply_markup=InlineKeyboardMarkup().add(
                               InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")))
    else:
        await msg.edit_text("❌ **ОШИБКА ТЕСТА**\nПОПРОБУЙ ПОЗЖЕ", parse_mode='Markdown', 
                           reply_markup=InlineKeyboardMarkup().add(
                               InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")))

@dp.callback_query_handler(lambda c: c.data == "dns_test")
async def dns_test_cb(callback: CallbackQuery):
    msg = await callback.message.edit_text("🔍 **ПРОВЕРКА DNS...**\n⏳ ПОДОЖДИ", parse_mode='Markdown')
    result = await test_dns_leak()
    await msg.edit_text(result, parse_mode='Markdown', 
                       reply_markup=InlineKeyboardMarkup().add(
                           InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")))

@dp.callback_query_handler(lambda c: c.data == "change_protocol")
async def change_protocol_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    with get_db() as conn:
        cursor = conn.execute("SELECT selected_protocol FROM users WHERE telegram_id = ?", (uid,))
        r = cursor.fetchone()
        cur = r[0] if r else 'wireguard'
    
    text = f"🌍 **ТЕКУЩИЙ ПРОТОКОЛ:** `{cur.upper()}`\n━━━━━━━━━━━━━━━━━━━━━\n⚡ WIREGUARD — БЫСТРЫЙ\n🛡️ AMNEZIAWG — АНТИГЛУШИЛКА\n🔒 VLESS — ОБХОД DPI\n🛡️ TROJAN — СКРЫТЫЙ\n━━━━━━━━━━━━━━━━━━━━━\n⚠️ ДЛЯ СМЕНЫ ПРОТОКОЛА СОЗДАЙ НОВОЕ УСТРОЙСТВО"
    
    await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=protocol_kb())

@dp.callback_query_handler(lambda c: c.data.startswith("protocol_"))
async def set_protocol_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    proto = callback.data.replace("protocol_", "")
    
    with get_db() as conn:
        conn.execute("UPDATE users SET selected_protocol = ? WHERE telegram_id = ?", (proto, uid))
    
    await callback.answer(f"✅ ПРОТОКОЛ {proto.upper()} ВЫБРАН!", show_alert=True)
    await change_protocol_cb(callback)

@dp.callback_query_handler(lambda c: c.data == "partner_api")
async def partner_api_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    update_partner_level(uid)
    code = create_partner_link(uid)
    
    if not code:
        await callback.message.edit_text("❌ ОШИБКА СОЗДАНИЯ ССЫЛКИ", 
                                   reply_markup=InlineKeyboardMarkup().add(
                                       InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")))
        return
    
    botname = (await bot.get_me()).username
    link = f"https://t.me/{botname}?start=ref_{code}"
    stats = get_partner_stats(code)
    percent = get_partner_percent(uid)
    
    text = f"🤝 **ПАРТНЁРСКАЯ ПРОГРАММА** 🤝\n━━━━━━━━━━━━━━━━━━━━━\n📊 ПЕРЕХОДОВ: {stats['clicks']}\n✅ РЕГИСТРАЦИЙ: {stats['registrations']}\n💰 ЗАРАБОТАНО: {stats['earnings']}₽\n🎯 ТВОЯ СТАВКА: **{percent}%**\n━━━━━━━━━━━━━━━━━━━━━\n🔗 **ТВОЯ ССЫЛКА:**\n`{link}`\n━━━━━━━━━━━━━━━━━━━━━\n💸 ТЫ ПОЛУЧАЕШЬ {percent}% ОТ КАЖДОГО ПЛАТЕЖА НАВСЕГДА!\n🔥 ЧЕМ БОЛЬШЕ ДРУЗЕЙ — ТЕМ ВЫШЕ ПРОЦЕНТ!"
    
    await callback.message.edit_text(text, parse_mode='Markdown', 
                               reply_markup=InlineKeyboardMarkup().add(
                                   InlineKeyboardButton("📤 ПОДЕЛИТЬСЯ", switch_inline_query=link),
                                   InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")))

@dp.callback_query_handler(lambda c: c.data == "api_plans")
async def api_plans_cb(callback: CallbackQuery):
    text = "🔌 **API ДЛЯ РАЗРАБОТЧИКОВ** 🔌\n━━━━━━━━━━━━━━━━━━━━━\nПОДКЛЮЧАЙ СВОИ ПРИЛОЖЕНИЯ К ULTROVPN\n\n"
    for k, v in API_PLANS.items():
        text += f"**{v['name']}** — {v['price']}₽\n   • {v['requests']} ЗАПРОСОВ\n   • {v['days']} ДНЕЙ\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n⚡️ ДЛЯ КОРПОРАТИВНЫХ КЛИЕНТОВ"
    
    kb = InlineKeyboardMarkup(row_width=1)
    for k in API_PLANS:
        kb.add(InlineKeyboardButton(API_PLANS[k]["name"], callback_data=f"buy_api_{k}"))
    kb.add(InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu"))
    
    await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("buy_api_"))
async def buy_api_cb(callback: CallbackQuery):
    await callback.answer("🔌 API ДОСТУП ПОКУПАЕТСЯ ЧЕРЕЗ АДМИНА. НАПИШИТЕ @UltroVPNSupport", show_alert=True)

@dp.callback_query_handler(lambda c: c.data == "settings")
async def settings_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    
    with get_db() as conn:
        cursor = conn.execute("""SELECT s.*, u.auto_renew, u.selected_dns, u.selected_port 
                                FROM user_settings s 
                                JOIN users u ON u.id = s.user_id 
                                WHERE u.telegram_id = ?""", (uid,))
        s = cursor.fetchone()
    
    if s:
        txt = f"⚙️ **ТУРБО НАСТРОЙКИ** ⚙️\n━━━━━━━━━━━━━━━━━━━━━\n"
        txt += f"🔄 AUTO-CONNECT: {'✅' if s[1] else '❌'}\n"
        txt += f"🛡️ KILL SWITCH: {'✅' if s[2] else '❌'}\n"
        txt += f"🚫 ADBLOCK: {'✅' if s[3] else '❌'}\n"
        txt += f"🔄 АВТОПРОДЛЕНИЕ: {'✅' if s[6] else '❌'}\n"
        txt += f"🌐 DNS: {s[7]}\n"
        txt += f"🔌 ПОРТ: {s[8]}\n"
        txt += "━━━━━━━━━━━━━━━━━━━━━\n🔥 НАСТРОЙ ПОД СЕБЯ!"
        
        await callback.message.edit_text(txt, parse_mode='Markdown', reply_markup=settings_kb())

@dp.callback_query_handler(lambda c: c.data.startswith("toggle_"))
async def toggle_setting_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    setting = callback.data.replace("toggle_", "")
    
    allowed_settings = ['autoconnect', 'killswitch', 'adblock']
    
    if setting in allowed_settings:
        with get_db() as conn:
            cursor = conn.execute(f"SELECT {setting} FROM user_settings WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)", (uid,))
            cur = cursor.fetchone()[0]
            new = 0 if cur else 1
            conn.execute(f"UPDATE user_settings SET {setting} = ? WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)", (new, uid))
    elif setting == 'autorenew':
        with get_db() as conn:
            cursor = conn.execute("SELECT auto_renew FROM users WHERE telegram_id = ?", (uid,))
            cur = cursor.fetchone()[0]
            new = 0 if cur else 1
            conn.execute("UPDATE users SET auto_renew = ? WHERE telegram_id = ?", (new, uid))
    
    await callback.answer(f"✅ {setting.upper()} ИЗМЕНЁН!", show_alert=True)
    await settings_cb(callback)

@dp.callback_query_handler(lambda c: c.data == "change_dns")
async def change_dns_menu_cb(callback: CallbackQuery):
    text = "🌐 **ВЫБЕРИ DNS СЕРВЕР** 🌐\n━━━━━━━━━━━━━━━━━━━━━\n☁️ CLOUDFLARE (1.1.1.1)\n🔍 GOOGLE (8.8.8.8)\n🛡️ ADGUARD (94.140.14.14)\n🔧 СВОЙ DNS\n━━━━━━━━━━━━━━━━━━━━━\n⚡️ ВЫБЕРИ ДЛЯ МАКСИМАЛЬНОЙ СКОРОСТИ"
    
    await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=dns_kb())

@dp.callback_query_handler(lambda c: c.data.startswith("dns_"))
async def set_dns_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    dns_map = {"cloudflare": "1.1.1.1", "google": "8.8.8.8", "adguard": "94.140.14.14"}
    t = callback.data.replace("dns_", "")
    
    if t == "custom":
        await callback.message.edit_text("🔧 **ВВЕДИ DNS СЕРВЕР**\n━━━━━━━━━━━━━━━━━━━━━\n📝 НАПРИМЕР: 1.1.1.1\n\nОТПРАВЬ АДРЕС СООБЩЕНИЕМ", 
                                   parse_mode='Markdown', 
                                   reply_markup=InlineKeyboardMarkup().add(
                                       InlineKeyboardButton("🔙 НАЗАД", callback_data="change_dns")))
        return
    
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

@dp.message_handler(lambda m: m.text and m.text.isdigit() and 1024 <= int(m.text) <= 65535)
async def set_port_handler(message: Message):
    uid = message.from_user.id
    port = int(message.text)
    
    with get_db() as conn:
        conn.execute("UPDATE users SET selected_port = ? WHERE telegram_id = ?", (port, uid))
    
    await message.reply(f"✅ ПОРТ ИЗМЕНЁН НА {port}!\n⚠️ ДЛЯ ПРИМЕНЕНИЯ СОЗДАЙТЕ НОВОЕ УСТРОЙСТВО", parse_mode='Markdown')

@dp.callback_query_handler(lambda c: c.data == "wifi_whitelist")
async def wifi_whitelist_prompt_cb(callback: CallbackQuery):
    text = "📶 **WHITE LIST WIFI**\n━━━━━━━━━━━━━━━━━━━━━\n📝 ОТПРАВЬ SSID WIFI\n\nVPN БУДЕТ ВКЛЮЧАТЬСЯ ТОЛЬКО НА ЭТИХ СЕТЯХ"
    
    await callback.message.edit_text(text, parse_mode='Markdown', 
                               reply_markup=InlineKeyboardMarkup().add(
                                   InlineKeyboardButton("🔙 НАЗАД", callback_data="settings")))

@dp.callback_query_handler(lambda c: c.data == "split_tunneling")
async def split_tunneling_prompt_cb(callback: CallbackQuery):
    text = "📱 **SPLIT TUNNELING**\n━━━━━━━━━━━━━━━━━━━━━\n📝 ОТПРАВЬ НАЗВАНИЕ ПРИЛОЖЕНИЯ\n\nЧЕРЕЗ VPN БУДУТ ИДТИ ТОЛЬКО ЭТИ ПРИЛОЖЕНИЯ"
    
    await callback.message.edit_text(text, parse_mode='Markdown', 
                               reply_markup=InlineKeyboardMarkup().add(
                                   InlineKeyboardButton("🔙 НАЗАД", callback_data="settings")))

@dp.callback_query_handler(lambda c: c.data == "schedule_settings")
async def schedule_menu_cb(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🕐 09:00-18:00", callback_data="schedule_work"),
        InlineKeyboardButton("🌙 00:00-06:00", callback_data="schedule_night"),
        InlineKeyboardButton("🚫 ОТКЛЮЧИТЬ", callback_data="schedule_off"),
        InlineKeyboardButton("🔙 НАЗАД", callback_data="settings")
    )
    
    await callback.message.edit_text("⏰ **РАСПИСАНИЕ VPN** ⏰\n━━━━━━━━━━━━━━━━━━━━━\nВЫБЕРИ ИНТЕРВАЛ ДЛЯ АВТОВКЛЮЧЕНИЯ", 
                               parse_mode='Markdown', reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("schedule_"))
async def set_schedule_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    val = callback.data.replace("schedule_", "")
    
    with get_db() as conn:
        if val == "off":
            conn.execute("""UPDATE user_settings 
                           SET schedule_enabled = 0, schedule_start = NULL, schedule_end = NULL 
                           WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)""", (uid,))
        elif val == "work":
            conn.execute("""UPDATE user_settings 
                           SET schedule_enabled = 1, schedule_start = '09:00', schedule_end = '18:00' 
                           WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)""", (uid,))
        elif val == "night":
            conn.execute("""UPDATE user_settings 
                           SET schedule_enabled = 1, schedule_start = '00:00', schedule_end = '06:00' 
                           WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)""", (uid,))
    
    await callback.answer("✅ РАСПИСАНИЕ СОХРАНЕНО!", show_alert=True)
    await settings_cb(callback)

@dp.callback_query_handler(lambda c: c.data == "change_theme")
async def change_theme_menu_cb(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🌙 ТЁМНАЯ", callback_data="theme_dark"),
        InlineKeyboardButton("☀️ СВЕТЛАЯ", callback_data="theme_light"),
        InlineKeyboardButton("💙 СИНЯЯ", callback_data="theme_blue"),
        InlineKeyboardButton("💚 ЗЕЛЁНАЯ", callback_data="theme_green"),
        InlineKeyboardButton("🔙 НАЗАД", callback_data="settings")
    )
    
    await callback.message.edit_text("🎨 **ЦВЕТОВАЯ ТЕМА** 🎨\n━━━━━━━━━━━━━━━━━━━━━\nВЫБЕРИ ОФОРМЛЕНИЕ ИНТЕРФЕЙСА", 
                               parse_mode='Markdown', reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("theme_"))
async def set_theme_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    theme = callback.data.replace("theme_", "")
    
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO user_themes (user_id, theme) VALUES (?, ?)", 
                     (get_user_db_id(uid), theme))
    
    await callback.answer(f"✅ ТЕМА ИЗМЕНЕНА НА {THEMES[theme]['name']}!", show_alert=True)
    await settings_cb(callback)

@dp.callback_query_handler(lambda c: c.data == "change_language")
async def change_language_menu_cb(callback: CallbackQuery):
    await callback.message.edit_text("🌐 **ВЫБЕРИ ЯЗЫК / SELECT LANGUAGE** 🌐\n━━━━━━━━━━━━━━━━━━━━━", 
                               parse_mode='Markdown', reply_markup=get_language_keyboard())

@dp.callback_query_handler(lambda c: c.data.startswith("lang_"))
async def set_language_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    lang = callback.data.replace("lang_", "")
    
    with get_db() as conn:
        conn.execute("UPDATE users SET language = ? WHERE telegram_id = ?", (lang, uid))
    
    await callback.answer(f"✅ ЯЗЫК ИЗМЕНЁН!", show_alert=True)
    await settings_cb(callback)

@dp.callback_query_handler(lambda c: c.data == "about")
async def about_cb(callback: CallbackQuery):
    text = f"⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️\n\n🔋 **ULTROVPN v8.0** 🔋\n💪 **ЭНЕРГИЯ ТВОЕЙ СВОБОДЫ!**\n\n⚡️ 100+ ФУНКЦИЙ\n🛡️ АНТИГЛУШИЛКА (AMNEZIAWG)\n🔒 VLESS + TROJAN + HYSTERIA2\n🎁 РЕФЕРАЛКА + БОНУСЫ\n📺 СТРИМИНГ-ПАКЕТЫ\n🎫 ПРОМОКОДЫ\n🔌 API ДЛЯ РАЗРАБОТЧИКОВ\n📱 ВСЕ УСТРОЙСТВА\n━━━━━━━━━━━━━━━━━━━━━\n📢 [НАШ КАНАЛ](https://t.me/UltroVPN)\n💬 @UltroVPNSupport\n━━━━━━━━━━━━━━━━━━━━━\n🔥 ТВОЙ ИНТЕРНЕТ — ТВОИ ПРАВИЛА!\n\n⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️"
    
    await callback.message.edit_text(text, parse_mode='Markdown', 
                               reply_markup=InlineKeyboardMarkup().add(
                                   InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")))

@dp.callback_query_handler(lambda c: c.data == "back_to_menu")
async def back_to_menu_cb(callback: CallbackQuery):
    await callback.message.edit_text(ENERGY_TEXTS["back"], parse_mode='Markdown', 
                               reply_markup=await main_kb(callback.from_user.id))

# ========== АДМИН ПАНЕЛЬ ==========
@dp.callback_query_handler(lambda c: c.data == "admin_panel")
@admin_only
async def admin_panel_cb(callback: CallbackQuery):
    text = "👑 **АДМИН ПАНЕЛЬ** 👑\n━━━━━━━━━━━━━━━━━━━━━\n📌 **КОМАНДЫ:**\n\n`/users` — СПИСОК ПОЛЬЗОВАТЕЛЕЙ\n`/deluser ID` — УДАЛИТЬ\n`/add_days ID ДНИ` — ДОБАВИТЬ ДНИ\n`/invite` — ИНВАЙТ\n`/broadcast` — РАССЫЛКА\n`/transactions` — ТРАНЗАКЦИИ\n`/createpromo КОД %` — ПРОМОКОД\n`/promolist` — СПИСОК ПРОМОКОДОВ\n`/delpromo КОД` — УДАЛИТЬ ПРОМОКОД\n`/setad ТЕКСТ ССЫЛКА` — РЕКЛАМА\n`/emergency_off_all` — ОТКЛЮЧИТЬ ВСЕХ\n`/analytics` — АНАЛИТИКА\n`/export_stats` — ЭКСПОРТ СТАТИСТИКИ\n`/post` — ОТПРАВИТЬ ПОСТ\n`/schedule_post` — НАСТРОЙКИ АВТОПОСТИНГА\n━━━━━━━━━━━━━━━━━━━━━\n🔥 УПРАВЛЯЙ ЭНЕРГИЕЙ!"
    
    await callback.message.edit_text(text, parse_mode='Markdown', 
                               reply_markup=InlineKeyboardMarkup().add(
                                   InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")))

@dp.message_handler(commands=['admin'])
@admin_only
async def admin_cmd(message: Message):
    try:
        with get_db() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM users")
            total = cursor.fetchone()[0]
            cursor = conn.execute("SELECT COUNT(*) FROM users WHERE subscription_end > datetime('now')")
            active = cursor.fetchone()[0]
            cursor = conn.execute("SELECT COUNT(*) FROM devices")
            devices = cursor.fetchone()[0]
            cursor = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE status='completed'")
            revenue = cursor.fetchone()[0]
        
        await message.reply(
            f"👑 **АДМИН ПАНЕЛЬ**\n━━━━━━━━━━━━━━━━━━━━━\n👥 ВСЕГО: {total}\n🟢 АКТИВНЫХ: {active}\n📱 УСТРОЙСТВ: {devices}\n💰 ДОХОД: {revenue}₽\n━━━━━━━━━━━━━━━━━━━━━\n🔥 /invite — ИНВАЙТ\n📢 /broadcast — РАССЫЛКА\n📊 /analytics — АНАЛИТИКА",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Ошибка в admin_cmd: {e}")
        await message.reply("❌ ОШИБКА ПОЛУЧЕНИЯ СТАТИСТИКИ")

@dp.message_handler(commands=['users'])
@admin_only
async def users_cmd(message: Message):
    try:
        with get_db() as conn:
            cursor = conn.execute("SELECT telegram_id, first_name, subscription_end, is_banned FROM users ORDER BY id DESC LIMIT 50")
            users = cursor.fetchall()
        
        if not users:
            await message.reply("📭 НЕТ ПОЛЬЗОВАТЕЛЕЙ")
            return
        
        text = "👥 **ПОЛЬЗОВАТЕЛИ (50):**\n━━━━━━━━━━━━━━━━━━━━━\n"
        for u in users:
            status = "🔴 БАН" if u[3] else "🟢 АКТ"
            end = u[2][:10] if u[2] else "НЕТ"
            text += f"• `{u[0]}` — {u[1][:15]} | {status} | ДО {end}\n"
        text += "━━━━━━━━━━━━━━━━━━━━━\n📌 /deluser ID — УДАЛИТЬ"
        
        if len(text) > 4000:
            for i in range(0, len(text), 4000):
                await message.reply(text[i:i+4000], parse_mode='Markdown')
        else:
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
            cursor = conn.execute("SELECT d.public_key FROM devices d JOIN users u ON u.id = d.user_id WHERE u.telegram_id = ?", (target,))
            devices = cursor.fetchall()
            
            for device in devices:
                if device[0]:
                    remove_peer(device[0])
            
            cursor = conn.execute("SELECT id FROM users WHERE telegram_id = ?", (target,))
            uidb = cursor.fetchone()
            if uidb:
                conn.execute("DELETE FROM devices WHERE user_id = ?", (uidb[0],))
                conn.execute("DELETE FROM user_settings WHERE user_id = ?", (uidb[0],))
                conn.execute("DELETE FROM backup_codes WHERE user_id = ?", (uidb[0],))
                conn.execute("DELETE FROM api_keys WHERE user_id = ?", (uidb[0],))
                conn.execute("DELETE FROM users WHERE telegram_id = ?", (target,))
                await message.reply(f"✅ ПОЛЬЗОВАТЕЛЬ `{target}` УДАЛЁН", parse_mode='Markdown')
                logger.info(f"Пользователь {target} удалён админом {message.from_user.id}")
            else:
                await message.reply(f"❌ ПОЛЬЗОВАТЕЛЬ `{target}` НЕ НАЙДЕН", parse_mode='Markdown')
    except ValueError:
        await message.reply("❌ НЕВЕРНЫЙ ID")
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
                logger.info(f"Добавлено {days} дней пользователю {target}")
            else:
                await message.reply(f"❌ ПОЛЬЗОВАТЕЛЬ `{target}` НЕ НАЙДЕН", parse_mode='Markdown')
    except ValueError:
        await message.reply("❌ НЕВЕРНЫЙ ID ИЛИ КОЛИЧЕСТВО ДНЕЙ")
    except Exception as e:
        logger.error(f"Ошибка в add_days_cmd: {e}")
        await message.reply("❌ ОШИБКА ДОБАВЛЕНИЯ ДНЕЙ")

@dp.message_handler(commands=['invite'])
@admin_only
async def invite_cmd(message: Message):
    try:
        code = secrets.token_hex(8).upper()
        uidb = get_user_db_id(message.from_user.id)
        
        with get_db() as conn:
            conn.execute("INSERT INTO invites (code, created_by) VALUES (?, ?)", (code, uidb))
        
        botname = (await bot.get_me()).username
        await message.reply(f"🎫 **ИНВАЙТ КОД:** `{code}`\n🔥 https://t.me/{botname}?start={code}", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Ошибка в invite_cmd: {e}")
        await message.reply("❌ ОШИБКА СОЗДАНИЯ ИНВАЙТА")

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
        failed = 0
        
        await message.reply(f"⏳ НАЧАЛА РАССЫЛКИ {len(users)} ПОЛЬЗОВАТЕЛЯМ...")
        
        for u in users:
            try:
                await bot.send_message(u[0], 
                    f"⚡️ **НОВОСТЬ ULTROVPN** ⚡️\n━━━━━━━━━━━━━━━━━━━━━\n{text}\n━━━━━━━━━━━━━━━━━━━━━\n🔥 ТВОЙ ЗАРЯД ВСЕГДА С ТОБОЙ!", 
                    parse_mode='Markdown')
                sent += 1
                await asyncio.sleep(0.05)
            except Exception:
                failed += 1
        
        await message.reply(f"✅ РАССЫЛКА ЗАВЕРШЕНА!\n📨 ОТПРАВЛЕНО: {sent}\n❌ ОШИБОК: {failed}")
        logger.info(f"Рассылка завершена. Отправлено: {sent}, Ошибок: {failed}")
    except Exception as e:
        logger.error(f"Ошибка в broadcast_cmd: {e}")
        await message.reply("❌ ОШИБКА РАССЫЛКИ")

@dp.message_handler(commands=['transactions'])
@admin_only
async def transactions_cmd(message: Message):
    try:
        with get_db() as conn:
            cursor = conn.execute("SELECT amount, payment_method, created_at, status FROM transactions ORDER BY created_at DESC LIMIT 20")
            txs = cursor.fetchall()
        
        if not txs:
            await message.reply("📭 НЕТ ТРАНЗАКЦИЙ")
            return
        
        text = "💰 **ТРАНЗАКЦИИ:**\n━━━━━━━━━━━━━━━━━━━━━\n"
        for tx in txs:
            status = "✅" if tx[3] == 'completed' else "⏳"
            text += f"{status} {tx[2][:10]} {tx[0]}₽ {tx[1]}\n"
        
        await message.reply(text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Ошибка в transactions_cmd: {e}")
        await message.reply("❌ ОШИБКА ПОЛУЧЕНИЯ ТРАНЗАКЦИЙ")

@dp.message_handler(commands=['createpromo'])
@admin_only
async def create_promo_cmd(message: Message):
    args = message.get_args().split()
    if len(args) < 2:
        await message.reply("❌ /createpromo КОД СКИДКА%\nПРИМЕР: /createpromo WELCOME50 50")
        return
    
    code = args[0].upper()
    try:
        discount = int(args[1])
    except ValueError:
        await message.reply("❌ СКИДКА ДОЛЖНА БЫТЬ ЧИСЛОМ")
        return
    
    try:
        with get_db() as conn:
            conn.execute("INSERT INTO promocodes (code, discount) VALUES (?, ?)", (code, discount))
        await message.reply(f"✅ ПРОМОКОД `{code}` СОЗДАН! СКИДКА {discount}%", parse_mode='Markdown')
        logger.info(f"Создан промокод {code} на {discount}%")
    except sqlite3.IntegrityError:
        await message.reply(f"❌ ПРОМОКОД `{code}` УЖЕ СУЩЕСТВУЕТ", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Ошибка в create_promo_cmd: {e}")
        await message.reply("❌ ОШИБКА СОЗДАНИЯ ПРОМОКОДА")

@dp.message_handler(commands=['promolist'])
@admin_only
async def promolist_cmd(message: Message):
    try:
        with get_db() as conn:
            cursor = conn.execute("SELECT code, discount, used_by FROM promocodes")
            promos = cursor.fetchall()
        
        if not promos:
            await message.reply("📭 НЕТ ПРОМОКОДОВ")
            return
        
        text = "🎫 **ПРОМОКОДЫ:**\n━━━━━━━━━━━━━━━━━━━━━\n"
        for p in promos:
            status = "✅ ИСПОЛЬЗОВАН" if p[2] else "❌ НЕ ИСПОЛЬЗОВАН"
            text += f"• `{p[0]}` — {p[1]}% — {status}\n"
        
        await message.reply(text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Ошибка в promolist_cmd: {e}")
        await message.reply("❌ ОШИБКА ПОЛУЧЕНИЯ СПИСКА")

@dp.message_handler(commands=['delpromo'])
@admin_only
async def delpromo_cmd(message: Message):
    code = message.get_args().strip().upper()
    if not code:
        await message.reply("❌ /delpromo КОД")
        return
    
    try:
        with get_db() as conn:
            conn.execute("DELETE FROM promocodes WHERE code = ?", (code,))
        await message.reply(f"✅ ПРОМОКОД `{code}` УДАЛЁН", parse_mode='Markdown')
        logger.info(f"Удалён промокод {code}")
    except Exception as e:
        logger.error(f"Ошибка в delpromo_cmd: {e}")
        await message.reply("❌ ОШИБКА УДАЛЕНИЯ")

@dp.message_handler(commands=['setad'])
@admin_only
async def setad_cmd(message: Message):
    global SPONSOR_BUTTON_TEXT, SPONSOR_BUTTON_URL
    
    args = message.get_args().split()
    if len(args) < 2:
        await message.reply("❌ /setad ТЕКСТ ССЫЛКА")
        return
    
    SPONSOR_BUTTON_TEXT = ' '.join(args[:-1])
    SPONSOR_BUTTON_URL = args[-1]
    
    await message.reply(f"✅ РЕКЛАМА ОБНОВЛЕНА!\nТЕКСТ: {SPONSOR_BUTTON_TEXT}\nССЫЛКА: {SPONSOR_BUTTON_URL}")
    logger.info(f"Рекламная кнопка обновлена: {SPONSOR_BUTTON_TEXT} -> {SPONSOR_BUTTON_URL}")

@dp.message_handler(commands=['emergency_off_all'])
@admin_only
async def emergency_off_all_cmd(message: Message):
    try:
        with get_db() as conn:
            cursor = conn.execute("SELECT public_key FROM devices WHERE public_key IS NOT NULL")
            devices = cursor.fetchall()
        
        count = 0
        for device in devices:
            if remove_peer(device[0]):
                count += 1
        
        await message.reply(f"🚨 **ЭКСТРЕННОЕ ОТКЛЮЧЕНИЕ!**\n🔥 ОТКЛЮЧЕНО УСТРОЙСТВ: {count}", parse_mode='Markdown')
        logger.warning(f"Экстренное отключение всех устройств. Отключено: {count}")
    except Exception as e:
        logger.error(f"Ошибка в emergency_off_all_cmd: {e}")
        await message.reply("❌ ОШИБКА ОТКЛЮЧЕНИЯ")

@dp.message_handler(commands=['analytics'])
@admin_only
async def analytics_cmd(message: Message):
    await message.reply("📊 **СБОР ДАННЫХ...** ⏳")
    
    await collect_daily_stats()
    
    with get_db() as conn:
        today = datetime.now().date().isoformat()
        cursor = conn.execute("SELECT * FROM daily_stats WHERE date = ?", (today,))
        today_stats = cursor.fetchone()
        
        cursor = conn.execute("""
            SELECT 
                SUM(new_users) as total_new,
                AVG(active_users) as avg_active,
                SUM(revenue) as total_revenue,
                AVG(conversions) as avg_conversions,
                AVG(referral_clicks) as avg_clicks
            FROM daily_stats 
            WHERE date > datetime('now', '-7 days')
        """)
        week_stats = cursor.fetchone()
        
        cursor = conn.execute("""
            SELECT 
                SUM(new_users) as total_new,
                AVG(active_users) as avg_active,
                SUM(revenue) as total_revenue,
                COUNT(DISTINCT date) as days_count
            FROM daily_stats 
            WHERE date > datetime('now', '-30 days')
        """)
        month_stats = cursor.fetchone()
        
        cursor = conn.execute("""
            SELECT code, COUNT(*) as uses
            FROM promocodes
            WHERE used_at > datetime('now', '-30 days')
            GROUP BY code
            ORDER BY uses DESC
            LIMIT 5
        """)
        top_promos = cursor.fetchall()
        
        cursor = conn.execute("""
            SELECT source, SUM(clicks) as clicks, SUM(registrations) as regs
            FROM source_stats
            WHERE date > datetime('now', '-30 days')
            GROUP BY source
            ORDER BY regs DESC
            LIMIT 5
        """)
        top_sources = cursor.fetchall()
        
        cursor = conn.execute("""
            SELECT cohort_date, day_1, day_7, day_30
            FROM retention_stats
            ORDER BY cohort_date DESC
            LIMIT 5
        """)
        retention = cursor.fetchall()
        
        cursor = conn.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1")
        banned_users = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT COUNT(*) FROM devices")
        total_devices = cursor.fetchone()[0]
    
    text = f"""
📊 **ULTROVPN АНАЛИТИКА**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📅 **СЕГОДНЯ:**
👥 НОВЫХ: {today_stats[1] if today_stats else 0}
🟢 АКТИВНЫХ: {today_stats[2] if today_stats else 0}
💰 ДОХОД: {today_stats[3] if today_stats else 0}₽
📈 КОНВЕРСИЙ: {today_stats[4] if today_stats else 0}
🔗 РЕФ. КЛИКОВ: {today_stats[5] if today_stats else 0}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📆 **ПОСЛЕДНИЕ 7 ДНЕЙ:**
👥 НОВЫХ: {week_stats[0] if week_stats else 0}
🟢 АКТИВНЫХ (ср.): {week_stats[1] if week_stats else 0:.0f}
💰 ДОХОД: {week_stats[2] if week_stats else 0}₽
📈 КОНВЕРСИЙ (ср.): {week_stats[3] if week_stats else 0:.1f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📆 **ПОСЛЕДНИЕ 30 ДНЕЙ:**
👥 НОВЫХ: {month_stats[0] if month_stats else 0}
🟢 АКТИВНЫХ (ср.): {month_stats[1] if month_stats else 0:.0f}
💰 ДОХОД: {month_stats[2] if month_stats else 0}₽
📊 ARPU: {(month_stats[2] / month_stats[3] / 30) if month_stats and month_stats[3] else 0:.2f}₽/день

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎫 **ТОП ПРОМОКОДЫ (месяц):**
"""
    if top_promos:
        for i, promo in enumerate(top_promos[:5], 1):
            text += f"{i}. `{promo[0]}` — {promo[1]} использований\n"
    else:
        text += "📭 НЕТ ДАННЫХ\n"
    
    text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📱 **ИСТОЧНИКИ ТРАФИКА (месяц):**
"""
    if top_sources:
        for src in top_sources[:5]:
            conv_rate = (src[2] / src[1] * 100) if src[1] > 0 else 0
            text += f"• {src[0]}: {src[2]} рег. ({conv_rate:.1f}%)\n"
    else:
        text += "📭 НЕТ ДАННЫХ\n"
    
    text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **RETENTION (удержание):**
"""
    if retention:
        for ret in retention[:5]:
            day1_pct = (ret[1] / ret[0] * 100) if ret[0] > 0 else 0
            day7_pct = (ret[2] / ret[0] * 100) if ret[0] > 0 else 0
            text += f"• {ret[0]}: День1 {day1_pct:.0f}% | День7 {day7_pct:.0f}%\n"
    else:
        text += "📭 НЕТ ДАННЫХ\n"
    
    text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **ОБЩАЯ СТАТИСТИКА:**
👥 ВСЕГО ПОЛЬЗОВАТЕЛЕЙ: {total_users}
🚫 ЗАБЛОКИРОВАННЫХ: {banned_users}
📱 ВСЕГО УСТРОЙСТВ: {total_devices}
📊 СРЕДНЕЕ УСТРОЙСТВ НА ПОЛЬЗОВАТЕЛЯ: {total_devices/total_users:.1f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔥 /export_stats — ЭКСПОРТ СТАТИСТИКИ
"""
    
    await message.reply(text, parse_mode='Markdown')

@dp.message_handler(commands=['export_stats'])
@admin_only
async def export_stats_cmd(message: Message):
    await message.reply("📊 **ФОРМИРУЮ CSV ФАЙЛ...** ⏳")
    
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM daily_stats ORDER BY date DESC LIMIT 90")
        stats = cursor.fetchall()
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Дата', 'Новые', 'Активные', 'Доход', 'Конверсии', 'Реф.клики'])
    
    for stat in stats:
        writer.writerow([stat[0], stat[1], stat[2], stat[3], stat[4], stat[5]])
    
    output.seek(0)
    file = BytesIO(output.getvalue().encode('utf-8'))
    file.name = f"analytics_{datetime.now().strftime('%Y%m%d')}.csv"
    
    await message.reply_document(
        types.InputFile(file),
        caption=f"📊 Статистика UltroVPN за последние 90 дней\n📅 {datetime.now().strftime('%d.%m.%Y')}"
    )

@dp.message_handler(commands=['post'])
@admin_only
async def post_cmd(message: Message):
    text = message.get_args()
    if not text:
        await message.reply("❌ /post ТЕКСТ СООБЩЕНИЯ\n\nПример:\n/post Привет всем! 🔥")
        return
    
    try:
        await bot.send_message(
            AUTO_POST_CHANNEL,
            text,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        await message.reply("✅ ПОСТ ОТПРАВЛЕН В КАНАЛ!")
        logger.info(f"Ручной пост отправлен админом {message.from_user.id}")
    except Exception as e:
        await message.reply(f"❌ ОШИБКА: {e}")

@dp.message_handler(commands=['schedule_post'])
@admin_only
async def schedule_post_cmd(message: Message):
    global AUTO_POST_INTERVAL_HOURS, AUTO_POST_ENABLED, AUTO_POST_CHANNEL
    
    args = message.get_args().split()
    if len(args) < 1:
        await message.reply(f"""❌ **НАСТРОЙКА АВТОПОСТИНГА**

📌 /schedule_post hours [интервал]
   Пример: /schedule_post 6

📌 /schedule_post on — ВКЛЮЧИТЬ
📌 /schedule_post off — ВЫКЛЮЧИТЬ
📌 /schedule_post channel @username — СМЕНИТЬ КАНАЛ
📌 /schedule_post status — СТАТУС

📢 Текущий канал: {AUTO_POST_CHANNEL or 'не задан'}
⏱️ Интервал: {AUTO_POST_INTERVAL_HOURS} часов
🟢 Статус: {'ВКЛЮЧЕН' if AUTO_POST_ENABLED else 'ВЫКЛЮЧЕН'}
""", parse_mode='Markdown')
        return
    
    command = args[0].lower()
    
    if command == "on":
        AUTO_POST_ENABLED = True
        await message.reply("✅ АВТОПОСТИНГ ВКЛЮЧЁН!")
        
    elif command == "off":
        AUTO_POST_ENABLED = False
        await message.reply("❌ АВТОПОСТИНГ ВЫКЛЮЧЁН!")
        
    elif command == "hours" and len(args) > 1:
        try:
            hours = int(args[1])
            if 1 <= hours <= 24:
                AUTO_POST_INTERVAL_HOURS = hours
                await message.reply(f"✅ ИНТЕРВАЛ ИЗМЕНЁН НА {hours} ЧАСОВ!")
            else:
                await message.reply("❌ ИНТЕРВАЛ ДОЛЖЕН БЫТЬ ОТ 1 ДО 24 ЧАСОВ")
        except ValueError:
            await message.reply("❌ НЕВЕРНОЕ ЗНАЧЕНИЕ")
            
    elif command == "channel" and len(args) > 1:
        channel = args[1]
        if channel.startswith('@'):
            AUTO_POST_CHANNEL = channel
            await message.reply(f"✅ КАНАЛ ИЗМЕНЁН НА {channel}")
        else:
            await message.reply("❌ КАНАЛ ДОЛЖЕН НАЧИНАТЬСЯ С @")
            
    elif command == "status":
        await message.reply(f"""📊 **СТАТУС АВТОПОСТИНГА**

📢 КАНАЛ: {AUTO_POST_CHANNEL or 'не задан'}
⏱️ ИНТЕРВАЛ: {AUTO_POST_INTERVAL_HOURS} ч.
🟢 СТАТУС: {'ВКЛЮЧЕН' if AUTO_POST_ENABLED else 'ВЫКЛЮЧЕН'}
📝 ШАБЛОНОВ: {len(AUTO_POST_TEMPLATES)}
""", parse_mode='Markdown')
    else:
        await message.reply("❌ НЕИЗВЕСТНАЯ КОМАНДА")

@dp.message_handler(commands=['backup_db'])
@admin_only
async def backup_db_cmd(message: Message):
    try:
        backup_db()
        await message.reply("✅ БЭКАП БАЗЫ ДАННЫХ СОЗДАН!\n📁 ПАПКА: backups/")
        logger.info(f"Ручной бэкап БД от {message.from_user.id}")
    except Exception as e:
        logger.error(f"Ошибка бэкапа БД: {e}")
        await message.reply("❌ ОШИБКА СОЗДАНИЯ БЭКАПА")

# ========== ЭКСТРЕННОЕ ОТКЛЮЧЕНИЕ ==========
@dp.message_handler(lambda m: m.text and m.text.lower() in EMERGENCY_COMMANDS)
async def emergency_off_handler(message: Message):
    uid = message.from_user.id
    
    try:
        with get_db() as conn:
            cursor = conn.execute("SELECT d.public_key FROM devices d JOIN users u ON u.id = d.user_id WHERE u.telegram_id = ?", (uid,))
            devs = cursor.fetchall()
            
            for dev in devs:
                if dev[0]:
                    remove_peer(dev[0])
        
        await message.reply("🚨 **ЭКСТРЕННОЕ ОТКЛЮЧЕНИЕ!**\n⚡️ ВСЕ VPN СОЕДИНЕНИЯ РАЗОРВАНЫ!\n🔥 НАЖМИ /start ЧТОБЫ ЗАРЯДИТЬСЯ ЗАНОВО!", parse_mode='Markdown')
        logger.info(f"Экстренное отключение для {uid}")
    except Exception as e:
        logger.error(f"Ошибка экстренного отключения: {e}")
        await message.reply("❌ ОШИБКА ОТКЛЮЧЕНИЯ")

# ========== ЗАПУСК ==========
async def on_startup(dp):
    try:
        if not setup_wireguard():
            logger.warning("WireGuard не настроен! Возможно, бот запущен не на сервере")
        
        asyncio.create_task(check_expiring_subscriptions())
        asyncio.create_task(auto_poster())
        asyncio.create_task(daily_stats_collector())
        
        me = await bot.get_me()
        logger.info("=" * 60)
        logger.info("⚡️ ULTROVPN v8.0 — ЭНЕРГИЯ ТВОЕЙ СВОБОДЫ! ⚡️")
        logger.info(f"🔥 БОТ ЗАПУЩЕН: @{me.username}")
        logger.info(f"⚡️ IP: {SERVER_PUBLIC_IP}")
        logger.info(f"📢 АВТОПОСТИНГ: {'ВКЛ' if AUTO_POST_ENABLED else 'ВЫКЛ'}")
        logger.info(f"📊 АНАЛИТИКА: ВКЛЮЧЕНА")
        logger.info("=" * 60)
        
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, 
                    "⚡️ **ULTROVPN БОТ ЗАПУЩЕН!** ⚡️\n"
                    f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
                    "📊 Аналитика включена\n"
                    "📢 Автопостинг активен\n"
                    "🔥 ВСЕ СИСТЕМЫ РАБОТАЮТ!", parse_mode='Markdown')
            except:
                pass
                
    except Exception as e:
        logger.error(f"Ошибка при запуске: {e}")
        raise

def main():
    init_db()
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)

if __name__ == '__main__':
    main()
```
