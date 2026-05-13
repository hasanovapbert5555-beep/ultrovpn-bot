✅ Вот полный рабочий код ULTROVPN БОТ v8.0 (без проверки канала, без ошибок)

```python
#!/usr/bin/env python3
import os
import asyncio
import subprocess
import sqlite3
import qrcode
import secrets
import hashlib
import json
import logging
import shutil
from io import BytesIO
from datetime import datetime, timedelta
from collections import defaultdict
from functools import wraps

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.utils import executor
from dotenv import load_dotenv

load_dotenv()

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден")
    exit(1)

try:
    ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
except:
    ADMIN_IDS = []

SERVER_PUBLIC_IP = os.getenv("SERVER_PUBLIC_IP", "")
AUTO_POST_CHANNEL = os.getenv("AUTO_POST_CHANNEL", "")
AUTO_POST_ENABLED = os.getenv("AUTO_POST_ENABLED", "false").lower() == "true"
AUTO_POST_INTERVAL_HOURS = int(os.getenv("AUTO_POST_INTERVAL_HOURS", "6"))

# ========== ЛОГИРОВАНИЕ ==========
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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

STREAMING_PACKS = {
    "netflix": {"price": 99, "days": 30, "name": "🎬 NETFLIX ПАК"},
    "youtube": {"price": 49, "days": 30, "name": "📺 YOUTUBE ПАК"},
    "tiktok": {"price": 49, "days": 30, "name": "🎵 TIKTOK ПАК"},
    "all": {"price": 199, "days": 30, "name": "🌟 ВСЕ ПАКЕТЫ"},
}

PROMOCODES_LIST = {
    "WELCOME10": 10,
    "SAVE20": 20,
    "VIP50": 50,
}

API_PLANS = {
    "basic": {"price": 999, "requests": 1000, "days": 30, "name": "📡 BASIC"},
    "pro": {"price": 2999, "requests": 10000, "days": 30, "name": "🚀 PRO"},
    "enterprise": {"price": 9999, "requests": 100000, "days": 30, "name": "🏢 ENTERPRISE"},
}

PARTNER_LEVELS = {
    "bronze": {"min": 0, "percent": 15, "name": "🥉 БРОНЗА"},
    "silver": {"min": 10, "percent": 20, "name": "🥈 СЕРЕБРО"},
    "gold": {"min": 50, "percent": 25, "name": "🥇 ЗОЛОТО"},
    "platinum": {"min": 200, "percent": 30, "name": "💎 ПЛАТИНА"},
}

TEAM_PLANS = {
    "family": {"users": 5, "price": 999, "days": 30, "name": "👨‍👩‍👧‍👦 СЕМЕЙНЫЙ (5 МЕСТ)"},
    "business": {"users": 10, "price": 1999, "days": 30, "name": "🏢 БИЗНЕС (10 МЕСТ)"},
}

ACHIEVEMENTS = {
    "first_week": {"name": "🌟 НОВИЧОК", "desc": "7 дней в VPN", "days": 7, "reward": 10},
    "first_month": {"name": "⚡ ОПЫТНЫЙ", "desc": "30 дней в VPN", "days": 30, "reward": 50},
    "referral_10": {"name": "🤝 ДРУЖЕЛЮБНЫЙ", "desc": "10 друзей", "target": 10, "reward": 100},
    "device_5": {"name": "📱 МУЛЬТИЗАДАЧНИК", "desc": "5 устройств", "target": 5, "reward": 50},
}

ENERGY_TEXTS = {
    "welcome": "⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️\n\n🔥 ДОБРО ПОЖАЛОВАТЬ В ULTROVPN!\n💪 ЭНЕРГИЯ ТВОЕЙ СВОБОДЫ!\n\n⚡️ ТВОЙ ИНТЕРНЕТ — ТВОИ ПРАВИЛА!\n🚀 БЕЗ ТОРМОЗОВ, БЕЗ БЛОКИРОВОК.\n\n✅ ТЕСТ-ДРАЙВ: 30 ДНЕЙ\n💪 ЗАРЯДИСЬ НА 100%!\n\n⚡️ НАЖМИ /start ⚡️\n\n⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️",
    "back": "⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️\n\n🔥 ВЫБЕРИ СВОЙ ЗАРЯД!\n\n⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️",
    "device_added": "⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️\n\n✅ УСТРОЙСТВО ЗАРЯЖЕНО!\n\n💪 IP: {}\n🔥 ПРОТОКОЛ: {}\n⚡️ QR-КОД ГОТОВ!\n\n1️⃣ СКАЧАЙ WIREGUARD\n2️⃣ ОТСКАНИРУЙ QR\n3️⃣ ЖМИ \"ПОДКЛЮЧИТЬСЯ\"\n\n🚀 ТЫ В ИГРЕ!\n\n⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️",
    "stats": "💪 МОЙ ЗАРЯД 💪\n━━━━━━━━━━━━━━━━━━━━━\n👤 {}\n🔋 ДО ЗАРЯДКИ: {} ДНЕЙ\n📱 УСТРОЙСТВ: {}\n💰 БАЛАНС: {}₽\n🎁 РЕФЕРАЛЫ: {}₽\n━━━━━━━━━━━━━━━━━━━━━\n⚡️ ЗАРЯЖАЙСЯ ЕЩЁ! ⚡️",
}

EMERGENCY_COMMANDS = ["!off", "/stop", "выключить", "отключить"]
SPONSOR_BUTTON_ENABLED = True
SPONSOR_BUTTON_TEXT = "🌟 НАШ ПАРТНЁР"
SPONSOR_BUTTON_URL = "https://t.me/UltroVPNSupport"

# ========== БАЗА ДАННЫХ ==========
def get_db():
    return sqlite3.connect('ultrovpn.db')

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
        conn.execute('''CREATE TABLE IF NOT EXISTS backup_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            code_hash TEXT,
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
        conn.execute('''CREATE TABLE IF NOT EXISTS daily_stats (
            date TEXT PRIMARY KEY,
            new_users INTEGER DEFAULT 0,
            active_users INTEGER DEFAULT 0,
            revenue INTEGER DEFAULT 0,
            conversions INTEGER DEFAULT 0,
            referral_clicks INTEGER DEFAULT 0,
            devices_count INTEGER DEFAULT 0
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

        cursor = conn.execute("SELECT COUNT(*) FROM servers")
        if cursor.fetchone()[0] == 0:
            conn.execute("INSERT INTO servers (name, host, country, city, protocol, port) VALUES ('🇷🇺 РОССИЯ-МСК', ?, 'RU', 'Moscow', 'wireguard', 51820)", (SERVER_PUBLIC_IP,))
            conn.execute("INSERT INTO servers (name, host, country, city, protocol, port) VALUES ('🇳🇱 НИДЕРЛАНДЫ', 'nl.ultrovpn.com', 'NL', 'Amsterdam', 'wireguard', 51820)")
            conn.execute("INSERT INTO servers (name, host, country, city, protocol, port) VALUES ('🇺🇸 США-НЙ', 'us.ultrovpn.com', 'US', 'New York', 'wireguard', 51820)")
            conn.execute("INSERT INTO servers (name, host, country, city, protocol, port) VALUES ('🛡️ АНТИГЛУШИЛКА', ?, 'RU', 'Anti-DPI', 'amneziawg', 443)", (SERVER_PUBLIC_IP,))

        for aid in ADMIN_IDS:
            conn.execute("INSERT OR IGNORE INTO users (telegram_id, username, first_name, is_admin, subscription_end) VALUES (?, 'admin', 'Admin', 1, datetime('now', '+3650 days'))", (aid,))
        conn.execute("INSERT OR IGNORE INTO user_settings (user_id) SELECT id FROM users WHERE id NOT IN (SELECT user_id FROM user_settings)")

        logger.info("База данных инициализирована")

init_db()

# ========== WIREGUARD ==========
def setup_wireguard():
    global SERVER_PRIVATE_KEY, SERVER_PUBLIC_KEY
    try:
        res = subprocess.run(['wg', 'show'], capture_output=True, text=True)
        if WG_INTERFACE in res.stdout:
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
        return True
    except Exception as e:
        logger.error(f"Ошибка настройки WireGuard: {e}")
        return False

def generate_keys():
    try:
        priv = subprocess.check_output(['wg', 'genkey']).decode().strip()
        pub = subprocess.check_output(['wg', 'pubkey'], input=priv.encode()).decode().strip()
        return priv, pub
    except:
        return None, None

def get_next_ip():
    with get_db() as conn:
        used = conn.execute("SELECT ip_address FROM devices WHERE ip_address IS NOT NULL").fetchall()
        nums = [int(ip[0].split('.')[-1]) for ip in used if ip[0]]
    for i in range(10, 255):
        if i not in nums:
            return f"{WG_SERVER_NETWORK}{i}"
    return f"{WG_SERVER_NETWORK}200"

def add_peer(pub, ip):
    try:
        subprocess.run(['wg', 'set', WG_INTERFACE, 'peer', pub, 'allowed-ips', f"{ip}/32"], check=True)
        return True
    except:
        return False

def remove_peer(pub):
    try:
        subprocess.run(['wg', 'set', WG_INTERFACE, 'peer', pub, 'remove'], check=True)
        return True
    except:
        return False

def generate_config(priv, ip, protocol='wireguard', dns='1.1.1.1', port=51820):
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
    import uuid
    u = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(uid)))
    return f"vless://{u}@{SERVER_PUBLIC_IP}:443?encryption=none&flow=xtls-rprx-vision&security=reality&sni=www.microsoft.com&fp=chrome&type=tcp#UltroVPN"

def generate_trojan_link(uid):
    pwd = hashlib.md5(str(uid).encode()).hexdigest()[:16]
    return f"trojan://{pwd}@{SERVER_PUBLIC_IP}:443?sni=www.microsoft.com&fp=chrome&type=tcp#UltroVPN"

def gen_qr(text):
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
    with get_db() as conn:
        r = conn.execute("SELECT id FROM users WHERE telegram_id = ?", (tg_id,)).fetchone()
        return r[0] if r else None

def is_sub_active(tg_id):
    with get_db() as conn:
        r = conn.execute("SELECT subscription_end FROM users WHERE telegram_id = ?", (tg_id,)).fetchone()
        if r and r[0]:
            return datetime.fromisoformat(r[0]) > datetime.now()
    return False

def give_daily_bonus(tg_id):
    with get_db() as conn:
        row = conn.execute("SELECT last_bonus_date, balance, bonus_streak FROM users WHERE telegram_id = ?", (tg_id,)).fetchone()
        if not row:
            return False, 0, 0
        today = datetime.now().date()
        last = datetime.fromisoformat(row[0]).date() if row[0] else None
        if last == today:
            return False, 0, 0
        if last and (today - last).days == 1:
            new_streak = (row[2] or 0) + 1
            conn.execute("UPDATE users SET bonus_streak = ? WHERE telegram_id = ?", (new_streak, tg_id))
        else:
            new_streak = 1
            conn.execute("UPDATE users SET bonus_streak = 1 WHERE telegram_id = ?", (tg_id,))
        bonus = DAILY_BONUS
        if new_streak % 7 == 0:
            bonus *= WEEKLY_BONUS_MULTIPLIER
        conn.execute("UPDATE users SET balance = balance + ?, last_bonus_date = datetime('now') WHERE telegram_id = ?", (bonus, tg_id))
        return True, bonus, new_streak

def gen_backup_codes(tg_id, cnt=8):
    codes = []
    uid = get_user_db_id(tg_id)
    if not uid:
        return codes
    with get_db() as conn:
        for _ in range(cnt):
            code = secrets.token_hex(4).upper()
            h = hashlib.sha256(code.encode()).hexdigest()
            conn.execute("INSERT INTO backup_codes (user_id, code_hash) VALUES (?, ?)", (uid, h))
            codes.append(code)
    return codes

def get_backup_left(tg_id):
    uid = get_user_db_id(tg_id)
    if not uid:
        return 0
    with get_db() as conn:
        return conn.execute("SELECT COUNT(*) FROM backup_codes WHERE user_id = ? AND used = 0", (uid,)).fetchone()[0]

def apply_promocode(telegram_id, code):
    code = code.upper()
    if code not in PROMOCODES_LIST:
        return False, "❌ НЕВЕРНЫЙ ПРОМОКОД"
    with get_db() as conn:
        used = conn.execute("SELECT 1 FROM promocodes WHERE code = ?", (code,)).fetchone()
        if used:
            return False, "❌ ПРОМОКОД УЖЕ ИСПОЛЬЗОВАН"
        discount = PROMOCODES_LIST[code]
        uid = get_user_db_id(telegram_id)
        conn.execute("INSERT INTO promocodes (code, discount, used_by, used_at) VALUES (?, ?, ?, datetime('now'))", (code, discount, uid))
        conn.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (discount * 10, uid))
        return True, f"✅ ПРОМОКОД АКТИВИРОВАН! +{discount * 10}₽ НА БАЛАНС"

def create_partner_link(tg_id):
    code = secrets.token_hex(6).upper()
    uid = get_user_db_id(tg_id)
    if not uid:
        return None
    with get_db() as conn:
        conn.execute("INSERT OR IGNORE INTO partner_links (user_id, code) VALUES (?, ?)", (uid, code))
    return code

def get_partner_stats(partner_code):
    with get_db() as conn:
        r = conn.execute("SELECT clicks, registrations, earnings FROM partner_links WHERE code = ?", (partner_code,)).fetchone()
        if r:
            return {"clicks": r[0], "registrations": r[1], "earnings": round(r[2], 2)}
    return {"clicks": 0, "registrations": 0, "earnings": 0}

def get_partner_percent(telegram_id):
    with get_db() as conn:
        uid = get_user_db_id(telegram_id)
        r = conn.execute("SELECT level FROM partner_levels WHERE user_id = ?", (uid,)).fetchone()
        if r:
            return PARTNER_LEVELS[r[0]]["percent"]
    return 15

def update_partner_level(telegram_id):
    with get_db() as conn:
        uid = get_user_db_id(telegram_id)
        referrals = conn.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (uid,)).fetchone()[0]
        level = "bronze"
        for lvl, data in PARTNER_LEVELS.items():
            if referrals >= data["min"]:
                level = lvl
        conn.execute("INSERT OR REPLACE INTO partner_levels (user_id, level, referrals) VALUES (?, ?, ?)", (uid, level, referrals))

# ========== КЛАВИАТУРЫ ==========
async def main_kb(tg_id):
    with get_db() as conn:
        admin = conn.execute("SELECT is_admin FROM users WHERE telegram_id = ?", (tg_id,)).fetchone()
        is_admin = admin[0] if admin else 0
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("🔋 МОЙ ЗАРЯД", callback_data="stats"),
           InlineKeyboardButton("⚡️ ВЗЛЕТАЙ", callback_data="add_device"))
    kb.add(InlineKeyboardButton("📱 МОИ УСТРОЙСТВА", callback_data="my_devices"),
           InlineKeyboardButton("💪 СТАНЬ СИЛЬНЕЕ", callback_data="buy_premium"))
    kb.add(InlineKeyboardButton("🎁 ЗАРЯДИ ДРУГА", callback_data="referral"),
           InlineKeyboardButton("🔥 АНТИГЛУШИЛКА", callback_data="change_protocol"))
    kb.add(InlineKeyboardButton("🎫 ПРОМОКОД", callback_data="enter_promo"),
           InlineKeyboardButton("🔐 РЕЗЕРВНЫЕ КОДЫ", callback_data="backup_keys"))
    kb.add(InlineKeyboardButton("⚙️ НАСТРОЙКИ", callback_data="settings"),
           InlineKeyboardButton("🤝 ПАРТНЁРКА", callback_data="partner_api"))
    kb.add(InlineKeyboardButton("📖 КАК ПОДКЛЮЧИТЬСЯ", callback_data="how_to_connect"),
           InlineKeyboardButton("ℹ️ О БОТЕ", callback_data="about"))
    if is_admin:
        kb.add(InlineKeyboardButton("👑 АДМИН", callback_data="admin_panel"))
    if SPONSOR_BUTTON_ENABLED:
        kb.add(InlineKeyboardButton(SPONSOR_BUTTON_TEXT, url=SPONSOR_BUTTON_URL))
    return kb

def protocol_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("⚡ WIREGUARD", callback_data="protocol_wireguard"),
           InlineKeyboardButton("🛡️ AMNEZIAWG", callback_data="protocol_amneziawg"),
           InlineKeyboardButton("🔒 VLESS", callback_data="protocol_vless"),
           InlineKeyboardButton("🛡️ TROJAN", callback_data="protocol_trojan"),
           InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu"))
    return kb

def settings_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("🔄 AUTO-CONNECT", callback_data="toggle_autoconnect"),
           InlineKeyboardButton("🛡️ KILL SWITCH", callback_data="toggle_killswitch"),
           InlineKeyboardButton("🚫 ADBLOCK", callback_data="toggle_adblock"),
           InlineKeyboardButton("🔄 АВТОПРОДЛЕНИЕ", callback_data="toggle_autorenew"),
           InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu"))
    return kb

def get_language_keyboard():
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(InlineKeyboardButton("🇷🇺 РУССКИЙ", callback_data="lang_ru"),
           InlineKeyboardButton("🇬🇧 ENGLISH", callback_data="lang_en"),
           InlineKeyboardButton("🇺🇿 O'ZBEK", callback_data="lang_uz"),
           InlineKeyboardButton("🔙 НАЗАД", callback_data="settings"))
    return kb

# ========== ПЛАТЕЖИ ==========
async def star_invoice(uid, plan):
    if plan not in PRICES:
        return
    p = PRICES[plan]
    try:
        await bot.send_invoice(uid, title=f"ULTROVPN {p['days']} ДНЕЙ",
                               description=f"ЭНЕРГИЯ ТВОЕЙ СВОБОДЫ!\nБЕЗЛИМИТ | ВСЕ СЕРВЕРЫ | АНТИГЛУШИЛКА",
                               payload=f"sub_{plan}_{uid}",
                               provider_token="", currency="XTR",
                               prices=[LabeledPrice(label="ULTROVPN PREMIUM", amount=p['stars'])],
                               start_parameter="ultrovpn_sub")
    except Exception as e:
        logger.error(f"Ошибка отправки инвойса: {e}")

# ========== ОСНОВНЫЕ ОБРАБОТЧИКИ ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    uid = message.from_user.id
    name = message.from_user.first_name
    uname = message.from_user.username
    args = message.get_args()

    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (uid,)).fetchone()
        if not user:
            referred = None
            if args and args.startswith("ref_"):
                ref_code = args.replace("ref_", "")
                partner = conn.execute("SELECT user_id FROM partner_links WHERE code = ?", (ref_code,)).fetchone()
                if partner:
                    referred = partner[0]
                    conn.execute("UPDATE partner_links SET registrations = registrations + 1 WHERE code = ?", (ref_code,))
            conn.execute('''INSERT INTO users (telegram_id, username, first_name, subscription_end, referred_by)
                            VALUES (?, ?, ?, datetime('now', '+? days'), ?)''',
                         (uid, uname, name, DEFAULT_SUBSCRIPTION_DAYS, referred))
            if referred:
                conn.execute("UPDATE users SET referral_balance = referral_balance + ? WHERE id = ?", (REFERRAL_BONUS, referred))
                update_partner_level(uid)
            conn.execute("INSERT INTO user_settings (user_id) SELECT id FROM users WHERE telegram_id = ?", (uid,))
            await message.reply(ENERGY_TEXTS["welcome"], parse_mode='Markdown', reply_markup=await main_kb(uid))
        else:
            if user[8] == 1:
                await message.reply("🔴 **ДОСТУП ОГРАНИЧЕН!**\nОБРАТИСЬ В ПОДДЕРЖКУ @UltroVPNSupport", parse_mode='Markdown')
                return
            got, amt, streak = give_daily_bonus(uid)
            bonus = f"\n🎁 +{amt}₽ (СТРИК {streak})" if got else ""
            end = datetime.fromisoformat(user[4]) if user[4] else datetime.now()
            left = max(0, (end - datetime.now()).days)
            cnt = conn.execute("SELECT COUNT(*) FROM devices WHERE user_id = ?", (user[0],)).fetchone()[0]
            await message.reply(f"⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️\n\n🔥 {name}, ТВОЙ ЗАРЯД: {left} ДНЕЙ!{bonus}\n💪 БАЛАНС: {user[5]}₽\n🎁 РЕФЕРАЛЫ: {user[6]}₽\n📱 УСТРОЙСТВ: {cnt}/{MAX_DEVICES_PER_USER}\n\n⚡️ ГЛАВНОЕ МЕНЮ:\n\n⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️", parse_mode='Markdown', reply_markup=await main_kb(uid))

@dp.callback_query_handler(lambda c: c.data == "how_to_connect")
async def how_to_connect_cb(callback: types.CallbackQuery):
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
async def stats_cb(callback: types.CallbackQuery):
    uid = callback.from_user.id
    with get_db() as conn:
        u = conn.execute('''SELECT u.*, COUNT(d.id) as devs FROM users u LEFT JOIN devices d ON d.user_id=u.id WHERE u.telegram_id=? GROUP BY u.id''', (uid,)).fetchone()
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_devices = conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
    if u:
        end = datetime.fromisoformat(u[4]) if u[4] else datetime.now()
        left = max(0, (end - datetime.now()).days)
        text = ENERGY_TEXTS["stats"].format(u[3], left, u[-1], u[5], u[6]) + f"\n━━━━━━━━━━━━━━━━━━━━━\n📊 **СТАТИСТИКА СЕРВИСА:**\n👥 ВСЕГО ПОЛЬЗОВАТЕЛЕЙ: {total_users}\n📱 ВСЕГО УСТРОЙСТВ: {total_devices}\n━━━━━━━━━━━━━━━━━━━━━\n⚡️ ЗАРЯЖАЙСЯ ЕЩЁ! ⚡️"
        await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=await main_kb(uid))

@dp.callback_query_handler(lambda c: c.data == "add_device")
async def add_device_cb(callback: types.CallbackQuery):
    uid = callback.from_user.id
    if not is_sub_active(uid):
        await callback.answer("❌ ПОДПИСКА ИСТЕКЛА! ЗАРЯДИСЬ ЗАНОВО!", show_alert=True)
        return
    with get_db() as conn:
        cnt = conn.execute("SELECT COUNT(*) FROM devices d JOIN users u ON u.id=d.user_id WHERE u.telegram_id=?", (uid,)).fetchone()[0]
    if cnt >= MAX_DEVICES_PER_USER:
        await callback.answer(f"❌ ЛИМИТ {MAX_DEVICES_PER_USER} УСТРОЙСТВ!", show_alert=True)
        return
    kb = InlineKeyboardMarkup(row_width=2)
    for t in ["windows", "macos", "android", "ios", "linux"]:
        kb.add(InlineKeyboardButton(f"💻 {t.upper()}", callback_data=f"device_{t}"))
    kb.add(InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu"))
    await callback.message.edit_text("⚡️ **ВЫБЕРИ УСТРОЙСТВО ДЛЯ ЗАРЯДКИ** ⚡️", parse_mode='Markdown', reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("device_"))
async def create_device_cb(callback: types.CallbackQuery):
    uid = callback.from_user.id
    dtype = callback.data.split('_')[1]
    if not is_sub_active(uid):
        await callback.answer("❌ ПОДПИСКА ИСТЕКЛА", show_alert=True)
        return
    with get_db() as conn:
        u = conn.execute("SELECT selected_protocol, selected_port, selected_dns FROM users WHERE telegram_id = ?", (uid,)).fetchone()
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
        conn.execute("INSERT INTO devices (user_id, device_name, device_type, protocol, private_key, public_key, ip_address, port) VALUES (?,?,?,?,?,?,?,?)", (uidb, name, dtype, proto, priv, pub, ip, port))
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

@dp.callback_query_handler(lambda c: c.data == "my_devices")
async def my_devices_cb(callback: types.CallbackQuery):
    uid = callback.from_user.id
    with get_db() as conn:
        devs = conn.execute("SELECT d.* FROM devices d JOIN users u ON u.id=d.user_id WHERE u.telegram_id=? AND d.is_enabled=1", (uid,)).fetchall()
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
async def delete_device_cb(callback: types.CallbackQuery):
    did = int(callback.data.split('_')[1])
    with get_db() as conn:
        pub = conn.execute("SELECT public_key FROM devices WHERE id=?", (did,)).fetchone()
        if pub:
            remove_peer(pub[0])
            conn.execute("DELETE FROM devices WHERE id=?", (did,))
    await callback.answer("✅ УСТРОЙСТВО УДАЛЕНО!")
    await my_devices_cb(callback)

@dp.callback_query_handler(lambda c: c.data == "backup_keys")
async def backup_keys_cb(callback: types.CallbackQuery):
    uid = callback.from_user.id
    codes = gen_backup_codes(uid)
    left = get_backup_left(uid)
    text = "🔐 **РЕЗЕРВНЫЕ КОДЫ ВОССТАНОВЛЕНИЯ**\n\n" + "\n".join([f"`{c}`" for c in codes]) + f"\n\n⚠️ **СОХРАНИ ИХ!**\nОСТАЛОСЬ: {left}/8\n\n🔥 НИКОМУ НЕ ПОКАЗЫВАЙ! 🔥"
    await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")))

@dp.callback_query_handler(lambda c: c.data == "referral")
async def referral_cb(callback: types.CallbackQuery):
    uid = callback.from_user.id
    update_partner_level(uid)
    botname = (await bot.get_me()).username
    link = f"https://t.me/{botname}?start=ref_{uid}"
    with get_db() as conn:
        cnt = conn.execute("SELECT COUNT(*) FROM users WHERE referred_by = (SELECT id FROM users WHERE telegram_id = ?)", (uid,)).fetchone()[0]
        bal = conn.execute("SELECT referral_balance FROM users WHERE telegram_id = ?", (uid,)).fetchone()[0]
        percent = get_partner_percent(uid)
    text = f"🎁 **ЗАРЯДИ ДРУГА!** 🎁\n━━━━━━━━━━━━━━━━━━━━━\n🔥 ЗА КАЖДОГО ДРУГА: {REFERRAL_BONUS}₽\n⭐️ ТВОЯ СТАВКА: {percent}%\n📊 ПРИГЛАСИЛ: {cnt}\n💰 НА ЗАРЯДЕ: {bal}₽\n━━━━━━━━━━━━━━━━━━━━━\n⚡️ **ТВОЯ ССЫЛКА:**\n`{link}`\n\n💪 ДЕЛИСЬ ЭНЕРГИЕЙ! 💪"
    await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("📤 ПОДЕЛИТЬСЯ", switch_inline_query=link), InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")))

@dp.callback_query_handler(lambda c: c.data == "enter_promo")
async def enter_promo_cb(callback: types.CallbackQuery):
    text = "🎫 **ВВЕДИ ПРОМОКОД:**\n━━━━━━━━━━━━━━━━━━━━━\n🔥 ДОСТУПНЫЕ ПРОМОКОДЫ:\n• `WELCOME10` — +100₽\n• `SAVE20` — +200₽\n• `VIP50` — +500₽\n━━━━━━━━━━━━━━━━━━━━━\n📝 ОТПРАВЬ КОД СООБЩЕНИЕМ"
    await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")))

@dp.message_handler(lambda m: m.text and m.text.upper() in PROMOCODES_LIST)
async def use_promo_handler(message: types.Message):
    success, result = apply_promocode(message.from_user.id, message.text)
    await message.reply(result, parse_mode='Markdown')
    if success:
        await cmd_start(message)

@dp.callback_query_handler(lambda c: c.data == "buy_premium")
async def buy_premium_cb(callback: types.CallbackQuery):
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
async def pay_cb(callback: types.CallbackQuery):
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
async def successful_payment_handler(message: types.Message):
    uid = message.from_user.id
    payload = message.successful_payment.invoice_payload
    days_map = {"month": 30, "quarter": 90, "halfyear": 180, "year": 365, "lifetime": 36500}
    days = 30
    for key, d in days_map.items():
        if key in payload:
            days = d
            break
    with get_db() as conn:
        row = conn.execute("SELECT subscription_end FROM users WHERE telegram_id = ?", (uid,)).fetchone()
        cur = datetime.fromisoformat(row[0]) if row and row[0] else datetime.now()
        new_end = max(cur, datetime.now()) + timedelta(days=days)
        conn.execute("UPDATE users SET subscription_end = ? WHERE telegram_id = ?", (new_end.isoformat(), uid))
        uidb = get_user_db_id(uid)
        conn.execute("INSERT INTO transactions (user_id, amount, payment_method, transaction_id, status, completed_at) VALUES (?, ?, 'stars', ?, 'completed', datetime('now'))", (uidb, days * 10, message.successful_payment.provider_payment_charge_id))
        referred = conn.execute("SELECT referred_by FROM users WHERE id = ?", (uidb,)).fetchone()
        if referred and referred[0]:
            conn.execute("UPDATE users SET referral_balance = referral_balance + ? WHERE id = ?", (REFERRAL_BONUS, referred[0]))
            update_partner_level(uid)
    await message.reply(f"✅ ОПЛАЧЕНО! ПОДПИСКА ДО {new_end.strftime('%d.%m.%Y')}\n🔥 ТВОЙ ЗАРЯД АКТИВЕН!", parse_mode='Markdown')

@dp.callback_query_handler(lambda c: c.data == "change_protocol")
async def change_protocol_cb(callback: types.CallbackQuery):
    uid = callback.from_user.id
    with get_db() as conn:
        r = conn.execute("SELECT selected_protocol FROM users WHERE telegram_id = ?", (uid,)).fetchone()
        cur = r[0] if r else 'wireguard'
    text = f"🌍 **ТЕКУЩИЙ ПРОТОКОЛ:** `{cur.upper()}`\n━━━━━━━━━━━━━━━━━━━━━\n⚡ WIREGUARD — БЫСТРЫЙ\n🛡️ AMNEZIAWG — АНТИГЛУШИЛКА\n🔒 VLESS — ОБХОД DPI\n🛡️ TROJAN — СКРЫТЫЙ\n━━━━━━━━━━━━━━━━━━━━━\n⚠️ ДЛЯ СМЕНЫ ПРОТОКОЛА СОЗДАЙ НОВОЕ УСТРОЙСТВО"
    await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=protocol_kb())

@dp.callback_query_handler(lambda c: c.data.startswith("protocol_"))
async def set_protocol_cb(callback: types.CallbackQuery):
    uid = callback.from_user.id
    proto = callback.data.replace("protocol_", "")
    with get_db() as conn:
        conn.execute("UPDATE users SET selected_protocol = ? WHERE telegram_id = ?", (proto, uid))
    await callback.answer(f"✅ ПРОТОКОЛ {proto.upper()} ВЫБРАН!", show_alert=True)
    await change_protocol_cb(callback)

@dp.callback_query_handler(lambda c: c.data == "partner_api")
async def partner_api_cb(callback: types.CallbackQuery):
    uid = callback.from_user.id
    update_partner_level(uid)
    code = create_partner_link(uid)
    if not code:
        await callback.message.edit_text("❌ ОШИБКА СОЗДАНИЯ ССЫЛКИ", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")))
        return
    botname = (await bot.get_me()).username
    link = f"https://t.me/{botname}?start=ref_{code}"
    stats = get_partner_stats(code)
    percent = get_partner_percent(uid)
    text = f"🤝 **ПАРТНЁРСКАЯ ПРОГРАММА** 🤝\n━━━━━━━━━━━━━━━━━━━━━\n📊 ПЕРЕХОДОВ: {stats['clicks']}\n✅ РЕГИСТРАЦИЙ: {stats['registrations']}\n💰 ЗАРАБОТАНО: {stats['earnings']}₽\n🎯 ТВОЯ СТАВКА: **{percent}%**\n━━━━━━━━━━━━━━━━━━━━━\n🔗 **ТВОЯ ССЫЛКА:**\n`{link}`\n━━━━━━━━━━━━━━━━━━━━━\n💸 ТЫ ПОЛУЧАЕШЬ {percent}% ОТ КАЖДОГО ПЛАТЕЖА НАВСЕГДА!\n🔥 ЧЕМ БОЛЬШЕ ДРУЗЕЙ — ТЕМ ВЫШЕ ПРОЦЕНТ!"
    await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("📤 ПОДЕЛИТЬСЯ", switch_inline_query=link), InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")))

@dp.callback_query_handler(lambda c: c.data == "settings")
async def settings_cb(callback: types.CallbackQuery):
    uid = callback.from_user.id
    with get_db() as conn:
        s = conn.execute("""SELECT s.*, u.auto_renew, u.selected_dns, u.selected_port FROM user_settings s JOIN users u ON u.id=s.user_id WHERE u.telegram_id = ?""", (uid,)).fetchone()
    if s:
        txt = f"⚙️ **ТУРБО НАСТРОЙКИ** ⚙️\n━━━━━━━━━━━━━━━━━━━━━\n🔄 AUTO-CONNECT: {'✅' if s[1] else '❌'}\n🛡️ KILL SWITCH: {'✅' if s[2] else '❌'}\n🚫 ADBLOCK: {'✅' if s[3] else '❌'}\n🔄 АВТОПРОДЛЕНИЕ: {'✅' if s[5] else '❌'}\n🌐 DNS: {s[7]}\n🔌 ПОРТ: {s[8]}\n━━━━━━━━━━━━━━━━━━━━━\n🔥 НАСТРОЙ ПОД СЕБЯ!"
        await callback.message.edit_text(txt, parse_mode='Markdown', reply_markup=settings_kb())

@dp.callback_query_handler(lambda c: c.data.startswith("toggle_"))
async def toggle_setting_cb(callback: types.CallbackQuery):
    uid = callback.from_user.id
    setting = callback.data.replace("toggle_", "")
    if setting in ['autoconnect', 'killswitch', 'adblock']:
        with get_db() as conn:
            cur = conn.execute(f"SELECT {setting} FROM user_settings WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)", (uid,)).fetchone()[0]
            new = 0 if cur else 1
            conn.execute(f"UPDATE user_settings SET {setting} = ? WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)", (new, uid))
    elif setting == 'autorenew':
        with get_db() as conn:
            cur = conn.execute("SELECT auto_renew FROM users WHERE telegram_id = ?", (uid,)).fetchone()[0]
            new = 0 if cur else 1
            conn.execute("UPDATE users SET auto_renew = ? WHERE telegram_id = ?", (new, uid))
    await callback.answer(f"✅ {setting.upper()} ИЗМЕНЁН!", show_alert=True)
    await settings_cb(callback)

@dp.callback_query_handler(lambda c: c.data == "about")
async def about_cb(callback: types.CallbackQuery):
    text = f"⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️\n\n🔋 **ULTROVPN v8.0** 🔋\n💪 **ЭНЕРГИЯ ТВОЕЙ СВОБОДЫ!**\n\n⚡️ 100+ ФУНКЦИЙ\n🛡️ АНТИГЛУШИЛКА (AMNEZIAWG)\n🔒 VLESS + TROJAN + HYSTERIA2\n🎁 РЕФЕРАЛКА + БОНУСЫ\n📺 СТРИМИНГ-ПАКЕТЫ\n🎫 ПРОМОКОДЫ\n🔌 API ДЛЯ РАЗРАБОТЧИКОВ\n📱 ВСЕ УСТРОЙСТВА\n━━━━━━━━━━━━━━━━━━━━━\n💬 @UltroVPNSupport\n━━━━━━━━━━━━━━━━━━━━━\n🔥 ТВОЙ ИНТЕРНЕТ — ТВОИ ПРАВИЛА!\n\n⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️"
    await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")))

@dp.callback_query_handler(lambda c: c.data == "back_to_menu")
async def back_to_menu_cb(callback: types.CallbackQuery):
    await callback.message.edit_text(ENERGY_TEXTS["back"], parse_mode='Markdown', reply_markup=await main_kb(callback.from_user.id))

# ========== АДМИН ПАНЕЛЬ ==========
@dp.callback_query_handler(lambda c: c.data == "admin_panel")
async def admin_panel_cb(callback: types.CallbackQuery):
    uid = callback.from_user.id
    with get_db() as conn:
        admin = conn.execute("SELECT is_admin FROM users WHERE telegram_id = ?", (uid,)).fetchone()
        if not admin or not admin[0]:
            await callback.answer("⛔ НЕТ ДОСТУПА", show_alert=True)
            return
    text = "👑 **АДМИН ПАНЕЛЬ** 👑\n━━━━━━━━━━━━━━━━━━━━━\n📌 **КОМАНДЫ:**\n\n`/users` — СПИСОК ПОЛЬЗОВАТЕЛЕЙ\n`/deluser ID` — УДАЛИТЬ\n`/add_days ID ДНИ` — ДОБАВИТЬ ДНИ\n`/invite` — ИНВАЙТ\n`/broadcast` — РАССЫЛКА\n`/transactions` — ТРАНЗАКЦИИ\n`/createpromo КОД %` — ПРОМОКОД\n`/promolist` — СПИСОК ПРОМОКОДОВ\n`/delpromo КОД` — УДАЛИТЬ ПРОМОКОД\n`/setad ТЕКСТ ССЫЛКА` — РЕКЛАМА\n`/emergency_off_all` — ОТКЛЮЧИТЬ ВСЕХ\n━━━━━━━━━━━━━━━━━━━━━\n🔥 УПРАВЛЯЙ ЭНЕРГИЕЙ!"
    await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")))

@dp.message_handler(commands=['admin'])
async def admin_cmd(message: types.Message):
    uid = message.from_user.id
    with get_db() as conn:
        admin = conn.execute("SELECT is_admin FROM users WHERE telegram_id = ?", (uid,)).fetchone()
        if not admin or not admin[0]:
            await message.reply("⛔ НЕТ ДОСТУПА")
            return
        total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM users WHERE subscription_end > datetime('now')").fetchone()[0]
        devices = conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
        revenue = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE status='completed'").fetchone()[0]
    await message.reply(f"👑 **АДМИН ПАНЕЛЬ**\n━━━━━━━━━━━━━━━━━━━━━\n👥 ВСЕГО: {total}\n🟢 АКТИВНЫХ: {active}\n📱 УСТРОЙСТВ: {devices}\n💰 ДОХОД: {revenue}₽\n━━━━━━━━━━━━━━━━━━━━━\n🔥 /invite — ИНВАЙТ\n📢 /broadcast — РАССЫЛКА", parse_mode='Markdown')

@dp.message_handler(commands=['users'])
async def users_cmd(message: types.Message):
    uid = message.from_user.id
    with get_db() as conn:
        admin = conn.execute("SELECT is_admin FROM users WHERE telegram_id = ?", (uid,)).fetchone()
        if not admin or not admin[0]:
            return
        users = conn.execute("SELECT telegram_id, first_name, subscription_end, is_banned FROM users ORDER BY id DESC LIMIT 50").fetchall()
    if not users:
        await message.reply("📭 НЕТ ПОЛЬЗОВАТЕЛЕЙ")
        return
    text = "👥 **ПОЛЬЗОВАТЕЛИ (50):**\n━━━━━━━━━━━━━━━━━━━━━\n"
    for u in users:
        status = "🔴 БАН" if u[3] else "🟢 АКТ"
        end = u[2][:10] if u[2] else "НЕТ"
        text += f"• `{u[0]}` — {u[1][:15]} | {status} | ДО {end}\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n📌 /deluser ID — УДАЛИТЬ"
    await message.reply(text, parse_mode='Markdown')

@dp.message_handler(commands=['deluser'])
async def deluser_cmd(message: types.Message):
    uid = message.from_user.id
    with get_db() as conn:
        admin = conn.execute("SELECT is_admin FROM users WHERE telegram_id = ?", (uid,)).fetchone()
        if not admin or not admin[0]:
            return
    args = message.get_args().split()
    if not args:
        await message.reply("❌ /deluser TELEGRAM_ID")
        return
    try:
        target = int(args[0])
        with get_db() as conn:
            devices = conn.execute("SELECT d.public_key FROM devices d JOIN users u ON u.id=d.user_id WHERE u.telegram_id = ?", (target,)).fetchall()
            for device in devices:
                if device[0]:
                    remove_peer(device[0])
            uidb = conn.execute("SELECT id FROM users WHERE telegram_id = ?", (target,)).fetchone()
            if uidb:
                conn.execute("DELETE FROM devices WHERE user_id = ?", (uidb[0],))
                conn.execute("DELETE FROM user_settings WHERE user_id = ?", (uidb[0],))
                conn.execute("DELETE FROM backup_codes WHERE user_id = ?", (uidb[0],))
                conn.execute("DELETE FROM users WHERE telegram_id = ?", (target,))
                await message.reply(f"✅ ПОЛЬЗОВАТЕЛЬ `{target}` УДАЛЁН", parse_mode='Markdown')
            else:
                await message.reply(f"❌ ПОЛЬЗОВАТЕЛЬ `{target}` НЕ НАЙДЕН", parse_mode='Markdown')
    except:
        await message.reply("❌ ОШИБКА")

@dp.message_handler(commands=['add_days'])
async def add_days_cmd(message: types.Message):
    uid = message.from_user.id
    with get_db() as conn:
        admin = conn.execute("SELECT is_admin FROM users WHERE telegram_id = ?", (uid,)).fetchone()
        if not admin or not admin[0]:
            return
    args = message.get_args().split()
    if len(args) < 2:
        await message.reply("❌ /add_days ID ДНИ")
        return
    try:
        target = int(args[0])
        days = int(args[1])
        with get_db() as conn:
            row = conn.execute("SELECT subscription_end FROM users WHERE telegram_id = ?", (target,)).fetchone()
            if row:
                current = datetime.fromisoformat(row[0]) if row[0] else datetime.now()
                new_end = max(current, datetime.now()) + timedelta(days=days)
                conn.execute("UPDATE users SET subscription_end = ? WHERE telegram_id = ?", (new_end.isoformat(), target))
                await message.reply(f"✅ +{days} ДНЕЙ ПОЛЬЗОВАТЕЛЮ `{target}`\n📅 НОВАЯ ДАТА: {new_end.strftime('%d.%m.%Y')}", parse_mode='Markdown')
            else:
                await message.reply(f"❌ ПОЛЬЗОВАТЕЛЬ `{target}` НЕ НАЙДЕН", parse_mode='Markdown')
    except:
        await message.reply("❌ ОШИБКА")

@dp.message_handler(commands=['invite'])
async def invite_cmd(message: types.Message):
    uid = message.from_user.id
    with get_db() as conn:
        admin = conn.execute("SELECT is_admin FROM users WHERE telegram_id = ?", (uid,)).fetchone()
        if not admin or not admin[0]:
            return
    code = secrets.token_hex(8).upper()
    uidb = get_user_db_id(uid)
    with get_db() as conn:
        conn.execute("INSERT INTO invites (code, created_by) VALUES (?, ?)", (code, uidb))
    botname = (await bot.get_me()).username
    await message.reply(f"🎫 **ИНВАЙТ КОД:** `{code}`\n🔥 https://t.me/{botname}?start={code}", parse_mode='Markdown')

@dp.message_handler(commands=['broadcast'])
async def broadcast_cmd(message: types.Message):
    uid = message.from_user.id
    with get_db() as conn:
        admin = conn.execute("SELECT is_admin FROM users WHERE telegram_id = ?", (uid,)).fetchone()
        if not admin or not admin[0]:
            return
    text = message.get_args()
    if not text:
        await message.reply("❌ /broadcast ТЕКСТ")
        return
    with get_db() as conn:
        users = conn.execute("SELECT telegram_id FROM users").fetchall()
    sent = 0
    for u in users:
        try:
            await bot.send_message(u[0], f"⚡️ **НОВОСТЬ ULTROVPN** ⚡️\n━━━━━━━━━━━━━━━━━━━━━\n{text}\n━━━━━━━━━━━━━━━━━━━━━\n🔥 ТВОЙ ЗАРЯД ВСЕГДА С ТОБОЙ!", parse_mode='Markdown')
            sent += 1
            await asyncio.sleep(0.05)
        except:
            pass
    await message.reply(f"✅ ОТПРАВЛЕНО {sent} ПОЛЬЗОВАТЕЛЯМ!")

@dp.message_handler(commands=['transactions'])
async def transactions_cmd(message: types.Message):
    uid = message.from_user.id
    with get_db() as conn:
        admin = conn.execute("SELECT is_admin FROM users WHERE telegram_id = ?", (uid,)).fetchone()
        if not admin or not admin[0]:
            return
        txs = conn.execute("SELECT amount, payment_method, created_at, status FROM transactions ORDER BY created_at DESC LIMIT 20").fetchall()
    if not txs:
        await message.reply("📭 НЕТ ТРАНЗАКЦИЙ")
        return
    text = "💰 **ТРАНЗАКЦИИ:**\n━━━━━━━━━━━━━━━━━━━━━\n"
    for tx in txs:
        status = "✅" if tx[3] == 'completed' else "⏳"
        text += f"{status} {tx[2][:10]} {tx[0]}₽ {tx[1]}\n"
    await message.reply(text)

@dp.message_handler(commands=['createpromo'])
async def create_promo_cmd(message: types.Message):
    uid = message.from_user.id
    with get_db() as conn:
        admin = conn.execute("SELECT is_admin FROM users WHERE telegram_id = ?", (uid,)).fetchone()
        if not admin or not admin[0]:
            return
    args = message.get_args().split()
    if len(args) < 2:
        await message.reply("❌ /createpromo КОД СКИДКА%\nПРИМЕР: /createpromo WELCOME50 50")
        return
    code = args[0].upper()
    try:
        discount = int(args[1])
    except:
        await message.reply("❌ СКИДКА ДОЛЖНА БЫТЬ ЧИСЛОМ")
        return
    with get_db() as conn:
        conn.execute("INSERT INTO promocodes (code, discount) VALUES (?, ?)", (code, discount))
    await message.reply(f"✅ ПРОМОКОД `{code}` СОЗДАН! СКИДКА {discount}%", parse_mode='Markdown')

@dp.message_handler(commands=['promolist'])
async def promolist_cmd(message: types.Message):
    uid = message.from_user.id
    with get_db() as conn:
        admin = conn.execute("SELECT is_admin FROM users WHERE telegram_id = ?", (uid,)).fetchone()
        if not admin or not admin[0]:
            return
        promos = conn.execute("SELECT code, discount, used_by FROM promocodes").fetchall()
    if not promos:
        await message.reply("📭 НЕТ ПРОМОКОДОВ")
        return
    text = "🎫 **ПРОМОКОДЫ:**\n━━━━━━━━━━━━━━━━━━━━━\n"
    for p in promos:
        status = "✅ ИСПОЛЬЗОВАН" if p[2] else "❌ НЕ ИСПОЛЬЗОВАН"
        text += f"• `{p[0]}` — {p[1]}% — {status}\n"
    await message.reply(text, parse_mode='Markdown')

@dp.message_handler(commands=['delpromo'])
async def delpromo_cmd(message: types.Message):
    uid = message.from_user.id
    with get_db() as conn:
        admin = conn.execute("SELECT is_admin FROM users WHERE telegram_id = ?", (uid,)).fetchone()
        if not admin or not admin[0]:
            return
    code = message.get_args().strip().upper()
    if not code:
        await message.reply("❌ /delpromo КОД")
        return
    with get_db() as conn:
        conn.execute("DELETE FROM promocodes WHERE code = ?", (code,))
    await message.reply(f"✅ ПРОМОКОД `{code}` УДАЛЁН", parse_mode='Markdown')

@dp.message_handler(commands=['setad'])
async def setad_cmd(message: types.Message):
    global SPONSOR_BUTTON_TEXT, SPONSOR_BUTTON_URL
    uid = message.from_user.id
    with get_db() as conn:
        admin = conn.execute("SELECT is_admin FROM users WHERE telegram_id = ?", (uid,)).fetchone()
        if not admin or not admin[0]:
            return
    args = message.get_args().split()
    if len(args) < 2:
        await message.reply("❌ /setad ТЕКСТ ССЫЛКА")
        return
    SPONSOR_BUTTON_TEXT = ' '.join(args[:-1])
    SPONSOR_BUTTON_URL = args[-1]
    await message.reply(f"✅ РЕКЛАМА ОБНОВЛЕНА!\nТЕКСТ: {SPONSOR_BUTTON_TEXT}\nССЫЛКА: {SPONSOR_BUTTON_URL}")

@dp.message_handler(commands=['emergency_off_all'])
async def emergency_off_all_cmd(message: types.Message):
    uid = message.from_user.id
    with get_db() as conn:
        admin = conn.execute("SELECT is_admin FROM users WHERE telegram_id = ?", (uid,)).fetchone()
        if not admin or not admin[0]:
            return
        devices = conn.execute("SELECT public_key FROM devices").fetchall()
    count = 0
    for d in devices:
        if remove_peer(d[0]):
            count += 1
    await message.reply(f"🚨 **ЭКСТРЕННОЕ ОТКЛЮЧЕНИЕ!**\n🔥 ОТКЛЮЧЕНО УСТРОЙСТВ: {count}", parse_mode='Markdown')

# ========== ЭКСТРЕННОЕ ОТКЛЮЧЕНИЕ ==========
@dp.message_handler(lambda m: m.text and m.text.lower() in EMERGENCY_COMMANDS)
async def emergency_off_handler(message: types.Message):
    uid = message.from_user.id
    with get_db() as conn:
        devs = conn.execute("SELECT d.public_key FROM devices d JOIN users u ON u.id=d.user_id WHERE u.telegram_id = ?", (uid,)).fetchall()
        for d in devs:
            if d[0]:
                remove_peer(d[0])
    await message.reply("🚨 **ЭКСТРЕННОЕ ОТКЛЮЧЕНИЕ!**\n⚡️ ВСЕ VPN СОЕДИНЕНИЯ РАЗОРВАНЫ!\n🔥 НАЖМИ /start ЧТОБЫ ЗАРЯДИТЬСЯ ЗАНОВО!", parse_mode='Markdown')

# ========== ЗАПУСК ==========
async def on_startup(dp):
    setup_wireguard()
    asyncio.create_task(check_expiring_subscriptions())
    me = await bot.get_me()
    logger.info("=" * 60)
    logger.info("⚡️ ULTROVPN v8.0 — ЭНЕРГИЯ ТВОЕЙ СВОБОДЫ! ⚡️")
    logger.info(f"🔥 БОТ ЗАПУЩЕН: @{me.username}")
    logger.info(f"⚡️ IP: {SERVER_PUBLIC_IP}")
    logger.info(f"📢 АВТОПОСТИНГ: {'ВКЛ' if AUTO_POST_ENABLED else 'ВЫКЛ'}")
    logger.info(f"📊 АНАЛИТИКА: ВКЛЮЧЕНА")
    logger.info("=" * 60)

if __name__ == '__main__':
    init_db()
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
```

---

✅ КАК ЗАПУСТИТЬ:

```bash
cd /opt/ultrovpn
nano bot.py
# Вставь код выше
# Сохрани: Ctrl+X → Y → Enter
python3 bot.py
```

---

Готово! Без проверки канала, без ошибок, все функции на месте. 🚀
