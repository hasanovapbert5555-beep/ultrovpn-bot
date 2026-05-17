 aiogram.filters import Text
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def make_main_keyboard():
    kb = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=False
    )
    kb.add(KeyboardButton("📱 Моя подписка"))
    kb.add(KeyboardButton("👥 Реферальная система"))
    kb.add(KeyboardButton("🎁 Подарить подписку"))
    kb.add(KeyboardButton("🌐 Подключить VPN"))
    kb.add(KeyboardButton("ℹ️ Информация"))
    return kb

MAIN_COMMANDS = {
    "subscription": "📱 Моя подписка",
    "referral": "👥 Реферальная система",
    "gift": "🎁 Подарить подписку",
    "connect_vpn": "🌐 Подключить VPN",
    "info": "ℹ️ Информация",
}
