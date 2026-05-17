import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
CRYPTOBOT_TOKEN = os.getenv('CRYPTOBOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))

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

# REALITY настройки (маскируемся под популярный сайт)
REALITY_SETTINGS = {
    'dest': 'www.yahoo.com:443',  # Маскируемся под Yahoo
    'server_names': ['www.yahoo.com'],
    'private_key': '',  # Будет сгенерирован автоматически при первом запуске
    'short_ids': ['6ba85179e30d4fc2']
}
