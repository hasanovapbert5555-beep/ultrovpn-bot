from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from datetime import datetime
import asyncio
from db import get_stats, get_all_users, update_subscription, get_user
from config import ADMIN_ID

router = Router()

# Фильтр для админа
async def is_admin(telegram_id: int) -> bool:
    return telegram_id == ADMIN_ID

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к этой команде")
        return
    
    stats = await get_stats()
    
    text = f"📊 <b>Статистика бота</b>\n\n"
    text += f"👥 Всего пользователей: {stats['total_users']}\n"
    text += f"✅ Активных подписок: {stats['active_subscriptions']}\n"
    text += f"💰 Платежей за месяц: {stats['monthly_payments_usdt']} USDT\n"
    
    await message.answer(text, parse_mode="HTML")

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к этой команде")
        return
    
    # Получаем текст для рассылки
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        await message.answer("❌ Укажите текст для рассылки после команды /broadcast")
        return
    
    # Получаем всех пользователей
    users = await get_all_users()
    
    sent = 0
    failed = 0
    
    status_msg = await message.answer(f"🔄 Начинаю рассылку {len(users)} пользователям...")
    
    for user_id in users:
        try:
            await message.bot.send_message(user_id, text, parse_mode="HTML")
            sent += 1
            await asyncio.sleep(0.05)  # Защита от флуда
        except Exception:
            failed += 1
        
        # Обновляем статус каждые 10 пользователей
        if (sent + failed) % 10 == 0:
            await status_msg.edit_text(f"🔄 Рассылка: {sent} успешно, {failed} ошибок из {len(users)}")
    
    await status_msg.edit_text(f"✅ Рассылка завершена!\n✅ Успешно: {sent}\n❌ Ошибок: {failed}")

@router.message(Command("extend"))
async def cmd_extend(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к этой команде")
        return
    
    args = message.text.split()
    if len(args) != 3:
        await message.answer("❌ Использование: /extend <telegram_id> <дни>")
        return
    
    try:
        user_id = int(args[1])
        days = int(args[2])
        
        user = await get_user(user_id)
        if not user:
            await message.answer(f"❌ Пользователь {user_id} не найден")
            return
        
        new_end = await update_subscription(user_id, days)
        new_end_date = datetime.fromtimestamp(new_end).strftime("%d.%m.%Y")
        
        await message.answer(f"✅ Подписка пользователя {user_id} продлена на {days} дней\n"
                            f"📅 Новая дата окончания: {new_end_date}")
        
        # Уведомляем пользователя
        try:
            await message.bot.send_message(user_id, f"🎉 Ваша подписка продлена на {days} дней!\n"
                                                   f"📅 Новая дата окончания: {new_end_date}")
        except:
            pass
            
    except ValueError:
        await message.answer("❌ Неверный формат ID или количества дней")

@router.message(Command("revoke"))
async def cmd_revoke(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к этой команде")
        return
    
    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ Использование: /revoke <telegram_id>")
        return
    
    try:
        user_id = int(args[1])
        
        user = await get_user(user_id)
        if not user:
            await message.answer(f"❌ Пользователь {user_id} не найден")
            return
        
        # Устанавливаем подписку в прошлое
        past_time = int(datetime.now().timestamp()) - 86400
        from db import update_subscription as set_subscription
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute('UPDATE users SET subscription_end = ? WHERE telegram_id = ?', (past_time, user_id))
            await db.commit()
        
        await message.answer(f"✅ Подписка пользователя {user_id} отозвана")
        
        # Уведомляем пользователя
        try:
            await message.bot.send_message(user_id, "⚠️ Ваша подписка была отозвана администратором")
        except:
            pass
            
    except ValueError:
        await message.answer("❌ Неверный формат ID")
