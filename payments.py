import aiohttp
import json
from typing import Optional, Dict, Any
from datetime import datetime
from config import CRYPTOBOT_TOKEN, CRYPTOBOT_API_URL, TARIFFS

class CryptoBotAPI:
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            'Crypto-Pay-API-Token': token,
            'Content-Type': 'application/json'
        }
    
    async def create_invoice(self, amount: float, currency: str = 'USDT', description: str = 'VPN Subscription') -> Optional[Dict[str, Any]]:
        """Создает счет через CryptoBot API"""
        async with aiohttp.ClientSession() as session:
            url = f"{CRYPTOBOT_API_URL}/createInvoice"
            payload = {
                'asset': currency,
                'amount': str(amount),
                'description': description,
                'paid_btn_name': 'callback',
                'paid_btn_url': 'https://t.me/your_bot'
            }
            
            try:
                async with session.post(url, headers=self.headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('ok'):
                            return data['result']
                    return None
            except Exception as e:
                print(f"Error creating invoice: {e}")
                return None
    
    async def get_invoice_status(self, invoice_id: str) -> Optional[str]:
        """Проверяет статус счета"""
        async with aiohttp.ClientSession() as session:
            url = f"{CRYPTOBOT_API_URL}/getInvoices"
            payload = {'invoice_ids': [invoice_id]}
            
            try:
                async with session.post(url, headers=self.headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('ok') and data['result']['items']:
                            return data['result']['items'][0]['status']
                    return None
            except Exception as e:
                print(f"Error checking invoice: {e}")
                return None

cryptobot = CryptoBotAPI(CRYPTOBOT_TOKEN)

async def create_payment(telegram_id: int, tariff_key: str) -> Optional[Dict[str, Any]]:
    """Создает платеж и возвращает информацию для оплаты"""
    tariff = TARIFFS.get(tariff_key)
    if not tariff:
        return None
    
    from db import add_payment
    
    # Создаем счет в CryptoBot
    invoice = await cryptobot.create_invoice(
        amount=tariff['price_usdt'],
        currency='USDT',
        description=f'VPN Subscription - {tariff_key}'
    )
    
    if invoice:
        # Сохраняем платеж в БД
        await add_payment(invoice['invoice_id'], telegram_id, tariff_key, tariff['price_usdt'])
        
        return {
            'invoice_id': invoice['invoice_id'],
            'pay_url': invoice['pay_url'],
            'amount_usdt': tariff['price_usdt']
        }
    
    return None

async def handle_payment_callback(update_data: Dict[str, Any]) -> bool:
    """Обрабатывает callback от CryptoBot"""
    from db import confirm_payment, update_subscription, get_user, update_referral_stats
    from config import TARIFFS
    
    # Проверяем данные callback
    if update_data.get('payload'):
        payload = json.loads(update_data['payload'])
        invoice_id = payload.get('invoice_id')
        
        if invoice_id:
            # Подтверждаем платеж в БД
            telegram_id, tariff_key = await confirm_payment(invoice_id)
            
            if telegram_id and tariff_key:
                tariff = TARIFFS.get(tariff_key)
                if tariff:
                    # Обновляем подписку пользователя
                    await update_subscription(telegram_id, tariff['days'])
                    
                    # Проверяем реферальную связь
                    user = await get_user(telegram_id)
                    if user and user['referred_by']:
                        # Начисляем бонус рефереру
                        await update_referral_stats(user['referred_by'], telegram_id)
                    
                    return True
    
    return False
