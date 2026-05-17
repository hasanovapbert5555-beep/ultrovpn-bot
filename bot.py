import asyncio
import logging
import json
from datetime import datetime
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from config import BOT_TOKEN, TARIFFS, MAX_DEVICES
from db import init_db, register_user, get_user, update_subscription, get_devices, revoke_device
from vpn import generate_vpn_config, revoke_device as revoke_vpn_device
from payments import create_payment, handle_payment_callback
from referral import process_referral_link, get_referral_stats
from keyboards import get_main_keyboard, get_tariffs_keyboard, get_devices_keyboard, get_payment_confirmation_keyboard, get_back_keyboard
from admin import router as admin_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Состояния для FSM
class GiftState(StatesGroup):
    waiting_for_username = State()
    waiting_for_tariff = State()

class DeviceState(StatesGroup):
    waiting_for_device_name = State()

# Регистрируем админский роутер
dp.include_router(admin_router)

@dp.message(CommandStart())
async def cmd_start(message: Message):
    # Обрабатываем реферальную ссылку
    args = message.text.split()
    if len(args) > 1:
        ref_code = args[1]
        await process_referral_link(ref_code, message.from_user.id)
    
    # Регистрируем пользователя
    user = await register_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )
    
    welcome_text = (
        f"🎉 Добро пожаловать, {message.from_user.first_name}!\n\n"
        f"🤖 Я бот для выдачи VPN-доступа по протоколу VLESS.\n\n"
        f"📱 Используйте кнопки меню для управления подпиской."
    )
    
    await message.answer(welcome_text, reply_markup=get_main_keyboard())

@dp.message(F.text == "📱 Моя подписка")
async def show_subscription(message: Message):
    user = await get_user(message.from_user.id)
    devices = await get_devices(message.from_user.id)
    
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        return
    
    sub_end = user['subscription_end']
    now = int(datetime.now().timestamp())
    
    if sub_end > now:
        days_left = (sub_end - now) // 86400
        sub_status = f"✅ Активна\n📅 Осталось дней: {days_left}\n📅 Дата окончания: {datetime.fromtimestamp(sub_end).strftime('%d.%m.%Y')}"
    else:
        sub_status = "❌ Неактивна"
    
    text = (
        f"📱 <b>Ваш профиль</b>\n\n"
        f"🆔 Telegram ID: {user['telegram_id']}\n"
        f"👤 Имя: {user['first_name'] or 'Не указано'}\n"
        f"💳 Подписка: {sub_status}\n"
        f"📱 Активных устройств: {len(devices)}/{MAX_DEVICES}\n"
        f"🎁 Бонусных дней получено: {user['bonus_days_earned']}\n\n"
        f"💰 <b>Пополнить подписку:</b>"
    )
    
    await message.answer(text, parse_mode="HTML", reply_markup=get_tariffs_keyboard())

@dp.message(F.text == "👥 Реферальная система")
async def show_referral(message: Message):
    stats = await get_referral_stats(message.from_user.id)
    
    text = (
        f"👥 <b>Реферальная система</b>\n\n"
        f"🔗 Ваша реферальная ссылка:\n<code>{stats['referral_link']}</code>\n\n"
        f"📊 Статистика:\n"
        f"• Приглашено друзей: {stats['total_referrals']}\n"
        f"• Активировано подписок: {stats['active_referrals']}\n"
        f"• Бонусных дней получено: {stats['bonus_days_earned']}\n\n"
        f"🎁 <b>Как это работает?</b>\n"
        f"Пригласите друга по вашей ссылке. Когда он купит ЛЮБОЙ тариф, вы получите +7 дней подписки БЕСПЛАТНО!\n\n"
        f"💡 <i>Чем больше друзей - тем дольше ваша подписка!</i>"
    )
    
    await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "🎁 Подарить подписку")
async def gift_subscription(message: Message, state: FSMContext):
    await message.answer("🎁 Введите username или Telegram ID друга, которому хотите подарить подписку:\n\n"
                        "Примеры:\n"
                        "• @username\n"
                        "• 123456789\n\n"
                        "❌ Для отмены введите /cancel")
    await state.set_state(GiftState.waiting_for_username)

