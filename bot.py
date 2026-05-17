import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, TARIFFS, MAX_DEVICES
from db import init_db, get_user, get_devices
from vpn import generate_vpn_config, revoke_device, xray_manager
from payments import create_payment, payment_polling_loop
from referral import process_referral_link, get_referral_stats
from keyboards import get_main_keyboard, get_tariffs_keyboard, get_devices_keyboard, get_payment_confirmation_keyboard, get_back_keyboard
from admin import router as admin_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Состояния (как в предыдущем коде)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

class GiftState(StatesGroup):
    waiting_for_username = State()
    waiting_for_tariff = State()

class DeviceState(StatesGroup):
    waiting_for_device_name = State()

# Регистрируем админский роутер
dp.include_router(admin_router)

# Все хендлеры такие же как в предыдущей версии bot.py
# (код с @dp.message, @dp.callback_query и т.д. остается без изменений)

# ... (все хендлеры из предыдущего bot.py копируются сюда)

async def main():
    # Инициализируем БД
    await init_db()
    logger.info("Database initialized")
    
    # Настраиваем REALITY inbound в Xray
    logger.info("Setting up REALITY inbound...")
    await xray_manager.setup_reality_inbound()
    
    # Запускаем polling для платежей в фоне
    asyncio.create_task(payment_polling_loop(bot))
    logger.info("Payment polling loop started")
    
    # Запускаем бота
    logger.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
