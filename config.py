import os
from dotenv import load_dotenv

def load_config():
    load_dotenv()
    cfg = {
        "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
        "ADMIN_TELEGRAM_ID": int(os.getenv("ADMIN_TELEGRAM_ID", 0)),
        "XRAYCorePath": os.getenv("XRAYCorePath", "/usr/local/bin/xray"),
        "XRAY_CONFIG_DIR": os.getenv("XRAY_CONFIG_DIR", "/etc/xray/v2"),
        "XRAY_TEMPLATE_CONF": os.getenv("XRAY_TEMPLATE_CONF", "/etc/xray/template_conf.json"),
        "DB_PATH": os.getenv("DB_PATH", "sqlite+aiosqlite:///vpnbot.db"),
        "REFERRAL_BASE_URL": os.getenv("REFERRAL_BASE_URL", "https://t.me/ваш_бот?start="),
        "CRYPTOBOT_BASE_URL": os.getenv("CRYPTOBOT_BASE_URL", "https://crypt.bot/api"),
        "CRYPTOBOT_API_KEY": os.getenv("CRYPTOBOT_API_KEY"),
        "CRYPTOBOT_WEBHOOK_URL": os.getenv("CRYPTOBOT_WEBHOOK_URL"),
        "CRYPTOBOT_CURRENCY": os.getenv("CRYPTOBOT_CURRENCY", "RUB"),
        "LOGS_DIR": os.getenv("LOGS_DIR", "./logs"),
    }
    return cfg