@dp.message(GiftState.waiting_for_username)
async def process_gift_username(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Операция отменена", reply_markup=get_main_keyboard())
        return
    
    # Сохраняем username/ID
    await state.update_data(gift_to=message.text.strip())
    await message.answer("💰 Выберите тариф для подарка:", reply_markup=get_tariffs_keyboard())
    await state.set_state(GiftState.waiting_for_tariff)

@dp.message(F.text == "🌐 Подключить VPN")
async def connect_vpn(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    devices = await get_devices(message.from_user.id)
    
    if not user or user['subscription_end'] < int(datetime.now().timestamp()):
        await message.answer("❌ У вас нет активной подписки!\n\n"
                            "💳 Пополните подписку через кнопку «Моя подписка»")
        return
    
    if len(devices) >= MAX_DEVICES:
        text = f"⚠️ У вас уже есть {MAX_DEVICES} активных устройств!\n\n"
        text += "Выберите устройство для отвязки:\n"
        
        for device in devices:
            text += f"• {device['device_name']}\n"
        
        await message.answer(text, reply_markup=get_devices_keyboard(devices))
        return
    
    await message.answer("📱 Введите название устройства (например: iPhone, Laptop, PC):\n\n"
                        "❌ Для отмены введите /cancel")
    await state.set_state(DeviceState.waiting_for_device_name)

@dp.message(DeviceState.waiting_for_device_name)
async def process_device_name(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Операция отменена", reply_markup=get_main_keyboard())
        return
    
    device_name = message.text.strip()
    
    # Генерируем конфиг
    config = await generate_vpn_config(message.from_user.id, device_name)
    
    if not config:
        await message.answer("❌ Не удалось создать VPN конфиг. Проверьте подписку или попробуйте позже.")
        await state.clear()
        return
    
    # Отправляем конфиг
    text = (
        f"✅ <b>VPN конфиг для {device_name} создан!</b>\n\n"
        f"🔗 <b>VLESS ссылка для импорта:</b>\n"
        f"<code>{config['vless_link']}</code>\n\n"
        f"📱 <b>Инструкция для HAppr:</b>\n"
        f"1. Скачайте HAppr (https://happr.app)\n"
        f"2. Нажмите «+» → «Импорт из буфера обмена»\n"
        f"3. Скопируйте ссылку выше и вставьте в HAppr\n"
        f"4. Подключитесь к VPN\n\n"
        f"💡 <i>Вы можете подключить до {MAX_DEVICES} устройств. Для добавления нового повторите действие.</i>"
    )
    
    await message.answer(text, parse_mode="HTML")
    await state.clear()

@dp.message(F.text == "ℹ️ Информация")
async def show_info(message: Message):
    text = (
        f"ℹ️ <b>Информация о VPN сервисе</b>\n\n"
        f"🔒 <b>Протокол:</b> VLESS (Xray-core)\n"
        f"🌐 <b>Поддерживаемые приложения:</b>\n"
        f"• HAppr (рекомендуется)\n"
        f"• v2rayNG\n"
        f"• Nekobox\n"
        f"• Shadowrocket (iOS)\n\n"
        f"🛡️ <b>Конфиденциальность:</b>\n"
        f"• Логи не хранятся\n"
        f"• Ваши IP-адреса не записываются\n"
        f"• Трафик не мониторится\n\n"
        f"⚡ <b>Особенности:</b>\n"
        f"• Высокая скорость (до 1 Гбит/с)\n"
        f"• Обход блокировок\n"
        f"• Поддержка до 5 устройств\n"
        f"• Автоматическое продление\n\n"
        f"📜 <b>Пользовательское соглашение:</b>\n"
        f"Запрещено использование сервиса для:\n"
        f"• Противозаконной деятельности\n"
        f"• Рассылки спама\n"
        f"• DDoS атак\n"
        f"• Распространения вредоносного ПО\n\n"
        f"При нарушении условий доступ блокируется без возврата средств.\n\n"
        f"💬 <b>Поддержка:</b> @your_support_bot"
    )
    
    await message.answer(text, parse_mode="HTML")

@dp.callback_query(F.data.startswith("tariff_"))
async def process_tariff_selection(callback: CallbackQuery):
    tariff_key = callback.data.replace("tariff_", "")
    tariff = TARIFFS.get(tariff_key)
    
    if not tariff:
        await callback.answer("❌ Тариф не найден")
        return
    
    # Создаем платеж
    payment = await create_payment(callback.from_user.id, tariff_key)
    
    if not payment:
        await callback.message.edit_text("❌ Ошибка создания платежа. Попробуйте позже.")
        return
    
    text = (
        f"💰 <b>Оплата подписки {tariff_key.upper()}</b>\n\n"
        f"📅 Дней: {tariff['days']}\n"
        f"💵 Сумма: {tariff['price_usdt']} USDT\n\n"
        f"🔗 Нажмите кнопку «Оплатить» для перехода к платежу\n\n"
        f"✅ После оплаты нажмите «Проверить оплату»\n"
        f"⏱ Счет действителен 60 минут"
    )
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_payment_confirmation_keyboard(payment['pay_url'])
    )
    
    # Сохраняем invoice_id в callback_data
    await callback.answer()

@dp.callback_query(F.data == "check_payment")
async def check_payment(callback: CallbackQuery):
    # Здесь должна быть проверка статуса платежа через API
    # Для демонстрации используем заглушку
    await callback.answer("⏳ Проверка платежа...", show_alert=True)
    
    # В реальном проекте: проверка через API CryptoBot
    # и активация подписки
    
    await callback.message.edit_text(
        "✅ Платеж подтвержден!\n\n"
        "🎉 Ваша подписка активирована!\n"
        "🌐 Используйте кнопку «Подключить VPN» для настройки.",
        reply_markup=get_back_keyboard()
    )

@dp.callback_query(F.data == "cancel_payment")
async def cancel_payment(callback: CallbackQuery):
    await callback.message.edit_text("❌ Платеж отменен", reply_markup=get_back_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Главное меню", reply_markup=get_main_keyboard())
    await callback.answer()

@dp.callback_query(F.data.startswith("revoke_device_"))
async def revoke_device_callback(callback: CallbackQuery):
    device_id = int(callback.data.replace("revoke_device_", ""))
    
    success = await revoke_vpn_device(callback.from_user.id, device_id)
    
    if success:
        await callback.answer("✅ Устройство отвязано", show_alert=True)
        await callback.message.delete()
        await callback.message.answer("Главное меню", reply_markup=get_main_keyboard())
    else:
        await callback.answer("❌ Ошибка при отвязке устройства", show_alert=True)

async def main():
    # Инициализируем БД
    await init_db()
    logger.info("Database initialized")
    
    # Запускаем бота
    logger.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
