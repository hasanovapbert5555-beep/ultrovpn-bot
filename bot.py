#!/usr/bin/env python3
import asyncio
import subprocess
import sqlite3
import qrcode
import secrets
import hashlib
import os
from io import BytesIO
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

# ========== НАСТРОЙКИ (ЗАМЕНИТЕ ТОКЕН) ==========
BOT_TOKEN = "8409472120:AAHlXcKE8P-ptInwx7MsbUcOAffhzuHObsg"  # ← ЗАМЕНИТЕ НА ВАШ ТОКЕН
ADMIN_IDS = [829349232]  # ← ЗАМЕНИТЕ НА ВАШ TELEGRAM ID
SERVER_PUBLIC_IP = "81.19.137.177"  # ← IP ВАШЕГО СЕРВЕРА
# =================================================

DEFAULT_SUBSCRIPTION_DAYS = 30
MAX_DEVICES_PER_USER = 5
REFERRAL_BONUS = 50
DAILY_BONUS = 5
WG_INTERFACE = "wg0"
WG_PORT = 51820
WG_SERVER_NETWORK = "10.0.0."

# ========== БАЗА ДАННЫХ ==========
def init_db():
    with sqlite3.connect('vpn_bot.db') as conn:
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
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            device_name TEXT,
            device_type TEXT,
            private_key TEXT,
            public_key TEXT,
            ip_address TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_enabled INTEGER DEFAULT 1
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
        conn.execute('''CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            auto_connect INTEGER DEFAULT 0,
            kill_switch INTEGER DEFAULT 1,
            ad_block INTEGER DEFAULT 0
        )''')
        for aid in ADMIN_IDS:
            conn.execute("INSERT OR IGNORE INTO users (telegram_id, username, first_name, is_admin, subscription_end) VALUES (?, 'admin', 'Admin', 1, datetime('now', '+365 days'))", (aid,))
        conn.execute("INSERT OR IGNORE INTO user_settings (user_id) SELECT id FROM users WHERE id NOT IN (SELECT user_id FROM user_settings)")

init_db()

# ========== WIREGUARD ==========
def setup_wireguard():
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
    return True

def generate_keys():
    priv = subprocess.check_output(['wg', 'genkey']).decode().strip()
    pub = subprocess.check_output(['wg', 'pubkey'], input=priv.encode()).decode().strip()
    return priv, pub

def get_next_ip():
    with sqlite3.connect('vpn_bot.db') as conn:
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

