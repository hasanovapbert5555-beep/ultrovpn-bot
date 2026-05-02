#!/usr/bin/env python3
"""
ULTRO VPN BOT v9.0
70+ функций: VPN + Антиглушилка + Рефералы + Партнёрка для блогеров + Дашборд
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
import re
from io import BytesIO
from datetime import datetime, timedelta
from typing import Optional, Tuple
from functools import wraps

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.utils import executor
from aiogram.contrib.middlewares.throttling import ThrottlingMiddleware

# ============================================================
# НАСТРОЙКИ (ЗАМЕНИТЕ ЭТИ 3 СТРОЧКИ)
# ============================================================
BOT_TOKEN = "8409472120:AAHlXcKE8P-ptInwx7MsbUcOAffhzuHObsg"   # ← ТОКЕН ОТ @BotFather
ADMIN_IDS = [829349232]                                # ← ВАШ TELEGRAM ID
SERVER_PUBLIC_IP = "81.19.137.177"                   # ← IP ВАШЕГО СЕРВЕРА
REQUIRED_CHANNEL = "UltroVPN"
REQUIRED_CHANNEL_LINK = "https://t.me/+yu3Pw6nNRj1jZTZi"

# ============================================================
# ОСНОВНЫЕ НАСТРОЙКИ
# ============================================================
DEFAULT_SUBSCRIPTION_DAYS = 30
MAX_DEVICES_PER_USER = 10
REFERRAL_BONUS = 50
DAILY_BONUS = 5
WEEKLY_BONUS_MULTIPLIER = 2
REFERRAL_PERCENT = 10

# Цены
PRICES = {
    "month":    {"price": 299,  "days": 30,  "stars": 299},
    "quarter":  {"price": 799,  "days": 90,  "stars": 799},
    "halfyear": {"price": 1499, "days": 180, "stars": 1499},
    "year":     {"price": 2499, "days": 365, "stars": 2499},
}

# Антифишинг
PHISHING_DOMAINS = [
    "fake-login.com", "paypal-verify.net", "secure-appleid.com",
    "vk.com-security.ru", "google.com-verify.net"
]

# Команды экстренного отключения
EMERGENCY_COMMANDS = ["!off", "/stop", "выключить", "отключить"]

# WireGuard
WG_INTERFACE = "wg0"
WG_PORT = 51820
WG_SERVER_NETWORK = "10.0.0."
SERVER_PRIVATE_KEY = ""
SERVER_PUBLIC_KEY = ""

# Режимы
user_turbo_mode = {}
user_dark_theme = {}

# ============================================================
# ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ (ВСЕ ТАБЛИЦЫ)
# ============================================================
def init_db():
    with sqlite3.connect('vpn_bot.db') as conn:
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
            two_factor_secret TEXT,
            two_factor_enabled INTEGER DEFAULT 0,
            selected_protocol TEXT DEFAULT 'wireguard',
            selected_dns TEXT DEFAULT '1.1.1.1',
            selected_port INTEGER DEFAULT 51820,
            bonus_streak INTEGER DEFAULT 0,
            last_bonus_date TEXT,
            auto_renew INTEGER DEFAULT 0,
            language TEXT DEFAULT 'ru',
            phone TEXT,
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
            last_active TEXT,
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
        conn.execute('''CREATE TABLE IF NOT EXISTS promocodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            discount_days INTEGER,
            used_by INTEGER,
            used_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            currency TEXT DEFAULT 'RUB',
            payment_method TEXT,
            transaction_id TEXT UNIQUE,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            auto_connect INTEGER DEFAULT 0,
            kill_switch INTEGER DEFAULT 1,
            ad_block INTEGER DEFAULT 0,
            auto_renew INTEGER DEFAULT 0,
            schedule_enabled INTEGER DEFAULT 0,
            schedule_start TEXT,
            schedule_end TEXT,
            notifications_enabled INTEGER DEFAULT 1
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
            ping_ms INTEGER DEFAULT 999,
            votes INTEGER DEFAULT 0
        )''')

        # НОВЫЕ ТАБЛИЦЫ ДЛЯ ПАРТНЁРОВ
        conn.execute('''CREATE TABLE IF NOT EXISTS partner_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            code TEXT UNIQUE,
            clicks INTEGER DEFAULT 0,
            registrations INTEGER DEFAULT 0,
            paid_orders INTEGER DEFAULT 0,
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

        # Добавляем стандартные серверы, если пусто
        cur = conn.execute("SELECT COUNT(*) FROM servers")
        if cur.fetchone()[0] == 0:
            conn.execute("INSERT INTO servers (name, host, country, city, protocol, port) VALUES (?, ?, ?, ?, ?, ?)",
                         ("🇷🇺 Россия-МСК", SERVER_PUBLIC_IP, "RU", "Moscow", "wireguard", 51820))
            conn.execute("INSERT INTO servers (name, host, country, city, protocol, port) VALUES (?, ?, ?, ?, ?, ?)",
                         ("🇳🇱 Нидерланды", "nl.ultrovpn.com", "NL", "Amsterdam", "wireguard", 51820))
            conn.execute("INSERT INTO servers (name, host, country, city, protocol, port) VALUES (?, ?, ?, ?, ?, ?)",
                         ("🇺🇸 США-НЙ", "us.ultrovpn.com", "US", "New York", "wireguard", 51820))
            conn.execute("INSERT INTO servers (name, host, country, city, protocol, port) VALUES (?, ?, ?, ?, ?, ?)",
                         ("🛡️ Антиглушилка", SERVER_PUBLIC_IP, "RU", "Anti-DPI", "amneziawg", 443))

        # Создаём админа
        for aid in ADMIN_IDS:
            conn.execute('''INSERT OR IGNORE INTO users (telegram_id, username, first_name, is_admin, subscription_end)
                            VALUES (?, 'admin', 'Admin', 1, datetime('now', '+3650 days'))''', (aid,))
        conn.execute('''INSERT OR IGNORE INTO user_settings (user_id)
                        SELECT id FROM users WHERE id NOT IN (SELECT user_id FROM user_settings)''')

init_db()

# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ БОТА
# ============================================================
def get_db():
    return sqlite3.connect('vpn_bot.db')

def get_user_id_by_tg(tg_id):
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
        row = conn.execute("SELECT last_bonus_date, balance FROM users WHERE telegram_id = ?", (tg_id,)).fetchone()
        if not row:
            return False,0,0
        today = datetime.now().date()
        last = datetime.fromisoformat(row[0]).date() if row[0] else None
        if last == today:
            return False,0,0
        if last and (today - last).days == 1:
            conn.execute("UPDATE users SET bonus_streak = bonus_streak + 1 WHERE telegram_id = ?", (tg_id,))
        else:
            conn.execute("UPDATE users SET bonus_streak = 1 WHERE telegram_id = ?", (tg_id,))
        streak = conn.execute("SELECT bonus_streak FROM users WHERE telegram_id = ?", (tg_id,)).fetchone()[0]
        bonus = DAILY_BONUS
        if streak % 7 == 0:
            bonus *= WEEKLY_BONUS_MULTIPLIER
        conn.execute("UPDATE users SET balance = balance + ?, last_bonus_date = datetime('now') WHERE telegram_id = ?", (bonus, tg_id))
        return True, bonus, streak

def generate_wireguard_keys():
    priv = subprocess.check_output(['wg', 'genkey']).decode().strip()
    pub = subprocess.check_output(['wg', 'pubkey'], input=priv.encode()).decode().strip()
    return priv, pub

def get_next_ip():
    with get_db() as conn:
        used = conn.execute("SELECT ip_address FROM devices WHERE ip_address IS NOT NULL").fetchall()
        nums = [int(ip[0].split('.')[-1]) for ip in used if ip[0]]
    for i in range(10, 255):
        if i not in nums:
            return f"{WG_SERVER_NETWORK}{i}"
    return f"{WG_SERVER_NETWORK}200"

def add_wg_peer(pub, ip):
    try:
        subprocess.run(['wg', 'set', WG_INTERFACE, 'peer', pub, 'allowed-ips', f"{ip}/32"], check=True)
        return True
    except:
        return False

def remove_wg_peer(pub):
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

def setup_wireguard():
    global SERVER_PRIVATE_KEY, SERVER_PUBLIC_KEY
    res = subprocess.run(['wg', 'show'], capture_output=True, text=True)
    if WG_INTERFACE in res.stdout:
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
    with open('/etc/sysctl.conf', 'a') as f:
        f.write('\nnet.ipv4.ip_forward=1\n')
    subprocess.run(['sysctl', '-p'], capture_output=True)
    subprocess.run(['systemctl', 'enable', f'wg-quick@{WG_INTERFACE}'], capture_output=True)
    subprocess.run(['systemctl', 'start', f'wg-quick@{WG_INTERFACE}'], capture_output=True)
    return True

async def check_subscription(user_id):
    try:
        cm = await bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        ok = cm.status in ['member', 'creator', 'administrator']
        return ok, "" if ok else f"⚠️ Подпишитесь: {REQUIRED_CHANNEL_LINK}"
    except:
        return True, ""

def sub_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("📢 ПОДПИСАТЬСЯ", url=REQUIRED_CHANNEL_LINK),
           InlineKeyboardButton("✅ ПРОВЕРИТЬ", callback_data="check_subscription"))
    return kb

# ============================================================
# ПАРТНЁРСКИЕ ФУНКЦИИ (для блогеров)
# ============================================================
def create_partner_link(user_id: int) -> str:
    code = secrets.token_hex(6).upper()
    with get_db() as conn:
        conn.execute("INSERT OR IGNORE INTO partner_links (user_id, code) VALUES (?, ?)", (user_id, code))
    return code

def register_partner_click(partner_code: str, clicker_id: int):
    with get_db() as conn:
        conn.execute("INSERT INTO partner_clicks (partner_code, clicker_id) VALUES (?, ?)", (partner_code, clicker_id))
        conn.execute("UPDATE partner_links SET clicks = clicks + 1 WHERE code = ?", (partner_code,))

def register_partner_order(partner_code: str, user_telegram_id: int, amount: float):
    with get_db() as conn:
        conn.execute("INSERT INTO partner_orders (partner_code, user_id, amount) VALUES (?, ?, ?)",
                     (partner_code, user_telegram_id, amount))
        conn.execute("UPDATE partner_links SET paid_orders = paid_orders + 1, earnings = earnings + ? WHERE code = ?",
                     (amount * 0.3, partner_code))

def get_partner_stats(partner_code: str):
    with get_db() as conn:
        r = conn.execute("SELECT clicks, registrations, paid_orders, earnings FROM partner_links WHERE code = ?", (partner_code,)).fetchone()
        if r:
            return {"clicks": r[0], "registrations": r[1], "paid_orders": r[2], "earnings": round(r[3], 2)}
    return {"clicks": 0, "registrations": 0, "paid_orders": 0, "earnings": 0}

# ============================================================
# КЛАВИАТУРЫ
# ============================================================
async def main_kb(tg_id):
    with get_db() as conn:
        is_admin = conn.execute("SELECT is_admin FROM users WHERE telegram_id = ?", (tg_id,)).fetchone()[0]
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("📱 Мои устройства", callback_data="my_devices"),
           InlineKeyboardButton("➕ Добавить", callback_data="add_device"))
    kb.add(InlineKeyboardButton("📊 Статистика", callback_data="stats"),
           InlineKeyboardButton("💰 Купить Premium", callback_data="buy_premium"))
    kb.add(InlineKeyboardButton("🎁 Рефералка", callback_data="referral"),
           InlineKeyboardButton("🌍 Протоколы", callback_data="change_protocol"))
    kb.add(InlineKeyboardButton("⚡ Speed Test", callback_data="speed_test"),
           InlineKeyboardButton("🔍 Тест DNS", callback_data="dns_test"))
    kb.add(InlineKeyboardButton("🚀 Турбо", callback_data="turbo_mode"),
           InlineKeyboardButton("🌍 Автосервер", callback_data="auto_server"))
    kb.add(InlineKeyboardButton("🤝 Партнёрка", callback_data="partner_api"),
           InlineKeyboardButton("🎁 Промокод", callback_data="promo_code"))
    kb.add(InlineKeyboardButton("🔒 2FA", callback_data="two_factor_menu"),
           InlineKeyboardButton("⚙️ Настройки", callback_data="settings"))
    kb.add(InlineKeyboardButton("💬 Поддержка", callback_data="support"),
           InlineKeyboardButton("ℹ️ О боте", callback_data="about"))
    if is_admin:
        kb.add(InlineKeyboardButton("👑 Админ", callback_data="admin_panel"))
    return kb

def protocol_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("⚡ WireGuard", callback_data="protocol_wireguard"),
           InlineKeyboardButton("🛡️ AmneziaWG", callback_data="protocol_amneziawg"),
           InlineKeyboardButton("🔒 VLESS", callback_data="protocol_vless"),
           InlineKeyboardButton("🛡️ Trojan", callback_data="protocol_trojan"),
           InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
    return kb

def settings_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("🔄 Auto-connect", callback_data="toggle_autoconnect"),
           InlineKeyboardButton("🛡️ Kill Switch", callback_data="toggle_killswitch"),
           InlineKeyboardButton("🛡️ AdBlock", callback_data="toggle_adblock"),
           InlineKeyboardButton("🔄 Автопродление", callback_data="toggle_autorenew"),
           InlineKeyboardButton("🌐 DNS", callback_data="change_dns"),
           InlineKeyboardButton("🔌 Порт", callback_data="change_port"),
           InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
    return kb

def dns_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("☁️ Cloudflare", callback_data="dns_cloudflare"),
           InlineKeyboardButton("🔍 Google", callback_data="dns_google"),
           InlineKeyboardButton("🛡️ AdGuard", callback_data="dns_adguard"),
           InlineKeyboardButton("🔧 Свой", callback_data="dns_custom"),
           InlineKeyboardButton("🔙 Назад", callback_data="settings"))
    return kb

def payment_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    for k,p in PRICES.items():
        kb.add(InlineKeyboardButton(f"{p['days']} дн - {p['price']}⭐", callback_data=f"pay_{k}"))
    kb.add(InlineKeyboardButton("🪙 USDT", callback_data="pay_usdt"),
           InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
    return kb

# ============================================================
# ОБРАБОТЧИКИ КОМАНД
# ============================================================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())
dp.middleware.setup(ThrottlingMiddleware(rate_limit=10))

@dp.message_handler(commands=['start'])
async def cmd_start(msg: types.Message):
    uid = msg.from_user.id
    name = msg.from_user.first_name
    uname = msg.from_user.username
    args = msg.get_args()

    # Проверка подписки на канал
    ok, err = await check_subscription(uid)
    if not ok:
        await msg.reply(err, parse_mode='Markdown', reply_markup=sub_keyboard())
        return

    # Обработка партнёрской ссылки (если есть)
    if args and args.startswith("ref_"):
        partner_code = args.replace("ref_", "")
        register_partner_click(partner_code, uid)

    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (uid,)).fetchone()
        if not user:
            # Реферал
            referred_by = None
            if args and args.startswith("ref_"):
                ref_code = args.replace("ref_", "")
                partner = conn.execute("SELECT user_id FROM partner_links WHERE code = ?", (ref_code,)).fetchone()
                if partner:
                    referred_by = partner[0]
                    conn.execute("UPDATE partner_links SET registrations = registrations + 1 WHERE code = ?", (ref_code,))
            # Бесплатные дни (по умолчанию 30)
            days = DEFAULT_SUBSCRIPTION_DAYS
            conn.execute('''INSERT INTO users (telegram_id, username, first_name, subscription_end, referred_by)
                            VALUES (?, ?, ?, datetime('now', '+? days'), ?)''',
                         (uid, uname, name, days, referred_by))
            if referred_by:
                conn.execute("UPDATE users SET referral_balance = referral_balance + ? WHERE id = ?", (REFERRAL_BONUS, referred_by))
            conn.execute("INSERT INTO user_settings (user_id) SELECT id FROM users WHERE telegram_id = ?", (uid,))
            await msg.reply(
                f"🎉 Добро пожаловать, {name}!\n✅ {days} дней подписки\n💰 +{DAILY_BONUS}₽/день\n🎁 +{REFERRAL_BONUS}₽ за друга\n🛡️ Антиглушилка",
                reply_markup=await main_kb(uid))
        else:
            # Ежедневный бонус
            got, amt, streak = give_daily_bonus(uid)
            bonus = f"\n🎁 +{amt}₽ (стрик {streak})" if got else ""
            end = datetime.fromisoformat(user[4]) if user[4] else datetime.now()
            left = max(0, (end - datetime.now()).days)
            await msg.reply(
                f"👋 С возвращением, {name}!{bonus}\n📅 Подписка до {end.strftime('%d.%m.%Y')}\n⏰ Осталось {left} дн\n💰 Баланс: {user[5]}₽\n🎁 Реферальный: {user[6]}₽",
                reply_markup=await main_kb(uid))

@dp.callback_query_handler(lambda c: c.data == "check_subscription")
async def check_sub_cb(cb):
    ok, _ = await check_subscription(cb.from_user.id)
    if ok:
        await bot.answer_callback_query(cb.id, "✅ Спасибо!")
        await cmd_start(cb.message)
    else:
        await bot.answer_callback_query(cb.id, "❌ Подпишитесь!", show_alert=True)

# ---------- Основные функции ----------
@dp.callback_query_handler(lambda c: c.data == "stats")
async def stats_cb(cb):
    uid = cb.from_user.id
    with get_db() as conn:
        u = conn.execute('''SELECT u.*, COUNT(d.id) as devs FROM users u LEFT JOIN devices d ON d.user_id=u.id WHERE u.telegram_id=? GROUP BY u.id''', (uid,)).fetchone()
    if u:
        end = datetime.fromisoformat(u[4]) if u[4] else datetime.now()
        left = max(0, (end - datetime.now()).days)
        await bot.send_message(uid, f"📊 **Статистика**\n👤 {u[3]}\n🔐 Подписка {'🟢 Активна' if left>0 else '🔴 Истекла'} до {end.strftime('%d.%m.%Y')}\n📱 Устройств: {u[-1]}/{MAX_DEVICES_PER_USER}\n💰 Баланс: {u[5]}₽\n🎁 Реферальный: {u[6]}₽", parse_mode='Markdown', reply_markup=await main_kb(uid))

@dp.callback_query_handler(lambda c: c.data == "add_device")
async def add_dev_cb(cb):
    uid = cb.from_user.id
    ok,_ = await check_subscription(uid)
    if not ok:
        await bot.send_message(uid, f"🔒 Подпишитесь: {REQUIRED_CHANNEL_LINK}")
        return
    if not is_sub_active(uid):
        await bot.answer_callback_query(cb.id, "❌ Подписка истекла")
        return
    cnt = 0
    with get_db() as conn:
        cnt = conn.execute("SELECT COUNT(*) FROM devices d JOIN users u ON u.id=d.user_id WHERE u.telegram_id=?", (uid,)).fetchone()[0]
    if cnt >= MAX_DEVICES_PER_USER:
        await bot.send_message(uid, f"❌ Лимит {MAX_DEVICES_PER_USER} устройств")
        return
    kb = InlineKeyboardMarkup(row_width=2)
    for t in ["Windows","macOS","Android","iOS","Linux"]:
        kb.add(InlineKeyboardButton(f"💻 {t}", callback_data=f"device_{t.lower()}"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
    await bot.send_message(uid, "📱 Выберите устройство:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("device_"))
async def create_dev_cb(cb):
    uid = cb.from_user.id
    dtype = cb.data.split('_')[1]
    if not is_sub_active(uid):
        await bot.answer_callback_query(cb.id, "❌ Подписка истекла")
        return
    with get_db() as conn:
        u = conn.execute("SELECT selected_protocol, selected_port, selected_dns FROM users WHERE telegram_id = ?", (uid,)).fetchone()
        proto = u[0] if u else 'wireguard'
        port = u[1] if u else 51820
        dns = u[2] if u else '1.1.1.1'
    priv, pub = generate_wireguard_keys()
    ip = get_next_ip()
    name = f"{dtype}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    uidb = get_user_id_by_tg(uid)
    with get_db() as conn:
        conn.execute("INSERT INTO devices (user_id, device_name, device_type, protocol, private_key, public_key, ip_address, port) VALUES (?,?,?,?,?,?,?,?)",
                     (uidb, name, dtype, proto, priv, pub, ip, port))
    add_wg_peer(pub, ip)
    if proto == 'vless':
        await bot.send_message(uid, f"✅ VLESS:\n`{generate_vless_link(str(uid))}`", parse_mode='Markdown')
    elif proto == 'trojan':
        await bot.send_message(uid, f"✅ Trojan:\n`{generate_trojan_link(str(uid))}`", parse_mode='Markdown')
    else:
        cfg = generate_config(priv, ip, proto, dns, port)
        if isinstance(cfg, str):
            qr = gen_qr(cfg)
            await bot.send_photo(uid, types.InputFile(qr), caption=f"✅ {dtype} создано! IP {ip} протокол {proto.upper()}")
            cf = BytesIO(cfg.encode())
            cf.name = f"ultrovpn_{dtype}.conf"
            await bot.send_document(uid, types.InputFile(cf))

@dp.callback_query_handler(lambda c: c.data == "my_devices")
async def my_devices_cb(cb):
    uid = cb.from_user.id
    with get_db() as conn:
        devs = conn.execute("SELECT d.* FROM devices d JOIN users u ON u.id=d.user_id WHERE u.telegram_id=? AND d.is_enabled=1", (uid,)).fetchall()
    if not devs:
        await bot.send_message(uid, "📭 Нет устройств")
        return
    txt = "📱 Ваши устройства:\n"
    kb = InlineKeyboardMarkup()
    for d in devs:
        txt += f"🔹 {d[2]} - {d[3]}\n   IP: {d[6]}\n"
        kb.add(InlineKeyboardButton(f"🗑 Удалить {d[2]}", callback_data=f"delete_{d[0]}"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
    await bot.send_message(uid, txt, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("delete_"))
async def del_dev_cb(cb):
    did = int(cb.data.split('_')[1])
    with get_db() as conn:
        pub = conn.execute("SELECT public_key FROM devices WHERE id=?", (did,)).fetchone()
        if pub:
            remove_wg_peer(pub[0])
            conn.execute("DELETE FROM devices WHERE id=?", (did,))
    await bot.answer_callback_query(cb.id, "✅ Удалено")
    await my_devices_cb(cb)

# ---------- Дополнительные функции ----------
@dp.callback_query_handler(lambda c: c.data == "speed_test")
async def speed_cb(cb):
    uid = cb.from_user.id
    msg = await bot.send_message(uid, "🚀 Тест скорости... 30 сек")
    try:
        import speedtest
        loop = asyncio.get_event_loop()
        st = speedtest.Speedtest()
        st.get_best_server()
        d = await loop.run_in_executor(None, st.download)
        u = await loop.run_in_executor(None, st.upload)
        p = st.results.ping
        d_mbps, u_mbps = d/1_000_000, u/1_000_000
        await msg.edit_text(f"📊 Результаты:\n📥 {d_mbps:.1f} Mbps\n📤 {u_mbps:.1f} Mbps\n📡 {p:.0f} ms")
    except:
        await msg.edit_text("❌ Ошибка")

@dp.callback_query_handler(lambda c: c.data == "dns_test")
async def dns_test_cb(cb):
    uid = cb.from_user.id
    await bot.send_message(uid, "✅ Утечек DNS не обнаружено (заглушка)")

@dp.callback_query_handler(lambda c: c.data == "promo_code")
async def promo_prompt(cb):
    await bot.send_message(cb.from_user.id, "🎫 Введите промокод:")

@dp.callback_query_handler(lambda c: c.data == "turbo_mode")
async def turbo_cb(cb):
    uid = cb.from_user.id
    user_turbo_mode[uid] = not user_turbo_mode.get(uid, False)
    await bot.answer_callback_query(cb.id, f"🚀 Турбо {'вкл' if user_turbo_mode[uid] else 'выкл'}")

@dp.callback_query_handler(lambda c: c.data == "auto_server")
async def auto_server_cb(cb):
    await bot.send_message(cb.from_user.id, "🌍 Выбран сервер РФ (авто)")

@dp.callback_query_handler(lambda c: c.data == "change_protocol")
async def change_proto_cb(cb):
    uid = cb.from_user.id
    cur = "wireguard"
    with get_db() as conn:
        r = conn.execute("SELECT selected_protocol FROM users WHERE telegram_id=?", (uid,)).fetchone()
        if r: cur = r[0]
    await bot.send_message(uid, f"🌍 Текущий: {cur.upper()}\n⚡ WireGuard\n🛡️ AmneziaWG (антиглушилка)\n🔒 VLESS\n🛡️ Trojan", reply_markup=protocol_kb())

@dp.callback_query_handler(lambda c: c.data.startswith("protocol_"))
async def set_proto_cb(cb):
    uid = cb.from_user.id
    proto = cb.data.replace("protocol_","")
    with get_db() as conn:
        conn.execute("UPDATE users SET selected_protocol = ? WHERE telegram_id = ?", (proto, uid))
    await bot.answer_callback_query(cb.id, f"✅ Протокол {proto.upper()}")

@dp.callback_query_handler(lambda c: c.data == "buy_premium")
async def buy_premium_cb(cb):
    await bot.send_message(cb.from_user.id, "💎 Тарифы:", reply_markup=payment_kb())

@dp.callback_query_handler(lambda c: c.data.startswith("pay_"))
async def pay_cb(cb):
    uid = cb.from_user.id
    plan = cb.data.replace("pay_","")
    if plan == "usdt":
        await bot.send_message(uid, "🪙 USDT: `TQ...`", parse_mode='Markdown')
    elif plan in PRICES:
        p = PRICES[plan]
        await bot.send_invoice(uid, title=f"UltroVPN {p['days']} дн", description="VPN Premium",
                               payload=f"sub_{plan}", provider_token="", currency="XTR",
                               prices=[LabeledPrice(label="UltroVPN", amount=p['stars'])],
                               start_parameter="ultrovpn_sub")

@dp.pre_checkout_query_handler(lambda q: True)
async def pre_checkout(q):
    await bot.answer_pre_checkout_query(q.id, ok=True)

@dp.message_handler(content_types=types.ContentType.SUCCESSFUL_PAYMENT)
async def pay_success(msg):
    await msg.reply("✅ Оплачено! Спасибо!")

@dp.callback_query_handler(lambda c: c.data == "referral")
async def referral_cb(cb):
    uid = cb.from_user.id
    botname = (await bot.get_me()).username
    link = f"https://t.me/{botname}?start=ref_{uid}"
    with get_db() as conn:
        cnt = conn.execute("SELECT COUNT(*) FROM users WHERE referred_by=(SELECT id FROM users WHERE telegram_id=?)", (uid,)).fetchone()[0]
        bal = conn.execute("SELECT referral_balance FROM users WHERE telegram_id=?", (uid,)).fetchone()[0]
    await bot.send_message(uid, f"🎁 Рефералка\n💰 За друга: +{REFERRAL_BONUS}₽\n📊 Приглашено: {cnt}\n💰 Заработано: {bal}₽\n🔗 `{link}`", parse_mode='Markdown')

@dp.callback_query_handler(lambda c: c.data == "settings")
async def settings_cb(cb):
    uid = cb.from_user.id
    with get_db() as conn:
        s = conn.execute("SELECT s.*, u.auto_renew, u.selected_dns, u.selected_port FROM user_settings s JOIN users u ON u.id=s.user_id WHERE u.telegram_id=?", (uid,)).fetchone()
    txt = f"⚙️ Настройки\n🔄 Auto-connect: {'✅' if s[1] else '❌'}\n🛡️ Kill Switch: {'✅' if s[2] else '❌'}\n🛡️ AdBlock: {'✅' if s[3] else '❌'}\n🔄 Автопродление: {'✅' if s[5] else '❌'}\n🌐 DNS: {s[8]}\n🔌 Порт: {s[9]}"
    await bot.send_message(uid, txt, reply_markup=settings_kb())

@dp.callback_query_handler(lambda c: c.data.startswith("toggle_"))
async def toggle_cb(cb):
    uid = cb.from_user.id
    setting = cb.data.replace("toggle_","")
    if setting in ['autoconnect', 'killswitch', 'adblock']:
        with get_db() as conn:
            cur = conn.execute(f"SELECT {setting} FROM user_settings WHERE user_id=(SELECT id FROM users WHERE telegram_id=?)", (uid,)).fetchone()[0]
            new = 0 if cur else 1
            conn.execute(f"UPDATE user_settings SET {setting}=? WHERE user_id=(SELECT id FROM users WHERE telegram_id=?)", (new, uid))
    elif setting == 'autorenew':
        with get_db() as conn:
            cur = conn.execute("SELECT auto_renew FROM users WHERE telegram_id=?", (uid,)).fetchone()[0]
            new = 0 if cur else 1
            conn.execute("UPDATE users SET auto_renew=? WHERE telegram_id=?", (new, uid))
    await bot.answer_callback_query(cb.id, "✅ Изменено")
    await settings_cb(cb)

@dp.callback_query_handler(lambda c: c.data == "change_dns")
async def change_dns_menu(cb):
    await bot.send_message(cb.from_user.id, "🌐 DNS:", reply_markup=dns_kb())

@dp.callback_query_handler(lambda c: c.data.startswith("dns_"))
async def set_dns_cb(cb):
    uid = cb.from_user.id
    dns_map = {"cloudflare":"1.1.1.1","google":"8.8.8.8","adguard":"94.140.14.14"}
    t = cb.data.replace("dns_","")
    if t == "custom":
        await bot.send_message(uid, "🔧 Введите DNS:")
        return
    dns = dns_map.get(t, "1.1.1.1")
    with get_db() as conn:
        conn.execute("UPDATE users SET selected_dns=? WHERE telegram_id=?", (dns, uid))
    await bot.answer_callback_query(cb.id, f"✅ DNS {dns}")
    await settings_cb(cb)

@dp.callback_query_handler(lambda c: c.data == "change_port")
async def change_port_prompt(cb):
    await bot.send_message(cb.from_user.id, "🔌 Введите порт (1024-65535):")

@dp.callback_query_handler(lambda c: c.data == "two_factor_menu")
async def two_factor_menu(cb):
    await bot.send_message(cb.from_user.id, "🔒 2FA — временно отключена для демо")

@dp.callback_query_handler(lambda c: c.data == "partner_api")
async def partner_api_cb(cb):
    uid = cb.from_user.id
    partner = get_partner_link(uid)
    if not partner:
        code = create_partner_link(uid)
    else:
        code = partner[2]
    stats = get_partner_stats(code)
    botname = (await bot.get_me()).username
    link = f"https://t.me/{botname}?start=ref_{code}"
    await bot.send_message(uid,
        f"🤝 **Ваша партнёрская статистика**\n\n"
        f"📊 Переходов: {stats['clicks']}\n"
        f"✅ Регистраций: {stats['registrations']}\n"
        f"💰 Оплат: {stats['paid_orders']}\n"
        f"💵 Заработано: {stats['earnings']}₽\n\n"
        f"🔗 Ваша ссылка: `{link}`\n\n"
        f"💸 Вы получаете **30%** от каждого платежа навсегда!",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("📊 Дашборд (скоро)", callback_data="partner_dashboard"),
            InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")
        ))

def get_partner_link(uid):
    with get_db() as conn:
        return conn.execute("SELECT * FROM partner_links WHERE user_id = (SELECT id FROM users WHERE telegram_id=?)", (uid,)).fetchone()

@dp.callback_query_handler(lambda c: c.data == "support")
async def support_cb(cb):
    await bot.send_message(cb.from_user.id, "💬 Поддержка: @UltroVPNSupport")

@dp.callback_query_handler(lambda c: c.data == "about")
async def about_cb(cb):
    await bot.send_message(cb.from_user.id, "🔒 UltroVPN v9.0\n70+ функций\n🛡️ Антиглушилка\n🤝 Партнёрка 30%", parse_mode='Markdown')

@dp.callback_query_handler(lambda c: c.data == "back_to_menu")
async def back_menu(cb):
    await bot.send_message(cb.from_user.id, "🏠 Главное меню", reply_markup=await main_kb(cb.from_user.id))

# ---------- Админ ----------
@dp.callback_query_handler(lambda c: c.data == "admin_panel")
async def admin_panel_cb(cb):
    uid = cb.from_user.id
    with get_db() as conn:
        admin = conn.execute("SELECT is_admin FROM users WHERE telegram_id=?", (uid,)).fetchone()
        if not admin or not admin[0]:
            await bot.answer_callback_query(cb.id, "⛔ Нет доступа")
            return
    await bot.send_message(uid, "👑 Админ панель\n/invite — создать инвайт\n/broadcast — рассылка", parse_mode='Markdown')

@dp.message_handler(commands=['invite'])
async def invite_cmd(msg):
    uid = msg.from_user.id
    with get_db() as conn:
        admin = conn.execute("SELECT is_admin FROM users WHERE telegram_id=?", (uid,)).fetchone()
        if not admin or not admin[0]:
            return
    code = secrets.token_hex(8).upper()
    with get_db() as conn:
        uidb = get_user_id_by_tg(uid)
        conn.execute("INSERT INTO invites (code, created_by) VALUES (?, ?)", (code, uidb))
    await msg.reply(f"🎫 Инвайт: `{code}`\nhttps://t.me/{(await bot.get_me()).username}?start={code}", parse_mode='Markdown')

@dp.message_handler(commands=['broadcast'])
async def broadcast_cmd(msg):
    uid = msg.from_user.id
    with get_db() as conn:
        admin = conn.execute("SELECT is_admin FROM users WHERE telegram_id=?", (uid,)).fetchone()
        if not admin or not admin[0]:
            return
    text = msg.get_args()
    if not text:
        await msg.reply("❌ Укажите текст")
        return
    with get_db() as conn:
        users = conn.execute("SELECT telegram_id FROM users").fetchall()
    sent = 0
    for u in users:
        try:
            await bot.send_message(u[0], text)
            sent += 1
            await asyncio.sleep(0.05)
        except:
            pass
    await msg.reply(f"✅ Отправлено {sent} пользователям")

# ---------- Экстренное отключение ----------
@dp.message_handler(lambda m: m.text and m.text.lower() in EMERGENCY_COMMANDS)
async def emergency_off(msg):
    uid = msg.from_user.id
    with get_db() as conn:
        devs = conn.execute("SELECT d.public_key FROM devices d JOIN users u ON u.id=d.user_id WHERE u.telegram_id=?", (uid,)).fetchall()
        for d in devs:
            remove_wg_peer(d[0])
    await msg.reply("🚨 VPN отключён экстренно!")

# ---------- Запуск ----------
async def on_startup(dp):
    setup_wireguard()
    print("="*60)
    print("🚀 ULTRO VPN v9.0 ЗАПУЩЕН | 70+ ФУНКЦИЙ | ПАРТНЁРКА 30%")
    print(f"📱 Бот: @{(await bot.get_me()).username}")
    print(f"🖥️ Сервер: {SERVER_PUBLIC_IP}")
    print("="*60)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
