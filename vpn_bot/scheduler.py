from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from sqlalchemy import select
from database import AsyncSessionLocal
from models import Subscription, Key, User
from utils.outline_api import delete_outline_key
from config import SERVERS

async def check_expired_subscriptions(app):
    async with AsyncSessionLocal() as session:
        expired = await session.execute(
            select(Subscription).where(
                Subscription.is_active == True,
                Subscription.end_date < datetime.utcnow()
            )
        )
        for sub in expired.scalars().all():
            sub.is_active = False
            key = await session.get(Key, sub.key_id)
            if key:
                server = SERVERS.get(key.server_id)
                if server:
                    await delete_outline_key(server["api_url"], server["cert"], key.key_string)
            await session.commit()

async def send_reminders(app):
    async with AsyncSessionLocal() as session:
        three_days = datetime.utcnow() + timedelta(days=3)
        subs = await session.execute(
            select(Subscription, User).join(User).where(
                Subscription.is_active == True,
                Subscription.end_date <= three_days,
                Subscription.end_date > datetime.utcnow()
            )
        )
        for sub, user in subs.all():
            days_left = (sub.end_date - datetime.utcnow()).days
            try:
                await app.bot.send_message(
                    user.telegram_id,
                    f"⚠️ Ваша подписка истекает через {days_left} дня(ей).\nПродлите доступ в /buy"
                )
            except:
                pass

def start_scheduler(app):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_expired_subscriptions, "interval", hours=1, args=[app])
    scheduler.add_job(send_reminders, "interval", hours=6, args=[app])
    scheduler.start()