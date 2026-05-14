# bot.py
import asyncio, logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InputFile
import config, database, lang
from io import BytesIO
import qrcode
from datetime import datetime

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

bot = Bot(token=config.BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

def main_menu_kb(user_id:int):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    kb.add(types.KeyboardButton("🏠 Главное"), types.KeyboardButton("👤 Профиль"), types.KeyboardButton("❓ Помощь"))
    kb.add(types.KeyboardButton("🛒 Моя подписка"), types.KeyboardButton("💳 Пополнить"), types.KeyboardButton("🔗 Реферал"))
    return kb

def tariffs_kb(user_id:int):
    kb = types.InlineKeyboardMarkup()
    for key, v in config.PRICES.items():
        kb.add(types.InlineKeyboardButton(f"{v['name']['ru']} — {v['price_usd']}$", callback_data=f"buy:{key}"))
    return kb

@dp.message(commands=["start"])
async def cmd_start(m: types.Message):
    args = m.get_args()
    ref = args if args else None
    await database.ensure_user(m.from_user.id, m.from_user.username, m.from_user.full_name, ref)
    await m.answer(await lang.get_text(m.from_user.id, "start"), reply_markup=main_menu_kb(m.from_user.id))
    try:
        logo = InputFile(config.LOGO_PATH)
        await bot.send_photo(m.from_user.id, photo=logo)
    except Exception:
        logger.info("Logo send skipped")

@dp.message(commands=["lang"])
async def cmd_lang(m: types.Message):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Русский", callback_data="lang:ru"))
    kb.add(types.InlineKeyboardButton("English", callback_data="lang:en"))
    kb.add(types.InlineKeyboardButton("Uzbek", callback_data="lang:uz"))
    await m.answer("Choose language / Выберите язык:", reply_markup=kb)

@dp.callback_query(lambda c: c.data and c.data.startswith("lang:"))
async def cb_lang(c: types.CallbackQuery):
    code = c.data.split(":",1)[1]
    await database.set_user_language(c.from_user.id, code)
    await c.answer()
    await c.message.edit_text(await lang.get_text(c.from_user.id, "lang_changed"))

@dp.message()
async def all_text(m: types.Message):
    text = m.text.strip().lower()
    uid = m.from_user.id
    if "глав" in text or "🏠" in text:
        await m.answer(await lang.get_text(uid, "menu"), reply_markup=main_menu_kb(uid))
        return
    if "проф" in text or "👤" in text:
        user = await database.get_user(uid)
        bal = user.get("balance",0) if user else 0
        ref_link = f"t.me/{(await bot.get_me()).username}?start={(user['referral_code'] if user else '')}"
        await m.answer(await lang.get_text(uid, "profile_title") + f"\n" + await lang.get_text(uid, "balance", balance=bal) + f"\n" + await lang.get_text(uid, "referral_link", link=ref_link))
        return
    if "пом" in text or "❓" in text:
        await m.answer(await lang.get_text(uid, "help"))
        return
    if "🛒" in text or "подпис" in text or "моя подписка" in text:
        await m.answer(await lang.get_text(uid, "choose_tariff"), reply_markup=tariffs_kb(uid))
        return
    if "пополн" in text or "💳" in text:
        await m.answer("Выберите тариф для оплаты:", reply_markup=tariffs_kb(uid))
        return
    await m.answer("Нажмите кнопку внизу.", reply_markup=main_menu_kb(uid))

@dp.callback_query(lambda c: c.data and c.data.startswith("buy:"))
async def cb_buy(c: types.CallbackQuery):
    key = c.data.split(":",1)[1]
    plan = config.PRICES.get(key)
    if not plan:
        await c.answer("Unknown plan")
        return
    import uuid
    payment_uuid = str(uuid.uuid4())
    await database.create_order(c.from_user.id, key, plan["days"], plan["price_usd"], plan["price_rub"], "USD", payment_uuid)
    pay_url = f"https://pay.example/create?order_id={payment_uuid}"
    img = qrcode.make(pay_url)
    bio = BytesIO()
    bio.name = "qr.png"
    img.save(bio, "PNG")
    bio.seek(0)
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Оплатить картой", url=pay_url))
    await c.message.answer_photo(photo=bio, caption=f"Оплатите {plan['price_usd']}$\nOrder: {payment_uuid}", reply_markup=kb)
    await c.answer()

@dp.message(commands=["admin"])
async def cmd_admin(m: types.Message):
    if m.from_user.id not in config.ADMIN_IDS:
        await m.answer(await lang.get_text(m.from_user.id, "admin_only"))
        return
    stats = await database.get_stats()
    text = f"Users: {stats['users']}\nPaid orders: {stats['paid_orders']}\nRevenue USD: {stats['revenue_usd']}"
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Создать промокод", "Сделать рассылку")
    kb.add("Список выводов", "Статистика")
    await m.answer(text, reply_markup=kb)

async def main():
    await database.init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
