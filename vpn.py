import uuid
import json
import subprocess
import asyncio
import os
from typing import Optional, Dict, Any
from datetime import datetime
import hashlib
import base64

class XrayManager:
    def __init__(self):
        self.xray_config_path = '/usr/local/etc/xray/config.json'
        self.reality_keys = None
        self._init_reality_keys()
    
    def _init_reality_keys(self):
        """Генерирует ключи REALITY при первом запуске"""
        keys_file = '/usr/local/etc/xray/reality_keys.json'
        
        if os.path.exists(keys_file):
            with open(keys_file, 'r') as f:
                self.reality_keys = json.load(f)
        else:
            # Генерируем новые ключи REALITY
            result = subprocess.run(
                ['xray', 'x25519'],
                capture_output=True,
                text=True
            )
            output = result.stdout
            private_key = None
            public_key = None
            
            for line in output.split('\n'):
                if 'Private key:' in line:
                    private_key = line.split(':')[1].strip()
                elif 'Public key:' in line:
                    public_key = line.split(':')[1].strip()
            
            if private_key and public_key:
                self.reality_keys = {
                    'private_key': private_key,
                    'public_key': public_key
                }
                os.makedirs(os.path.dirname(keys_file), exist_ok=True)
                with open(keys_file, 'w') as f:
                    json.dump(self.reality_keys, f)
    
    def generate_uuid(self) -> str:
        return str(uuid.uuid4())
    
    def generate_vless_reality_link(self, uuid: str, telegram_id: int, server_address: str = 'www.yahoo.com') -> str:
        """Генерирует VLESS+REALITY ссылку"""
        from config import REALITY_SETTINGS
        
        # Формируем параметры для VLESS REALITY
        params = {
            'encryption': 'none',
            'security': 'reality',
            'pbk': self.reality_keys['public_key'],
            'sid': REALITY_SETTINGS['short_ids'][0],
            'spx': '/',
            'type': 'tcp',
            'flow': 'xtls-rprx-vision',
            'sni': 'www.yahoo.com',
            'fp': 'chrome'
        }
        
        # Кодируем параметры
        import urllib.parse
        param_str = urllib.parse.urlencode(params)
        
        # Формируем полную ссылку
        vless_link = f"vless://{uuid}@{server_address}:443?{param_str}#VPN_{telegram_id}"
        return vless_link
    
    def generate_config_for_user(self, uuid: str, telegram_id: int) -> dict:
        """Генерирует конфигурацию для добавления пользователя в Xray"""
        from config import REALITY_SETTINGS
        
        client_config = {
            "id": uuid,
            "flow": f"xtls-rprx-vision",
            "email": f"user_{telegram_id}",
            "fingerprint": "chrome"
        }
        
        return client_config
    
    async def add_user_to_xray(self, uuid: str, telegram_id: int) -> bool:
        """Добавляет пользователя в Xray через API"""
        try:
            # Генерируем конфиг для пользователя
            client_config = self.generate_config_for_user(uuid, telegram_id)
            
            # Здесь должен быть API запрос к Xray
            # Для реальной работы нужно включить API в Xray config.json
            # и использовать xray-api или прямое редактирование конфига с перезагрузкой
            
            # Вариант 1: Прямое редактирование config.json (проще для начала)
            if os.path.exists(self.xray_config_path):
                with open(self.xray_config_path, 'r') as f:
                    config = json.load(f)
                
                # Добавляем клиента в inbound
                if 'inbounds' in config and len(config['inbounds']) > 0:
                    if 'settings' not in config['inbounds'][0]:
                        config['inbounds'][0]['settings'] = {}
                    if 'clients' not in config['inbounds'][0]['settings']:
                        config['inbounds'][0]['settings']['clients'] = []
                    
                    # Проверяем, нет ли уже такого пользователя
                    existing = False
                    for client in config['inbounds'][0]['settings']['clients']:
                        if client.get('email') == f"user_{telegram_id}":
                            existing = True
                            break
                    
                    if not existing:
                        config['inbounds'][0]['settings']['clients'].append(client_config)
                        
                        # Сохраняем конфиг
                        with open(self.xray_config_path, 'w') as f:
                            json.dump(config, f, indent=2)
                        
                        # Перезагружаем Xray
                        subprocess.run(['systemctl', 'reload', 'xray'], capture_output=True)
                        await asyncio.sleep(1)
            
            return True
        except Exception as e:
            print(f"Error adding user to Xray: {e}")
            return False
    
    async def remove_user_from_xray(self, uuid: str, email: str = None) -> bool:
        """Удаляет пользователя из Xray"""
        try:
            if os.path.exists(self.xray_config_path):
                with open(self.xray_config_path, 'r') as f:
                    config = json.load(f)
                
                if 'inbounds' in config and len(config['inbounds']) > 0:
                    if 'settings' in config['inbounds'][0] and 'clients' in config['inbounds'][0]['settings']:
                        # Удаляем клиента
                        clients = config['inbounds'][0]['settings']['clients']
                        if email:
                            clients = [c for c in clients if c.get('email') != email]
                        else:
                            clients = [c for c in clients if c.get('id') != uuid]
                        
                        config['inbounds'][0]['settings']['clients'] = clients
                        
                        # Сохраняем конфиг
                        with open(self.xray_config_path, 'w') as f:
                            json.dump(config, f, indent=2)
                        
                        # Перезагружаем Xray
                        subprocess.run(['systemctl', 'reload', 'xray'], capture_output=True)
                        await asyncio.sleep(1)
            
            return True
        except Exception as e:
            print(f"Error removing user from Xray: {e}")
            return False
    
    async def setup_reality_inbound(self) -> bool:
        """Настраивает REALITY inbound в Xray"""
        from config import REALITY_SETTINGS
        
        if not self.reality_keys:
            return False
        
        inbound_config = {
            "port": 443,
            "protocol": "vless",
            "settings": {
                "clients": [],
                "decryption": "none"
            },
            "streamSettings": {
                "network": "tcp",
                "security": "reality",
                "realitySettings": {
                    "dest": REALITY_SETTINGS['dest'],
                    "serverNames": REALITY_SETTINGS['server_names'],
                    "privateKey": self.reality_keys['private_key'],
                    "shortIds": REALITY_SETTINGS['short_ids']
                }
            },
            "sniffing": {
                "enabled": True,
                "destOverride": ["http", "tls"]
            }
        }
        
        try:
            # Читаем существующий конфиг
            if os.path.exists(self.xray_config_path):
                with open(self.xray_config_path, 'r') as f:
                    config = json.load(f)
            else:
                config = {
                    "log": {"loglevel": "warning"},
                    "inbounds": [],
                    "outbounds": [{"protocol": "freedom", "tag": "direct"}]
                }
            
            # Заменяем или добавляем inbound
            inbound_exists = False
            for i, inbound in enumerate(config['inbounds']):
                if inbound.get('port') == 443:
                    config['inbounds'][i] = inbound_config
                    inbound_exists = True
                    break
            
            if not inbound_exists:
                config['inbounds'].append(inbound_config)
            
            # Сохраняем конфиг
            os.makedirs(os.path.dirname(self.xray_config_path), exist_ok=True)
            with open(self.xray_config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Перезапускаем Xray
            subprocess.run(['systemctl', 'restart', 'xray'], capture_output=True)
            await asyncio.sleep(2)
            
            return True
        except Exception as e:
            print(f"Error setting up REALITY inbound: {e}")
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
    vless_link = xray_manager.generate_vless_reality_link(new_uuid, telegram_id)
    
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
        await xray_manager.remove_user_from_xray(device['uuid'], f"user_{telegram_id}")
        return await remove_device(device_id, telegram_id)
    
    return False
