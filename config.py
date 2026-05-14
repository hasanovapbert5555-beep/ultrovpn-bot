# config.py
import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "123456789").split(",")]
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@support")

SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("SERVER_PORT", "443"))
SNI_DOMAIN = os.getenv("SNI_DOMAIN", "example.com")

PAY_PROVIDER = os.getenv("PAY_PROVIDER", "cryptomus")
PAY_MERCHANT_ID = os.getenv("PAY_MERCHANT_ID", "merchant_id")
PAY_API_KEY = os.getenv("PAY_API_KEY", "api_key")
PAY_WEBHOOK_SECRET = os.getenv("PAY_WEBHOOK_SECRET", "webhook_secret")
WEBHOOK_PUBLIC = os.getenv("WEBHOOK_PUBLIC", "https://your.domain/webhook")

DB_PATH = os.getenv("DB_PATH", "ultrovpn.db")
LOGO_PATH = os.getenv("LOGO_PATH", "logo.png")

PRICES = {
    "1m": {"days": 30,  "price_usd": 5.0,  "price_rub": 450, "name": {"ru":"1 месяц","en":"1 month","uz":"1 oy"}},
    "3m": {"days": 90,  "price_usd": 13.0, "price_rub": 1170,"name": {"ru":"3 месяца","en":"3 months","uz":"3 oy"}},
    "6m": {"days": 180, "price_usd": 23.0, "price_rub": 2070,"name": {"ru":"6 месяцев","en":"6 months","uz":"6 oy"}},
    "12m":{"days": 365, "price_usd": 40.0, "price_rub": 3600,"name": {"ru":"12 месяцев","en":"12 months","uz":"12 oy"}},
}

REFERRAL_PERCENTS = {1: 15, 2: 5, 3: 3}

MIN_WITHDRAW = float(os.getenv("MIN_WITHDRAW", "10.0"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
