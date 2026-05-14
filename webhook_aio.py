# webhook_aio.py
import asyncio
from aiohttp import web
import hmac, hashlib, json, logging
import config
import payments
from aiogram import Bot

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)
bot = Bot(token=config.BOT_TOKEN)

def verify_hmac_md5(secret: str, body: bytes, header_signature: str) -> bool:
    if not header_signature:
        return False
    hm = hmac.new(secret.encode(), body, hashlib.md5).hexdigest()
    return hmac.compare_digest(hm, header_signature)

async def handle(request):
    body = await request.read()
    header_signature = request.headers.get("X-Signature", "") or request.headers.get("X-Sign", "")
    if not verify_hmac_md5(config.PAY_WEBHOOK_SECRET, body, header_signature):
        logger.warning("Invalid signature")
        return web.Response(status=403, text="invalid signature")
    try:
        data = await request.json()
    except Exception:
        logger.exception("Invalid json")
        return web.Response(status=400, text="invalid json")
    payment_uuid = data.get("order_id") or data.get("payment_id") or data.get("id")
    status = data.get("status") or data.get("state")
    if not payment_uuid:
        return web.Response(status=400, text="no payment id")
    if str(status).lower() in ("paid","success","completed"):
        payment_payload = {"raw": data}
        result = await payments.handle_successful_payment(payment_uuid, payment_payload, bot=bot)
        return web.json_response({"ok": True, "result": result})
    return web.json_response({"ok": True, "ignored": True})

app = web.Application()
app.router.add_post("/webhook", handle)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=5000)
