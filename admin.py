from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from config import load_config
from db import init_db, get_or_create_user

router = Router()

ADMIN_ID = int(load_config().get("ADMIN_TELEGRAM_ID", 0))

def register_admin_handlers(dp):
    @dp.message(Command("stats"))
    async def stats(message: Message):
        if message.from_user.id != ADMIN_ID:
            return
        # Пример статистики
        await message.answer("Статистика: 0 активных пользователей (заглушка)")

    @dp.message(Command("broadcast"))
    async def broadcast(message: Message):
        if message.from_user.id != ADMIN_ID:
            return
        # Пример рассылки
        await message.answer("Рассылка отправлена (пример)")

    # Пример продления/отмены подписки по ID
    @dp.message("!extend")
    async def admin_extend(message: Message):
        if message.from_user.id != ADMIN_ID:
            return
        await message.answer("Подписка продлена (пример)")