def generate_config(priv, ip):
    return f"""[Interface]
PrivateKey = {priv}
Address = {ip}/24
DNS = 1.1.1.1
MTU = 1420

[Peer]
PublicKey = {SERVER_PUBLIC_KEY}
Endpoint = {SERVER_PUBLIC_IP}:{WG_PORT}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""

def generate_qr(text):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio

# ========== ВСПОМОГАТЕЛЬНЫЕ ==========
def get_user_db_id(tg_id):
    with sqlite3.connect('vpn_bot.db') as conn:
        r = conn.execute("SELECT id FROM users WHERE telegram_id = ?", (tg_id,)).fetchone()
        return r[0] if r else None

def is_sub_active(tg_id):
    with sqlite3.connect('vpn_bot.db') as conn:
        r = conn.execute("SELECT subscription_end FROM users WHERE telegram_id = ?", (tg_id,)).fetchone()
        if r and r[0]:
            return datetime.fromisoformat(r[0]) > datetime.now()
    return False

def give_daily_bonus(tg_id):
    with sqlite3.connect('vpn_bot.db') as conn:
        row = conn.execute("SELECT last_bonus_date, balance FROM users WHERE telegram_id = ?", (tg_id,)).fetchone()
        if not row:
            return False, 0, 0
        today = datetime.now().date()
        last = datetime.fromisoformat(row[0]).date() if row[0] else None
        if last == today:
            return False, 0, 0
        if last and (today - last).days == 1:
            conn.execute("UPDATE users SET bonus_streak = bonus_streak + 1 WHERE telegram_id = ?", (tg_id,))
        else:
            conn.execute("UPDATE users SET bonus_streak = 1 WHERE telegram_id = ?", (tg_id,))
        streak = conn.execute("SELECT bonus_streak FROM users WHERE telegram_id = ?", (tg_id,)).fetchone()[0]
        bonus = DAILY_BONUS
        if streak % 7 == 0:
            bonus *= 2
        conn.execute("UPDATE users SET balance = balance + ?, last_bonus_date = datetime('now') WHERE telegram_id = ?", (bonus, tg_id))
        return True, bonus, streak

def generate_backup_codes(tg_id, count=8):
    codes = []
    uid = get_user_db_id(tg_id)
    if not uid:
        return codes
    with sqlite3.connect('vpn_bot.db') as conn:
        for _ in range(count):
            code = secrets.token_hex(4).upper()
            h = hashlib.sha256(code.encode()).hexdigest()
            conn.execute("INSERT INTO backup_codes (user_id, code_hash) VALUES (?, ?)", (uid, h))
            codes.append(code)
    return codes

def get_backup_left(tg_id):
    uid = get_user_db_id(tg_id)
    if not uid:
        return 0
    with sqlite3.connect('vpn_bot.db') as conn:
        return conn.execute("SELECT COUNT(*) FROM backup_codes WHERE user_id = ? AND used = 0", (uid,)).fetchone()[0]

# ========== КЛАВИАТУРЫ ==========
def get_main_keyboard(is_admin=False):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("📱 Мои устройства", callback_data="my_devices"),
           InlineKeyboardButton("➕ Добавить", callback_data="add_device"))
    kb.add(InlineKeyboardButton("📊 Статистика", callback_data="stats"),
           InlineKeyboardButton("🎁 Рефералка", callback_data="referral"))
    kb.add(InlineKeyboardButton("⚡ Speed Test", callback_data="speed_test"),
           InlineKeyboardButton("🔐 Резервные коды", callback_data="backup_keys"))
    kb.add(InlineKeyboardButton("⚙️ Настройки", callback_data="settings"),
           InlineKeyboardButton("ℹ️ О боте", callback_data="about"))
    if is_admin:
        kb.add(InlineKeyboardButton("👑 Админ", callback_data="admin_panel"))
    return kb

# ========== ОБРАБОТЧИКИ ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def cmd_start(msg: types.Message):
    uid = msg.from_user.id
    name = msg.from_user.first_name
    uname = msg.from_user.username
    args = msg.get_args()
    
    with sqlite3.connect('vpn_bot.db') as conn:
        user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (uid,)).fetchone()
        if not user:
            referred = None
            if args and args.startswith('ref_'):
                try:
                    rid = int(args.replace('ref_', ''))
                    rrow = conn.execute("SELECT id FROM users WHERE telegram_id = ?", (rid,)).fetchone()
                    if rrow:
                        referred = rrow[0]
                except: pass
            conn.execute('''INSERT INTO users (telegram_id, username, first_name, subscription_end, referred_by)
                            VALUES (?, ?, ?, datetime('now', '+? days'), ?)''',
                         (uid, uname, name, DEFAULT_SUBSCRIPTION_DAYS, referred))
            if referred:
                conn.execute("UPDATE users SET referral_balance = referral_balance + ? WHERE id = ?", (REFERRAL_BONUS, referred))
            conn.execute("INSERT INTO user_settings (user_id) SELECT id FROM users WHERE telegram_id = ?", (uid,))
            await msg.reply(f"🎉 Добро пожаловать, {name}!\n✅ {DEFAULT_SUBSCRIPTION_DAYS} дней подписки\n💰 Бонус +{DAILY_BONUS}₽/день", reply_markup=get_main_keyboard())
        else:
            got, amt, streak = give_daily_bonus(uid)
            bonus = f"\n🎁 +{amt}₽ (стрик {streak})" if got else ""
            end = datetime.fromisoformat(user[4]) if user[4] else datetime.now()
            left = max(0, (end - datetime.now()).days)
            await msg.reply(f"👋 С возвращением, {name}!{bonus}\n📅 Подписка до: {end.strftime('%d.%m.%Y')}\n⏰ Осталось {left} дн\n💰 Баланс: {user[5]}₽", reply_markup=get_main_keyboard())

@dp.callback_query_handler(lambda c: c.data == "stats")
async def stats_cb(cb):
    uid = cb.from_user.id
    with sqlite3.connect('vpn_bot.db') as conn:
        u = conn.execute('''SELECT u.*, COUNT(d.id) as devs FROM users u LEFT JOIN devices d ON d.user_id=u.id WHERE u.telegram_id=? GROUP BY u.id''', (uid,)).fetchone()
    if u:
        end = datetime.fromisoformat(u[4]) if u[4] else datetime.now()
        left = max(0, (end - datetime.now()).days)
        await cb.message.edit_text(f"📊 Статистика\n👤 {u[3]}\n🔐 Подписка до {end.strftime('%d.%m.%Y')}\n📱 Устройств: {u[-1]}/{MAX_DEVICES_PER_USER}\n💰 Баланс: {u[5]}₽")

@dp.callback_query_handler(lambda c: c.data == "add_device")
async def add_dev_cb(cb):
    uid = cb.from_user.id
    if not is_sub_active(uid):
        await cb.answer("❌ Подписка истекла", show_alert=True)
        return
    cnt = 0
    with sqlite3.connect('vpn_bot.db') as conn:
        cnt = conn.execute("SELECT COUNT(*) FROM devices d JOIN users u ON u.id=d.user_id WHERE u.telegram_id=?", (uid,)).fetchone()[0]
    if cnt >= MAX_DEVICES_PER_USER:
        await cb.answer(f"❌ Лимит {MAX_DEVICES_PER_USER} устройств", show_alert=True)
        return
    kb = InlineKeyboardMarkup(row_width=2)
    for t in ["windows","macos","android","ios","linux"]:
        kb.add(InlineKeyboardButton(f"💻 {t.capitalize()}", callback_data=f"device_{t}"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
    await cb.message.edit_text("📱 Выберите устройство:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("device_"))
async def create_dev_cb(cb):
    uid = cb.from_user.id
    dtype = cb.data.split('_')[1]
    if not is_sub_active(uid):
        await cb.answer("❌ Подписка истекла", show_alert=True)
        return
    priv, pub = generate_keys()
    ip = get_next_ip()
    name = f"{dtype}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    uidb = get_user_db_id(uid)
    with sqlite3.connect('vpn_bot.db') as conn:
        conn.execute("INSERT INTO devices (user_id, device_name, device_type, private_key, public_key, ip_address) VALUES (?,?,?,?,?,?)", (uidb, name, dtype, priv, pub, ip))
    add_peer(pub, ip)
    cfg = generate_config(priv, ip)
    qr = generate_qr(cfg)
    await cb.message.delete()
    await bot.send_photo(uid, types.InputFile(qr), caption=f"✅ {dtype} создано! IP {ip}")
    cf = BytesIO(cfg.encode())
    cf.name = f"ultrovpn_{dtype}.conf"
    await bot.send_document(uid, types.InputFile(cf))

@dp.callback_query_handler(lambda c: c.data == "my_devices")
async def my_devices_cb(cb):
    uid = cb.from_user.id
    with sqlite3.connect('vpn_bot.db') as conn:
        devs = conn.execute("SELECT d.* FROM devices d JOIN users u ON u.id=d.user_id WHERE u.telegram_id=? AND d.is_enabled=1", (uid,)).fetchall()
    if not devs:
        await cb.message.edit_text("📭 Нет устройств", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")))
        return
    txt = "📱 Ваши устройства:\n\n"
    kb = InlineKeyboardMarkup()
    for d in devs:
        txt += f"🔹 {d[2]} - {d[3]}\n   IP: {d[6]}\n\n"
        kb.add(InlineKeyboardButton(f"🗑 Удалить {d[2]}", callback_data=f"delete_{d[0]}"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
    await cb.message.edit_text(txt, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("delete_"))
async def del_dev_cb(cb):
    did = int(cb.data.split('_')[1])
    with sqlite3.connect('vpn_bot.db') as conn:
        pub = conn.execute("SELECT public_key FROM devices WHERE id=?", (did,)).fetchone()
        if pub:
            remove_peer(pub[0])
            conn.execute("DELETE FROM devices WHERE id=?", (did,))
    await cb.answer("✅ Удалено")
    await my_devices_cb(cb)

@dp.callback_query_handler(lambda c: c.data == "backup_keys")
async def backup_cb(cb):
    uid = cb.from_user.id
    codes = generate_backup_codes(uid)
    left = get_backup_left(uid)
    await cb.message.edit_text("🔐 Резервные коды:\n" + "\n".join([f"`{c}`" for c in codes]) + f"\n\n⚠️ Осталось {left}/8", parse_mode='Markdown')

@dp.callback_query_handler(lambda c: c.data == "referral")
async def referral_cb(cb):
    uid = cb.from_user.id
    botname = (await bot.get_me()).username
    link = f"https://t.me/{botname}?start=ref_{uid}"
    with sqlite3.connect('vpn_bot.db') as conn:
        cnt = conn.execute("SELECT COUNT(*) FROM users WHERE referred_by=(SELECT id FROM users WHERE telegram_id=?)", (uid,)).fetchone()[0]
        bal = conn.execute("SELECT referral_balance FROM users WHERE telegram_id=?", (uid,)).fetchone()[0]
    await cb.message.edit_text(f"🎁 Рефералка\n💰 За друга: +{REFERRAL_BONUS}₽\n📊 Приглашено: {cnt}\n💰 Заработано: {bal}₽\n🔗 `{link}`", parse_mode='Markdown')

@dp.callback_query_handler(lambda c: c.data == "speed_test")
async def speed_cb(cb):
    await cb.message.edit_text("🚀 Speed test скоро будет...")

@dp.callback_query_handler(lambda c: c.data == "settings")
async def settings_cb(cb):
    txt = "⚙️ Настройки\n🔄 Auto-connect\n🛡️ Kill Switch\n🛡️ AdBlock"
    await cb.message.edit_text(txt)

@dp.callback_query_handler(lambda c: c.data == "about")
async def about_cb(cb):
    await cb.message.edit_text("🔒 UltroVPN v1.0\nЗащита в интернете")

@dp.callback_query_handler(lambda c: c.data == "back_to_menu")
async def back_menu(cb):
    await cb.message.edit_text("🏠 Главное меню", reply_markup=get_main_keyboard())

@dp.callback_query_handler(lambda c: c.data == "admin_panel")
async def admin_cb(cb):
    await cb.message.edit_text("👑 Админ панель\n/invite - создать инвайт")

@dp.message_handler(commands=['invite'])
async def invite_cmd(msg):
    code = secrets.token_hex(8).upper()
    with sqlite3.connect('vpn_bot.db') as conn:
        uidb = get_user_db_id(msg.from_user.id)
        conn.execute("INSERT INTO invites (code, created_by) VALUES (?, ?)", (code, uidb))
    await msg.reply(f"🎫 Инвайт: `{code}`", parse_mode='Markdown')

# ========== ЗАПУСК ==========
async def on_startup(dp):
    setup_wireguard()
    print("🚀 ULTROVPN БОТ ЗАПУЩЕН")
    print(f"📱 Бот: @{(await bot.get_me()).username}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
