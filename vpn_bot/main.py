import asyncio
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, PreCheckoutQueryHandler
from config import BOT_TOKEN
from database import init_db
from handlers.user import start, mykey_callback, revoke_key_callback, change_lang_callback, mystats_callback
from handlers.payment import buy_callback, buy_plan_callback, pre_checkout, successful_payment
from handlers.admin import admin_panel, users_list, broadcast
from handlers.support import support_callback, save_ticket
from scheduler import start_scheduler

async def main():
    await init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("users", users_list))
    app.add_handler(CommandHandler("broadcast", broadcast))

    # Callback handlers
    app.add_handler(CallbackQueryHandler(buy_callback, pattern="^buy$"))
    app.add_handler(CallbackQueryHandler(buy_plan_callback, pattern="^buy_\\d+_month[s]?$"))
    app.add_handler(CallbackQueryHandler(mykey_callback, pattern="^mykey$"))
    app.add_handler(CallbackQueryHandler(revoke_key_callback, pattern="^revoke_key$"))
    app.add_handler(CallbackQueryHandler(change_lang_callback, pattern="^change_lang$"))
    app.add_handler(CallbackQueryHandler(mystats_callback, pattern="^mystats$"))
    app.add_handler(CallbackQueryHandler(support_callback, pattern="^support$"))

    # Платежи
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))

    # Сообщения
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_ticket))

    start_scheduler(app)
    print("✅ Бот запущен")
    await app.run_polling()

if name == "__main__":
    asyncio.run(main())