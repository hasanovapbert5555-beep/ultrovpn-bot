from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config import TARIFFS

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура"""
    buttons = [
        [KeyboardButton(text="📱 Моя подписка")],
        [KeyboardButton(text="👥 Реферальная система")],
        [KeyboardButton(text="🎁 Подарить подписку")],
        [KeyboardButton(text="🌐 Подключить VPN")],
        [KeyboardButton(text="ℹ️ Информация")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_tariffs_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора тарифа"""
    buttons = []
    for key, tariff in TARIFFS.items():
        buttons.append([
            InlineKeyboardButton(
                text=f"{key.upper()} - {tariff['price_rub']}₽ ({tariff['price_usdt']} USDT)",
                callback_data=f"tariff_{key}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_devices_keyboard(devices: list) -> InlineKeyboardMarkup:
    """Клавиатура выбора устройства для отвязки"""
    buttons = []
    for device in devices:
        buttons.append([
            InlineKeyboardButton(
                text=f"❌ {device['device_name']}",
                callback_data=f"revoke_device_{device['id']}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_payment_confirmation_keyboard(pay_url: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения оплаты"""
    buttons = [
        [InlineKeyboardButton(text="💳 Оплатить", url=pay_url)],
        [InlineKeyboardButton(text="✅ Проверить оплату", callback_data="check_payment")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_payment")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_back_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура возврата в меню"""
    buttons = [[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
