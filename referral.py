from typing import Dict, Any
from db import get_user, get_user_by_referral_code

async def process_referral_link(referral_code: str, new_user_id: int) -> bool:
    """Обрабатывает реферальную ссылку при регистрации"""
    referrer_id = await get_user_by_referral_code(referral_code)
    
    if referrer_id and referrer_id != new_user_id:
        # Проверяем, не зарегистрирован ли уже пользователь
        user = await get_user(new_user_id)
        if not user or not user['referred_by']:
            from db import register_user
            await register_user(new_user_id, referred_by=referrer_id)
            return True
    
    return False

async def get_referral_stats(telegram_id: int) -> Dict[str, Any]:
    """Получает статистику реферальной системы"""
    user = await get_user(telegram_id)
    
    if not user:
        return {
            'referral_link': '',
            'total_referrals': 0,
            'active_referrals': 0,
            'bonus_days_earned': 0
        }
    
    referral_link = f"https://t.me/your_bot?start={user['referral_code']}"
    
    return {
        'referral_link': referral_link,
        'total_referrals': user['total_referrals'],
        'active_referrals': user['active_referrals'],
        'bonus_days_earned': user['bonus_days_earned']
    }
