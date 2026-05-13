import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from sqlalchemy import select, func
from database import get_db
from models import User, Subscription, Key, Referral, Payment
from config import SERVERS, PRICES, DEFAULT_SERVER_ID

with open("locales/ru.json", encoding="utf-8") as f:
    ru = json.load(f)
with open("locales/en.json", encoding="utf-8") as f:
    en = json.load(f)

def get_text(lang, key):
    return ru.get(key, key) if lang == "ru" else en.get(key, key)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref = context.args[0] if context.args else None

    async for session in get_db():
        result = await session.execute(select(User).where(User.telegram_id == user.id))
        db_user = result.scalar_one_or_none()

        if not db_user:
            db_user = User(telegram_id=user.id, username=user.username)
            if ref and ref.startswith("ref"):
                try:
                    ref_id = int(ref[3:])
                    db_user.referrer_id = ref_id
                except:
                    pass
            session.add(db_user)
            await session.commit()

        lang = db_user.lang
        keyboard = [
            [InlineKeyboardButton(get_text(lang, "buy"), callback_data="buy")],
            [InlineKeyboardButton(get_text(lang, "mykey"), callback_data="mykey")],
            [InlineKeyboardButton(get_text(lang, "set_server"), callback_data="set_server")],
            [InlineKeyboardButton(get_text(lang, "referral"), callback_data="referral")],
            [InlineKeyboardButton(get_text(lang, "server_status"), callback_data="server_status")],
            [InlineKeyboardButton(get_text(lang, "mystats"), callback_data="mystats")],
            [InlineKeyboardButton(get_text(lang, "support"), callback_data="support")],
            [InlineKeyboardButton(get_text(lang, "change_lang"), callback_data="change_lang")],
        ]
        await update.message.reply_text(get_text(lang, "welcome"), reply_markup=InlineKeyboardMarkup(keyboard))

async def mykey_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    async for session in get_db():
        user = await session.execute(select(User).where(User.telegram_id == user_id))
        user = user.scalar_one_or_none()
        if not user:
            await query.edit_message_text("❌ Ошибка. Напишите /start")
            return

        sub = await session.execute(select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.is_active == True,
            Subscription.end_date > datetime.utcnow()
        ))
        sub = sub.scalar_one_or_none()

        if not sub:
            await query.edit_message_text("❌ У вас нет активной подписки.\nКупите через /buy")
            return

        key_obj = await session.get(Key, sub.key_id)
        days_left = (sub.end_date - datetime.utcnow()).days

        text = f"🔑 <b>Ваш VPN-ключ</b>\n\n<code>{key_obj.config_text}</code>\n\n📅 Действует до: {sub.end_date.strftime('%d.%m.%Y')}\n⏳ Осталось дней: {days_left}\n🌍 Сервер: {SERVERS.get(sub.server_id, {}).get('name', 'Неизвестно')}"
        keyboard = [[InlineKeyboardButton("🗑 Отозвать ключ", callback_data="revoke_key")]]
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def revoke_key_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    async for session in get_db():
        user = await session.execute(select(User).where(User.telegram_id == user_id))
        user = user.scalar_one_or_none()
        if not user:
            return

        sub = await session.execute(select(Subscription).where(Subscription.user_id == user.id, Subscription.
is_active == True))
        sub = sub.scalar_one_or_none()
        if sub:
            sub.is_active = False
            await session.commit()
            await query.edit_message_text("✅ Ключ отозван. Доступ заблокирован.")
        else:
            await query.edit_message_text("❌ Нет активного ключа.")

async def change_lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    async for session in get_db():
        user = await session.execute(select(User).where(User.telegram_id == user_id))
        user = user.scalar_one_or_none()
        if user:
            user.lang = "en" if user.lang == "ru" else "ru"
            await session.commit()
            await query.edit_message_text(f"Язык изменён на {'English' if user.lang == 'en' else 'Русский'}. Нажмите /start")
        else:
            await query.edit_message_text("Ошибка. Напишите /start")

async def mystats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    async for session in get_db():
        user = await session.execute(select(User).where(User.telegram_id == user_id))
        user = user.scalar_one_or_none()
        if not user:
            await query.edit_message_text("❌ Ошибка. Напишите /start")
            return

        payments = await session.execute(select(func.sum(Payment.amount_stars)).where(Payment.user_id == user.id, Payment.status == "completed"))
        total_spent = payments.scalar() or 0

        text = f"📊 <b>Ваша статистика</b>\n\n"
        text += f"📅 Дата регистрации: {user.reg_date.strftime('%d.%m.%Y')}\n"
        text += f"💰 Потрачено Stars: {total_spent}\n"
        text += f"🔄 Смен сервера: {user.server_changes}\n"

        refs = await session.execute(select(Referral).where(Referral.referrer_id == user.id))
        ref_count = len(refs.scalars().all())
        text += f"👥 Приглашено друзей: {ref_count}"

        await query.edit_message_text(text, parse_mode="HTML")