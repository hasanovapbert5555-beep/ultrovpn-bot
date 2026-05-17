from urllib.parse import urlencode

from config import load_config
from db import get_or_create_user

CONFIG = load_config()
REF_BASE = CONFIG.get("REFERRAL_BASE_URL", "")

async def get_referral_info(telegram_id: int) -> str:
    user = await get_or_create_user(telegram_id)
    # Здесь нужен реф-код и сводка
    invited = 0
    activated = 0
    # В реальности: запрашиваем данные из БД
    profile = "Профиль рефералов:\n" \
              f"Приглашено: {invited}\n" \
              f"Активировано: {activated}\n" \
              f"Бонус дней: 7 за каждого друга, купившего тариф."
    link = f"{REF_BASE}{telegram_id}"
    return f"{profile}\nПригласительная ссылка:\n{link}"
