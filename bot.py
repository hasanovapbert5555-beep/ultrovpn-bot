import asyncio
import logging
from pathlib import Path

from config import load_config
from keyboards import make_main_keyboard
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiogram.types import Message
from admin import register_admin_handlers
import admin  # noqa: F401 (для экспорта)
import payments
from db import init_db, get_or_create_user
from vpn import ensure_user_context

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG = load_config()
bot = Bot(token=CONFIG["TELEGRAM_BOT_TOKEN"])
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

async def on_startup():
    await init_db()
    logger.info("Bot started and DB ready")

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    user = await get_or_create_user(user_id)
    ref = message.text.split("start=")[-1] if "start=" in message.text else None
    if ref:
        # сохраняем реферала
        await user.set_referrer(ref)

    await message.answer(
        "Добро пожаловать! Здесь можно получить VPN-доступ через VLESS.\n"
        "Используйте меню ниже для управления подпиской и VPN.",
        reply_markup=make_main_keyboard()
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer("Справка по боту доступна позже. Сейчас можно пользоваться основными функциями через главное меню.")

# Модульные обработчики кнопок из клавиатуры
from keyboards import MAIN_COMMANDS

@dp.message(text=MAIN_COMMANDS["subscription"])
async def show_subscription(message: Message):
    user = await get_or_create_user(message.from_user.id)
    profile = await user.get_profile()
    await message.answer(profile)

@dp.message(text=MAIN_COMMANDS["referral"])
async def show_referral(message: Message):
    from referral import get_referral_info
    info = await get_referral_info(message.from_user.id)
    await message.answer(info)

@dp.message(text=MAIN_COMMANDS["gift"])
async def gift_subscription(message: Message):
    await message.answer("Выберите тариф для подарка другу:", reply_markup=None)
    # Здесь можно внедрить Inline меню с тарифами

@dp.message(text=MAIN_COMMANDS["connect_vpn"])
async def connect_vpn(message: Message):
    user = await get_or_create_user(message.from_user.id)
    if not await user.has_active_subscription():
        await message.answer("У вас нет активной подписки.")
        return
    # покажем инструкции и vless ссылку
    conf = await ensure_user_context(user)
    if not conf:
        await message.answer("Не удалось сгенерировать конфиг VPN.")
        return
    await message.answer(conf["link"])
    await message.answer(conf["instructions"], disable_web_page_preview=True)

@dp.message(text=MAIN_COMMANDS["info"])
async def info(message: Message):
    await message.answer("VLESS - это протокол... Подробнее в инструкции.")

# Админские команды
register_admin_handlers(dp)

async def main():
    await on_startup()
    # запуск поллинга
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
