from functools import wraps
from datetime import datetime, timedelta

user_last_command = {}

def rate_limit(seconds=15):
    def decorator(func):
        @wraps(func)
        async def wrapper(update, context, *args, **kwargs):
            user_id = update.effective_user.id
            now = datetime.utcnow()
            if user_id in user_last_command and now - user_last_command[user_id] < timedelta(seconds=seconds):
                await update.callback_query.answer("⏳ Слишком часто! Подождите.", show_alert=True)
                return
            user_last_command[user_id] = now
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator