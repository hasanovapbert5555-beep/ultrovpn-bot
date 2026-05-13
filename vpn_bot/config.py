import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",")]
DATABASE_URL = os.getenv("DATABASE_URL")

PRICES = {
    "1_month": int(os.getenv("PRICE_1_MONTH", 50)),
    "3_months": int(os.getenv("PRICE_3_MONTH", 135)),
    "6_months": int(os.getenv("PRICE_6_MONTH", 240)),
    "12_months": int(os.getenv("PRICE_12_MONTH", 450)),
}

REFERRAL_BONUS_DAYS = int(os.getenv("REFERRAL_BONUS_DAYS", 3))

# Сервера
SERVERS = {
    1: {"name": "🇺🇸 США", "api_url": os.getenv("OUTLINE_API_URL_1"), "cert": os.getenv("OUTLINE_CERT_SHA256_1")},
    2: {"name": "🇳🇱 Нидерланды", "api_url": os.getenv("OUTLINE_API_URL_2"), "cert": os.getenv("OUTLINE_CERT_SHA256_2")},
}
