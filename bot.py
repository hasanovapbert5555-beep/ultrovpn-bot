import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import config
import database

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# Клавиатура
kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📡 Получить VPN")],
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="❓ Помощь")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def start(m: types.Message):
    await database.add_user(m.from_user.id, m.from_user.username)
    await m.answer(
        "🚀 Добро пожаловать в ULTROvpn!\n\n"
        "Нажмите «Получить VPN» чтобы получить доступ.\n"
        "Оплата: 5$ в месяц. Карты РФ работают.",
        reply_markup=kb
    )

@dp.message(lambda m: m.text == "📡 Получить VPN")
async def get_vpn(m: types.Message):
    vmess_link = f"vmess://eyJhZGQiOiJ7config.SERVER_HOST}iiwidhrtIjoiODQzIiwiaWQiOiIxMjM0NTY3OC05MC1hYmNkZWYiLCJhaWQiOiIwIiwibmV0IjoidGNwIn0="
    
    await m.answer(
        f"✅ Ваша подписка активирована!\n\n"
        f"📡 VMess ссылка:\n`{vmess_link}`\n\n"
        f"📱 Инструкция:\n"
        f"1. Скачайте приложение v2rayNG (Android) / Streisand (iOS)\n"
        f"2. Нажмите + → Импорт из буфера обмена\n"
        f"3. Вставьте ссылку\n\n"
        f"⏱ Действует 30 дней",
        parse_mode="Markdown"
    )

@dp.message(lambda m: m.text == "👤 Профиль")
async def profile(m: types.Message):
    await m.answer(f"👤 Ваш ID: {m.from_user.id}\n📅 Дата регистрации: сегодня\n💳 Баланс: 0 USDT")

@dp.message(lambda m: m.text == "❓ Помощь")
async def help_msg(m: types.Message):
    await m.answer("По вопросам: @support\nПополнить баланс: /pay")

@dp.message(Command("pay"))
async def pay(m: types.Message):
    await m.answer("💰 Для оплаты переведите 5$ на карту:\n1234 5678 9012 3456\n\nПосле оплаты нажмите «Получить VPN»")

async def main():
    await database.init_db()
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
EOF
