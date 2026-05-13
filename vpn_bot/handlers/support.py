from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_db
from models import Ticket, User
from config import ADMIN_IDS
from datetime import datetime

async def support_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✏️ Напишите ваше сообщение для поддержки:")

async def save_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message.text

    async for session in get_db():
        user = await session.execute(select(User).where(User.telegram_id == user_id))
        user = user.scalar_one_or_none()
        if not user:
            await update.message.reply_text("Ошибка. Напишите /start")
            return

        ticket = Ticket(user_id=user.id, message=message, status="open")
        session.add(ticket)
        await session.commit()

        # Уведомляем админов
        for admin_id in ADMIN_IDS:
            await context.bot.send_message(
                admin_id,
                f"🆕 Новый тикет #{ticket.id}\nОт: @{update.effective_user.username or user_id}\nСообщение: {message[:200]}"
            )
        await update.message.reply_text("✅ Ваше сообщение отправлено. Ожидайте ответа.")