import aiohttp
import json
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from config import CRYPTOBOT_TOKEN, CRYPTOBOT_API_URL, TARIFFS

class CryptoBotAPI:
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            'Crypto-Pay-API-Token': token,
            'Content-Type': 'application/json'
        }
        self.checked_invoices = set()  # Для отслеживания уже проверенных счетов
    
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
    
    async def get_invoices(self, status: str = 'active') -> Optional[list]:
        """Получает список счетов"""
        async with aiohttp.ClientSession() as session:
            url = f"{CRYPTOBOT_API_URL}/getInvoices"
            payload = {'status': status}
            
            try:
                async with session.post(url, headers=self.headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('ok'):
                            return data['result']['items']
                    return []
            except Exception as e:
                print(f"Error getting invoices: {e}")
                return []

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

async def check_payment_status(invoice_id: str) -> Optional[str]:
    """Проверяет статус платежа"""
    invoices = await cryptobot.get_invoices('active')
    for invoice in invoices:
        if invoice['invoice_id'] == invoice_id:
            return invoice['status']
    return None

async def process_paid_invoice(invoice_id: str) -> bool:
    """Обрабатывает оплаченный счет"""
    from db import confirm_payment, update_subscription, get_user, update_referral_stats
    from config import TARIFFS
    
    # Получаем информацию о платеже
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

async def payment_polling_loop(bot):
    """Фоновый процесс для проверки статуса платежей"""
    from db import get_all_users
    
    print("🔄 Payment polling loop started")
    
    while True:
        try:
            # Получаем все активные счета
            invoices = await cryptobot.get_invoices('active')
            
            for invoice in invoices:
                invoice_id = invoice['invoice_id']
                
                # Проверяем статус
                if invoice.get('status') == 'paid':
                    # Обрабатываем оплату
                    success = await process_paid_invoice(invoice_id)
                    
                    if success:
                        # Получаем информацию о платеже
                        from db import confirm_payment
                        result = await confirm_payment(invoice_id)
                        if result:
                            telegram_id, tariff_key = result
                            # Уведомляем пользователя
                            try:
                                await bot.send_message(
                                    telegram_id,
                                    f"✅ <b>Платеж подтвержден!</b>\n\n"
                                    f"🎉 Ваша подписка {tariff_key.upper()} активирована!\n"
                                    f"🌐 Используйте кнопку «Подключить VPN» для настройки.",
                                    parse_mode="HTML"
                                )
                            except:
                                pass
        
        except Exception as e:
            print(f"Error in payment polling: {e}")
        
        # Проверяем каждые 10 секунд
        await asyncio.sleep(10)
