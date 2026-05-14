# lang.py
import aiosqlite
import config

TRANSLATIONS = {
    "ru": {
        "start": "Добро пожаловать в ULTROvpn!\nНижнее меню внизу.",
        "menu": "Выберите действие:",
        "buy": "🛒 Купить VPN",
        "my_key": "🔑 Мой ключ",
        "profile": "👤 Профиль",
        "help": "❓ Помощь",
        "choose_tariff": "Выберите тариф:",
        "pay_methods": "Выберите способ оплаты:",
        "pay_button": "Перейти к оплате",
        "check_payment": "Проверить оплату",
        "success_payment": "Оплата подтверждена! Ваш ключ: {link}",
        "admin_only": "Доступно только администраторам.",
        "enter_promocode": "Введите промокод или нажмите пропустить.",
        "lang_changed": "Язык изменён.",
        "profile_title": "Профиль пользователя",
        "balance": "Баланс: {balance} USDT",
        "referral_link": "Ваша реферальная ссылка: {link}",
        "withdraw_min": "Минимальная сумма вывода {min} USDT",
        "withdraw_requested": "Запрос на вывод отправлен администрации.",
        "promo_invalid": "Промокод недействителен или истёк.",
        "promo_applied": "Промокод применён: {discount}",
    },
    "en": {
        "start": "Welcome to ULTROvpn!\nBottom menu below.",
        "menu": "Choose action:",
        "buy": "🛒 Buy VPN",
        "my_key": "🔑 My key",
        "profile": "👤 Profile",
        "help": "❓ Help",
        "choose_tariff": "Choose a tariff:",
        "pay_methods": "Choose payment method:",
        "pay_button": "Proceed to pay",
        "check_payment": "Check payment",
        "success_payment": "Payment confirmed! Your key: {link}",
        "admin_only": "Admin access only.",
        "enter_promocode": "Enter promo code or skip.",
        "lang_changed": "Language changed.",
        "profile_title": "User profile",
        "balance": "Balance: {balance} USDT",
        "referral_link": "Your referral link: {link}",
        "withdraw_min": "Minimum withdrawal {min} USDT",
        "withdraw_requested": "Withdrawal request sent to admins.",
        "promo_invalid": "Promo code invalid or expired.",
        "promo_applied": "Promo applied: {discount}",
    },
    "uz": {
        "start": "ULTROvpn ga xush kelibsiz!\nPastdagi menyu.",
        "menu": "Harakatni tanlang:",
        "buy": "🛒 VPN sotib olish",
        "my_key": "🔑 Mening kalitim",
        "profile": "👤 Profil",
        "help": "❓ Yordam",
        "choose_tariff": "Tarifni tanlang:",
        "pay_methods": "To'lov usulini tanlang:",
        "pay_button": "To'lovga o'tish",
        "check_payment": "To'lovni tekshirish",
        "success_payment": "To'lov tasdiqlandi! Sizning kalitingiz: {link}",
        "admin_only": "Faqat adminlarga ruxsat.",
        "enter_promocode": "Promo kodni kiriting yoki o‘tkazing.",
        "lang_changed": "Til o'zgартирилди.",
        "profile_title": "Foydalanuvchi profili",
        "balance": "Balans: {balance} USDT",
        "referral_link": "Sizning referal havolangiz: {link}",
        "withdraw_min": "Minimal yechib olish {min} USDT",
        "withdraw_requested": "Yechib olish so‘rovi adminlarga yuborildi.",
        "promo_invalid": "Promo kod noto'g'ri yoki muddati tugagan.",
        "promo_applied": "Promo qo'llanildi: {discount}",
    }
}

async def get_user_lang(user_id: int) -> str:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
        r = await cur.fetchone()
        return r["language"] if r else "ru"

async def get_text(user_id: int, key: str, **kwargs) -> str:
    lang_code = await get_user_lang(user_id)
    texts = TRANSLATIONS.get(lang_code, TRANSLATIONS["ru"])
    template = texts.get(key) or texts.get("lang_changed") if key.startswith("lang_changed") else texts.get(key, key)
    return template.format(**kwargs)
