import uuid
import json
import subprocess
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
import hashlib

# Глобальный словарь для хранения активных конфигураций Xray
# В реальном проекте здесь должна быть интеграция с Xray API
class XrayManager:
    def __init__(self):
        self.xray_config_path = '/usr/local/etc/xray/config.json'
        
    def generate_uuid(self) -> str:
        return str(uuid.uuid4())
    
    def generate_vless_link(self, uuid: str, telegram_id: int, server_address: str = 'your-server.com', port: int = 443) -> str:
        """Генерирует VLESS ссылку для импорта"""
        # Базовый шаблон VLESS URI
        config = {
            'v': '2',
            'ps': f'VPN_{telegram_id}',
            'add': server_address,
            'port': str(port),
            'id': uuid,
            'aid': '0',
            'scy': 'auto',
            'net': 'ws',
            'type': 'none',
            'host': server_address,
            'path': '/vless',
            'tls': 'tls'
        }
        
        # Кодируем в URL параметры
        import urllib.parse
        params = urllib.parse.urlencode(config)
        return f"vless://{uuid}@{server_address}:{port}?{params}#VPN_{telegram_id}"
    
    def generate_config_file(self, uuid: str, telegram_id: int) -> str:
        """Генерирует конфигурационный файл для Xray"""
        config_template = {
            "inbounds": [],
            "outbounds": [
                {
                    "protocol": "freedom",
                    "settings": {}
                }
            ]
        }
        
        # Создаем inbound для пользователя
        inbound = {
            "protocol": "vless",
            "port": 443,
            "settings": {
                "clients": [
                    {
                        "id": uuid,
                        "flow": f"xtls-rprx-vision-{telegram_id}",
                        "email": f"user_{telegram_id}"
                    }
                ],
                "decryption": "none"
            },
            "streamSettings": {
                "network": "ws",
                "security": "tls",
                "tlsSettings": {
                    "certificates": [
                        {
                            "certificateFile": "/path/to/cert.pem",
                            "keyFile": "/path/to/key.pem"
                        }
                    ]
                },
                "wsSettings": {
                    "path": "/vless"
                }
            }
        }
        
        config_template["inbounds"].append(inbound)
        return json.dumps(config_template, indent=2)
    
    async def add_user_to_xray(self, uuid: str, telegram_id: int) -> bool:
        """Добавляет пользователя в Xray (через API или перезагрузку конфига)"""
        try:
            # Здесь должна быть реальная интеграция с Xray API
            # Для демонстрации создаем файл конфига
            config = self.generate_config_file(uuid, telegram_id)
            config_hash = hashlib.md5(config.encode()).hexdigest()
            
            # В реальном проекте: отправка API запроса к Xray
            # или перезапись config.json и перезагрузка Xray
            
            # Симулируем успешное добавление
            await asyncio.sleep(0.1)
            return True
        except Exception as e:
            print(f"Error adding user to Xray: {e}")
            return False
    
    async def remove_user_from_xray(self, uuid: str) -> bool:
        """Удаляет пользователя из Xray"""
        try:
            # Здесь должна быть реальная интеграция с Xray API
            await asyncio.sleep(0.1)
            return True
        except Exception as e:
            print(f"Error removing user from Xray: {e}")
            return False

xray_manager = XrayManager()

async def generate_vpn_config(telegram_id: int, device_name: str) -> Optional[Dict[str, Any]]:
    """Генерирует VPN конфиг для пользователя"""
    from db import get_user, add_device, get_devices
    
    # Проверяем подписку
    user = await get_user(telegram_id)
    if not user or user['subscription_end'] < int(datetime.now().timestamp()):
        return None
    
    # Проверяем количество устройств
    devices = await get_devices(telegram_id)
    if len(devices) >= 5:
        return None
    
    # Генерируем UUID и конфиг
    new_uuid = xray_manager.generate_uuid()
    vless_link = xray_manager.generate_vless_link(new_uuid, telegram_id)
    
    # Добавляем пользователя в Xray
    success = await xray_manager.add_user_to_xray(new_uuid, telegram_id)
    if not success:
        return None
    
    # Сохраняем устройство
    config_hash = hashlib.md5(vless_link.encode()).hexdigest()
    await add_device(telegram_id, device_name, new_uuid, config_hash)
    
    return {
        'uuid': new_uuid,
        'vless_link': vless_link,
        'device_name': device_name
    }

async def revoke_device(telegram_id: int, device_id: int) -> bool:
    """Отзывает доступ для устройства"""
    from db import get_devices, remove_device
    
    devices = await get_devices(telegram_id)
    device = next((d for d in devices if d['id'] == device_id), None)
    
    if device:
        await xray_manager.remove_user_from_xray(device['uuid'])
        return await remove_device(device_id, telegram_id)
    
    return False
