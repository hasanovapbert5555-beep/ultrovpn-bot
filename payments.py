import asyncio
import aiohttp
from datetime import datetime
from config import load_config

CONFIG = load_config()

CRYPTOBOT_BASE = CONFIG.get("CRYPTOBOT_BASE_URL")
CRYPTOBOT_API_KEY = CONFIG.get("CRYPTOBOT_API_KEY")
CURRENCY = CONFIG.get("CRYPTOBOT_CURRENCY", "RUB")

# Примерная структура работы с CryptoBot API
async def create_invoice(user_id: int, amount_rub: float, description: str) -> dict:
    # Реализация создания счета через CryptoBot API
    payload = {
        "method": "create_invoice",
        "api_key": CRYPTOBOT_API_KEY,
        "amount": amount_rub,
        "currency": CURRENCY,
        "description": description,
        "uid": user_id
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(CRYPTOBOT_BASE, json=payload) as resp:
            data = await resp.json()
            return data

async def check_invoice(invoice_id: str) -> dict:
    payload = {
        "method": "check_invoice",
        "api_key": CRYPTOBOT_API_KEY,
        "invoice_id": invoice_id
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(CRYPTOBOT_BASE, json=payload) as resp:
            return await resp.json()

async def handle_payment_webhook(data: dict) -> dict:
    # обработка колбэка от CryptoBot
    # сюда будут приходить: user_id, invoice_id, status, amount
    # возвращаем обработанный результат
    return {"status": "ok"}
