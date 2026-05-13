from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import ContextTypes, CallbackQueryHandler, PreCheckoutQueryHandler, MessageHandler, filters
from database import get_db
from models import User, Payment, Subscription, Key, Referral
from config import PRICES, SERVERS, DEFAULT_SERVER_ID, REFERRAL_BONUS_DAYS
from utils.outline_api import create_outline_key

async def buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("1 месяц - 50 ⭐️", callback_data="buy_1_month")],
        [InlineKeyboardButton("3 месяца - 135 ⭐️", callback_data="buy_3_months")],
        [InlineKeyboardButton("6 месяцев - 240 ⭐️", callback_data="buy_6_months")],
        [InlineKeyboardButton("12 месяцев - 450 ⭐️", callback_data="buy_12_months")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")],
    ]
    await query.edit_message_text("🛒 Выберите тариф:", reply_markup=InlineKeyboardMarkup(keyboard))

async def buy_plan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan = query.data.replace("buy_", "")
    user_id = query.from_user.id

    if plan not in PRICES:
        await query.edit_message_text("❌ Ошибка. Выберите тариф из меню.")
        return

    stars = PRICES[plan]["stars"]
    title = f"VPN подписка - {plan.replace('_', ' ')}"
    description = f"Доступ к VPN на {PRICES[plan]['days']} дней"

    await context.bot.send_invoice(
        chat_id=user_id,
        title=title,
        description=description,
        payload=plan,
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice("Подписка", stars)],
        start_parameter="vpn_subscription"
    )

async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    payload = update.message.successful_payment.invoice_payload
    stars = update.message.successful_payment.total_amount

    async for session in get_db():
        user = await session.execute(select(User).where(User.telegram_id == user_id))
        user = user.scalar_one_or_none()
        if not user:
            await update.message.reply_text("❌ Ошибка. Напишите /start")
            return

        # Сохраняем платеж
        payment = Payment(user_id=user.id, amount_stars=stars, plan=payload, status="completed")
        session.add(payment)
        user.total_stars_spent += stars

        # Создаем ключ VPN
        server_id = DEFAULT_SERVER_ID
        server = SERVERS.get(server_id)
        key_id, config = await create_outline_key(server["api_url"], server["cert"])
        if not key_id:
            await update.message.reply_text("❌ Ошибка создания ключа. Обратитесь к администратору.")
            return

        new_key = Key(user_id=user.id, key_string=key_id, config_text=config, server_id=server_id)
        session.add(new_key)
        await session.flush()

        days = PRICES[payload]["days"]
        end_date = datetime.utcnow() + timedelta(days=days)

        sub = Subscription(user_id=user.id, key_id=new_key.id, server_id=server_id, start_date=datetime.utcnow(), end_date=end_date, is_active=True)
        session.add(sub)

        # Реферальный бонус
        if user.referrer_id:
            referrer = await session.get(User, user.referrer_id)
            if referrer:
                ref_bonus = Referral(referrer_id=referrer.id, referred_id=user.id, bonus_days_awarded=REFERRAL_BONUS_DAYS)
                session.add(ref_bonus)

                # Добавляем бонусные дни рефереру
                referrer_sub = await session.execute(select(Subscription).where(Subscription.user_id == referrer.id, Subscription.is_active == True))
referrer_sub = referrer_sub.scalar_one_or_none()
                if referrer_sub:
                    referrer_sub.end_date += timedelta(days=REFERRAL_BONUS_DAYS)

        await session.commit()

        await update.message.reply_text(
            f"✅ Оплата получена! Ваш VPN ключ:\n\n<code>{config}</code>\n\n"
            f"🌍 Сервер: {server['name']}\n"
            f"📅 Действует до: {end_date.strftime('%d.%m.%Y')}\n\n"
            f"Инструкция: скачайте Outline, нажмите +, вставьте ключ.",
            parse_mode="HTML"
        )