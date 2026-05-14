# payments.py
import logging
import secrets
from datetime import datetime, timedelta
import config
import database
import aiosqlite
import json
import base64
import uuid
from io import BytesIO
import qrcode

logger = logging.getLogger(__name__)

# --- Generators: vmess and simple proxy ---
def generate_vmess_payload(user_id: int, server_host: str, server_port: int, client_id: str = None,
                           alter_id: int = 0, security: str = "auto", network: str = "tcp", tls: bool = False,
                           path: str = "", host_header: str = ""):
    if client_id is None:
        client_id = str(uuid.uuid4())
    payload = {
        "v": "2",
        "ps": f"ULTROvpn_{user_id}",
        "add": server_host,
        "port": str(server_port),
        "id": client_id,
        "aid": str(alter_id),
        "net": network,
        "type": "none",
        "host": host_header or "",
        "path": path or "",
        "tls": "tls" if tls else ""
    }
    return payload

def vmess_link_from_payload(payload: dict) -> str:
    j = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    b = base64.b64encode(j.encode()).decode()
    return f"vmess://{b}"

def vmess_config_file(payload: dict) -> bytes:
    return json.dumps(payload, indent=2, ensure_ascii=False).encode()

def generate_proxy_line(user: str, password: str, host: str, port: int, proto: str = "http"):
    proto = proto.lower()
    if password:
        return f"{proto}://{user}:{password}@{host}:{port}"
    else:
        return f"{proto}://{host}:{port}"

def make_qr_bytes(text: str) -> bytes:
    img = qrcode.make(text)
    bio = BytesIO()
    bio.name = "qr.png"
    img.save(bio, "PNG")
    bio.seek(0)
    return bio.read()

# --- Example: create hysteria-like key (kept for backward compatibility) ---
async def create_hysteria_key(user_id:int, days:int):
    password = secrets.token_urlsafe(12)
    link = f"hysteria2://{password}@{config.SERVER_HOST}:{config.SERVER_PORT}?insecure=0&sni={config.SNI_DOMAIN}#ULTROvpn_{user_id}"
    return {"password": password, "link": link}

# --- Referral distribution (credits) ---
async def distribute_referrals(user_id:int, price_usd:float):
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT referrer_id FROM users WHERE user_id = ?", (user_id,))
        r = await cur.fetchone()
        ref1 = r["referrer_id"] if r else None

    if ref1:
        lvl1_amt = config.REFERRAL_PERCENTS.get(1,0) * price_usd / 100.0
        await database.add_referral_earning(ref1, user_id, lvl1_amt, 1)
        await database.credit_user_balance(ref1, lvl1_amt)

        async with aiosqlite.connect(config.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT referrer_id FROM users WHERE user_id = ?", (ref1,))
            r2 = await cur.fetchone()
            ref2 = r2["referrer_id"] if r2 else None

        if ref2:
            lvl2_amt = config.REFERRAL_PERCENTS.get(2,0) * price_usd / 100.0
            await database.add_referral_earning(ref2, user_id, lvl2_amt, 2)
            await database.credit_user_balance(ref2, lvl2_amt)

            async with aiosqlite.connect(config.DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                cur = await db.execute("SELECT referrer_id FROM users WHERE user_id = ?", (ref2,))
                r3 = await cur.fetchone()
                ref3 = r3["referrer_id"] if r3 else None

            if ref3:
                lvl3_amt = config.REFERRAL_PERCENTS.get(3,0) * price_usd / 100.0
                await database.add_referral_earning(ref3, user_id, lvl3_amt, 3)
                await database.credit_user_balance(ref3, lvl3_amt)

# --- Main: handle successful payment ---
async def handle_successful_payment(payment_uuid:str, payment_payload:dict, bot=None):
    res = await database.set_order_paid_if_pending(payment_uuid, payment_payload)
    if res is None:
        logger.warning("Order not found for %s", payment_uuid)
        return {"status":"not_found"}
    if res.get("already_paid"):
        logger.info("Already processed %s", payment_uuid)
        return {"status":"already_processed"}

    order = res["order"]
    user_id = order["user_id"]
    days = order.get("days", 30)
    price_usd = order.get("price_usd", 0.0)

    # Generate vmess and http proxy credentials
    vmess_id = str(uuid.uuid4())
    proxy_pass = secrets.token_urlsafe(8)
    expiry_ts = int((datetime.utcnow() + timedelta(days=days)).timestamp())

    # Vmess payload (adjust network/path/host/tls to your server settings)
    vmess_payload = generate_vmess_payload(user_id, config.SERVER_HOST, config.SERVER_PORT,
                                           client_id=vmess_id, alter_id=0, network="tcp", tls=False)

    vmess_uri = vmess_link_from_payload(vmess_payload)
    vmess_file = vmess_config_file(vmess_payload)
    vmess_qr = make_qr_bytes(vmess_uri)

    # HTTP proxy line (auth)
    proxy_user = f"user{user_id}"
    proxy_line = generate_proxy_line(proxy_user, proxy_pass, config.SERVER_HOST, config.SERVER_PORT, proto="http")
    proxy_qr = make_qr_bytes(proxy_line)

    # Save generated credentials to DB
    await database.update_user_proxy(user_id, vmess_id=vmess_id, proxy_pass=proxy_pass)

    # Update user's key + expiry fields (keeps backward compatibility)
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("UPDATE users SET key_password = ?, key_expiry = ?, total_spent = COALESCE(total_spent,0) + ? WHERE user_id = ?",
                         (vmess_id, expiry_ts, price_usd, user_id))
        await db.commit()

    # Distribute referrals
    await distribute_referrals(user_id, price_usd)

    # Notify user via bot: send URI, files and QR images
    if bot:
        try:
            await bot.send_message(user_id, f"✅ Оплата подтверждена. Срок до: {datetime.utcfromtimestamp(expiry_ts).strftime('%Y-%m-%d %H:%M:%S')} UTC")
        except Exception:
            logger.exception("Notify user text failed %s", user_id)

        # vmess: send text, file, qr
        try:
            await bot.send_message(user_id, f"vmess: {vmess_uri}")
        except Exception:
            pass
        try:
            bio = BytesIO(vmess_file); bio.name = "vmess.json"; bio.seek(0)
            await bot.send_document(user_id, document=bio, caption="Файл конфигурации vmess")
        except Exception:
            pass
        try:
            bioqr = BytesIO(vmess_qr); bioqr.name = "vmess_qr.png"; bioqr.seek(0)
            await bot.send_photo(user_id, photo=bioqr, caption="QR vmess")
        except Exception:
            pass

        # proxy: send line and qr
        try:
            await bot.send_message(user_id, f"HTTP proxy: {proxy_line}")
        except Exception:
            pass
        try:
            bioqr2 = BytesIO(proxy_qr); bioqr2.name = "proxy_qr.png"; bioqr2.seek(0)
            await bot.send_photo(user_id, photo=bioqr2, caption="QR HTTP proxy")
        except Exception:
            pass

    logger.info("Payment %s processed for order %s", payment_uuid, order["id"])
    return {"status":"processed", "order_id": order["id"], "vmess_uri": vmess_uri, "proxy_line": proxy_line, "expiry": expiry_ts}
