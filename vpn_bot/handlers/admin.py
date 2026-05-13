from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy import select, func
from database import get_db
from models import User, Subscription, Payment
from config import ADMIN_IDS

async def check_admin(func):
    async def wrapper(update, context):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("⛔ Доступ запрещён.")
            return
        return await func(update, context)
    return wrapper

@check_admin
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton("💰 Платежи", callback_data="admin_payments")],
        [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
    ]
    await update.message.reply_text("👑 Админ-панель", reply_markup=InlineKeyboardMarkup(keyboard))

@check_admin
async def users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async for session in get_db():
        users = await session.execute(select(User))
        users = users.scalars().all()
        text = "👥 Список пользователей:\n\n"
        for u in users[-20:]:
            sub = await session.execute(select(Subscription).where(Subscription.user_id == u.id, Subscription.is_active == True))
            sub = sub.scalar_one_or_none()
            status = f"до {sub.end_date.strftime('%d.%m')}" if sub else "❌ не активен"
            text += f"🆔 {u.telegram_id} | @{u.username or 'нет'} | {status}\n"
        await update.message.reply_text(text)

@check_admin
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /broadcast текст для рассылки")
        return
    text = " ".join(context.args)
    async for session in get_db():
        users = await session.execute(select(User))
        users = users.scalars().all()
        sent = 0
        for u in users:
            try:
                await context.bot.send_message(u.telegram_id, f"📢 Анонс:\n\n{text}")
                sent += 1
            except:
                pass
        await update.message.reply_text(f"✅ Рассылка завершена. Отправлено {sent} пользователям.")