import asyncio
import hashlib
import json
import os
import subprocess
import uuid
from datetime import datetime, timedelta

from config import load_config
from db import get_or_create_user
from pathlib import Path

CONFIG = load_config()
XRAY_PATH = CONFIG.get("XRAYCorePath", "/usr/local/bin/xray")
CONF_DIR = Path(CONFIG.get("XRAY_CONFIG_DIR", "/etc/xray/v2"))
TEMPLATE_CONF = Path(CONFIG.get("XRAY_TEMPLATE_CONF", "/etc/xray/template_conf.json"))

DEVICE_LIMIT = 5

async def ensure_user_context(user) -> dict:
    # Проверяем лимит устройств
    current = await user.get_active_devices()
    if current >= DEVICE_LIMIT:
        return {"error": "Достигнут лимит устройств."}

    # Генерируем UUID для VLESS
    user_uuid = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()

    # Создаем конфигурацию пользователя (пример шаблона)
    config_hash = hashlib.sha256(f"{user.telegram_id}_{user_uuid}".encode()).hexdigest()

    # Пример формирования VLESS ссылки
    vless_user_link = f"vless://{user_uuid}@vpn.local:443?encryption=none&security=none&flow=xtls-rprx-vision&sni=xray&path={config_hash}"

    # Сохраняем устройство
    await user.increment_devices()

    # В реальности нужно сохранить device в БД и сгенерировать локальный файл конфигурации,
    # а затем перезагрузить Xray-core или применить конфиг через API
    # Здесь — запись в файловую систему как демонстрация
    conf_content = {
        "inbounds": [{
            "port": 443,
            "protocol": "vless",
            "settings": {"clients": [{"id": user_uuid, "flow": "xtls-rprx-vision"}]},
            "streamSettings": {
                "network": "tcp",
                "security": "tls"
            },
            "tag": f"user-{user.telegram_id}"
        }],
        "outbounds": [{"protocol": "freedom"}]
    }

    conf_path = CONF_DIR / f"user_{user.telegram_id}.json"
    conf_path.parent.mkdir(parents=True, exist_ok=True)
    with open(conf_path, "w") as f:
        json.dump(conf_content, f, indent=2)

    # Применение конфигурации через Xray-core можно сделать через api/xray минь
    # Здесь просто возвращаем ссылку
    return {
        "link": vless_user_link,
        "instructions": "Скопируйте ссылку и импортируйте в приложение (HAppr, v2rayNG, Nekobox). Убедитесь, что TLS доступен."
    }
