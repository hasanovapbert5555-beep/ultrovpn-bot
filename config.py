import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
CRYPTOBOT_TOKEN = os.getenv('CRYPTOBOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
XRAY_API_PORT = int(os.getenv('XRAY_API_PORT', 8080))
XRAY_API_USER = os.getenv('XRAY_API_USER', 'admin')
XRAY_API_PASS = os.getenv('XRAY_API_PASS')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', 8443))

# Тарифы в днях и рублях
TARIFFS = {
    '1d': {'days': 1, 'price_rub': 10, 'price_usdt': 0.10},
    '1m': {'days': 30, 'price_rub': 299, 'price_usdt': 3.0},
    '3m': {'days': 90, 'price_rub': 799, 'price_usdt': 8.0},
    '6m': {'days': 180, 'price_rub': 1499, 'price_usdt': 15.0},
    '12m': {'days': 365, 'price_rub': 2799, 'price_usdt': 28.0}
}

# Лимит устройств
MAX_DEVICES = 5

# URL API CryptoBot
CRYPTOBOT_API_URL = 'https://pay.crypt.bot/api'
