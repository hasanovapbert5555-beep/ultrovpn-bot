import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from config import BOT_TOKEN, TARIFFS, MAX_DEVICES
from db import init_db, register_user, get_user, get_devices
from vpn import generate_vpn_config, revoke_device, xray_manager
from payments import create_payment, payment_polling_loop
from referral import process_referral_link, get_referral_stats
from admin import router as admin_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class DeviceState(StatesGroup):
    waiting_for_device_name = State()

def get_main_keyboard():
    buttons = [
        [KeyboardButton(text="📱 Моя подписка")],
        [KeyboardButton(text="👥 Реферальная система")],
        [KeyboardButton(text="🎁 Подарить подписку")],
        [KeyboardButton(text="🌐 Подключить VPN")],
        [KeyboardButton(text="ℹ️ Информация")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_tariffs_keyboard():
    buttons = []
    for key, tariff in TARIFFS.items():
        if 'price_rub' in tariff:
            price = tariff['price_rub']
        else:
            price = tariff.get('price_usdt', 0)
        btn_text = f"{key.upper()} - {price}₽"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"tariff_{key}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(CommandStart())
async def cmd_start(message: Message):
    args = message.text.split()
    if len(args) > 1:
        await process_referral_link(args[1], message.from_user.id)
    
    await register_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )
    
    await message.answer(
        f"🎉 Добро пожаловать, {message.from_user.first_name}!\n\n"
        f"🤖 Я бот для выдачи VPN-доступа.\n"
        f"📱 Используйте кнопки меню.",
        reply_markup=get_main_keyboard()
    )

@dp.message(F.text == "📱 Моя подписка")
async def show_subscription(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        return
    
    sub_end = user.get('subscription_end', 0)
    now = int(datetime.now().timestamp())
    
    if sub_end > now:
        days_left = (sub_end - now) // 86400
        sub_status = f"✅ Активна\n📅 Осталось дней: {days_left}"
    else:
        sub_status = "❌ Неактивна"
    
    devices = await get_devices(message.from_user.id)
    text = (
        f"📱 <b>Ваш профиль</b>\n\n"
        f"🆔 ID: {user['telegram_id']}\n"
        f"💳 Подписка: {sub_status}\n"
        f"📱 Устройств: {len(devices)}/{MAX_DEVICES}\n\n"
        f"💰 <b>Пополнить подписку:</b>"
    )
    
    await message.answer(text, parse_mode="HTML", reply_markup=get_tariffs_keyboard())

@dp.message(F.text == "👥 Реферальная система")
async def show_referral(message: Message):
    stats = await get_referral_stats(message.from_user.id)
    text = (
        f"👥 <b>Реферальная система</b>\n\n"
        f"🔗 Ваша реферальная ссылка:\n<code>{stats['referral_link']}</code>\n\n"
        f"📊 Приглашено друзей: {stats['total_referrals']}\n"
        f"🎁 Бонусных дней получено: {stats['bonus_days_earned']}\n\n"
        f"💡 За каждого друга, купившего подписку, вы получаете +7 дней!"
    )
    await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "🎁 Подарить подписку")
async def gift_subscription(message: Message):
    await message.answer(
        "🎁 <b>Подарок подписки</b>\n\n"
        "Эта функция в разработке.\n"
        "Скоро вы сможете дарить подписку друзьям!\n\n"
        "А пока приглашайте друзей через реферальную систему.",
        parse_mode="HTML"
    )

@dp.message(F.text == "🌐 Подключить VPN")
async def connect_vpn(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        return
    
    if user.get('subscription_end', 0) < int(datetime.now().timestamp()):
        await message.answer(
            "❌ У вас нет активной подписки!\n\n"
            "💳 Пополните подписку через кнопку «Моя подписка»"
        )
        return
    
    devices = await get_devices(message.from_user.id)
    if len(devices) >= MAX_DEVICES:
        device_list = "\n".join([f"• {d['device_name']}" for d in devices])
        await message.answer(
            f"⚠️ У вас уже {MAX_DEVICES} активных устройств:\n{device_list}\n\n"
            f"Чтобы добавить новое, сначала отвяжите одно из существующих."
        )
        return
    
    await message.answer(
        "📱 Введите название устройства (например: iPhone, Laptop, PC):\n\n"
        "❌ Для отмены отправьте /cancel"
    )
    await state.set_state(DeviceState.waiting_for_device_name)

@dp.message(DeviceState.waiting_for_device_name)
async def process_device_name(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Операция отменена", reply_markup=get_main_keyboard())
        return
    
    device_name = message.text.strip()
    if not device_name:
        await message.answer("❌ Название устройства не может быть пустым")
        return
    
    config = await generate_vpn_config(message.from_user.id, device_name)
    
    if config:
        text = (
            f"✅ <b>VPN конфиг для {config['device_name']} создан!</b>\n\n"
            f"🔗 <b>VLESS ссылка для импорта:</b>\n"
            f"<code>{config['vless_link']}</code>\n\n"
            f"📱 <b>Инструкция:</b>\n"
            f"1. Скопируйте ссылку выше\n"
            f"2. Установите HAppr или v2rayNG\n"
            f"3. Импортируйте конфиг из буфера обмена\n"
            f"4. Подключитесь к VPN\n\n"
            f"💡 Вы можете подключить до {MAX_DEVICES} устройств"
        )
        await message.answer(text, parse_mode="HTML")
    else:
        await message.answer(
            "❌ Не удалось создать VPN конфиг.\n\n"
            "Возможные причины:\n"
            "• Нет активной подписки\n"
            "• Проблемы с Xray сервером\n"
            "• Достигнут лимит устройств"
        )
    
    await state.clear()

@dp.message(F.text == "ℹ️ Информация")
async def show_info(message: Message):
    text = (
        f"ℹ️ <b>Информация о VPN сервисе</b>\n\n"
        f"🔒 <b>Протокол:</b> VLESS + REALITY\n"
        f"🌐 <b>Поддерживаемые приложения:</b>\n"
        f"• HAppr (рекомендуется)\n"
        f"• v2rayNG\n"
        f"• Nekobox\n\n"
        f"🛡️ <b>Конфиденциальность:</b>\n"
        f"• Логи не хранятся\n"
        f"• Ваши IP-адреса не записываются\n\n"
        f"⚡ <b>Особенности:</b>\n"
        f"• Высокая скорость\n"
        f"• Обход блокировок\n"
        f"• Поддержка до {MAX_DEVICES} устройств\n\n"
        f"📜 <b>Правила использования:</b>\n"
        f"Запрещено использование сервиса для противоправной деятельности.\n\n"
        f"💬 <b>Поддержка:</b> @your_support_bot"
    )
    await message.answer(text, parse_mode="HTML")

@dp.callback_query(F.data.startswith("tariff_"))
async def process_tariff(callback: CallbackQuery):
    tariff_key = callback.data.replace("tariff_", "")
    
    if tariff_key not in TARIFFS:
        await callback.answer("❌ Тариф не найден")
        return
    
    payment = await create_payment(callback.from_user.id, tariff_key)
    
    if payment:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=payment['pay_url'])],
            [InlineKeyboardButton(text="✅ Проверить оплату", callback_data=f"check_{payment['invoice_id']}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_payment")]
        ])
        
        await callback.message.edit_text(
            f"💰 <b>Оплата подписки {tariff_key.upper()}</b>\n\n"
            f"💵 Сумма: {payment['amount_usdt']} USDT\n\n"
            f"🔗 Нажмите «Оплатить» для перехода к платежу\n"
            f"✅ После оплаты нажмите «Проверить оплату»",
            parse_mode="HTML",
            reply_markup=kb
        )
    else:
        await callback.message.edit_text("❌ Ошибка создания платежа. Попробуйте позже.")
    
    await callback.answer()

@dp.callback_query(F.data == "cancel_payment")
async def cancel_payment(callback: CallbackQuery):
    await callback.message.edit_text("❌ Платеж отменен")
    await callback.answer()

dp.include_router(admin_router)

async def main():
    await init_db()
    logger.info("Database initialized")
    await xray_manager.setup_reality_inbound()
    asyncio.create_task(payment_polling_loop(bot))
    logger.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
