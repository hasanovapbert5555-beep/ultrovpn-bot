import uuid
import json
import subprocess
import asyncio
import os
import logging
import urllib.parse
from typing import Optional, Dict, Any
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

class XrayManager:
    def __init__(self):
        from config import XRAY_CONFIG_PATH, XRAY_KEYS_PATH
        self.xray_config_path = XRAY_CONFIG_PATH
        self.keys_file = XRAY_KEYS_PATH
        self.reality_keys = None
        self._init_reality_keys()
    
    def _init_reality_keys(self):
        """Генерирует ключи REALITY при первом запуске"""
        try:
            if os.path.exists(self.keys_file):
                with open(self.keys_file, 'r') as f:
                    self.reality_keys = json.load(f)
                logger.info("✅ REALITY keys loaded from file")
            else:
                # Генерируем новые ключи REALITY
                logger.info("🔑 Generating new REALITY keys...")
                result = subprocess.run(
                    ['xray', 'x25519'],
                    capture_output=True,
                    text=True,
                    timeout=10
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
                    os.makedirs(os.path.dirname(self.keys_file), exist_ok=True)
                    with open(self.keys_file, 'w') as f:
                        json.dump(self.reality_keys, f)
                    logger.info("✅ New REALITY keys generated and saved")
                else:
                    logger.error("❌ Failed to generate REALITY keys")
        except Exception as e:
            logger.error(f"❌ Error initializing REALITY keys: {e}")
            raise
    
    def generate_uuid(self) -> str:
        return str(uuid.uuid4())
    
    def generate_vless_reality_link(self, uuid: str, telegram_id: int, server_address: str = None) -> str:
        """Генерирует VLESS+REALITY ссылку"""
        from config import REALITY_SETTINGS, SERVER_IP
        
        if not server_address:
            server_address = SERVER_IP
        
        if not self.reality_keys:
            raise ValueError("REALITY keys not initialized")
        
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
        
        param_str = urllib.parse.urlencode(params)
        vless_link = f"vless://{uuid}@{server_address}:443?{param_str}#VPN_{telegram_id}"
        
        logger.debug(f"Generated VLESS link for user {telegram_id}")
        return vless_link
    
    def generate_config_for_user(self, uuid: str, telegram_id: int) -> dict:
        """Генерирует конфигурацию для добавления пользователя в Xray"""
        client_config = {
            "id": uuid,
            "flow": "xtls-rprx-vision",
            "email": f"user_{telegram_id}",
            "fingerprint": "chrome"
        }
        return client_config
    
    async def add_user_to_xray(self, uuid: str, telegram_id: int) -> bool:
        """Добавляет пользователя в Xray через редактирование config.json"""
        try:
            logger.info(f"Adding user {telegram_id} to Xray...")
            
            client_config = self.generate_config_for_user(uuid, telegram_id)
            
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
                            logger.warning(f"⚠️ User {telegram_id} already exists in Xray")
                            break
                    
                    if not existing:
                        config['inbounds'][0]['settings']['clients'].append(client_config)
                        
                        # Сохраняем конфиг
                        with open(self.xray_config_path, 'w') as f:
                            json.dump(config, f, indent=2)
                        
                        # Перезагружаем Xray
                        try:
                            subprocess.run(
                                ['systemctl', 'reload', 'xray'],
                                capture_output=True,
                                timeout=10
                            )
                            await asyncio.sleep(1)
                            logger.info(f"✅ User {telegram_id} added to Xray successfully")
                            return True
                        except subprocess.TimeoutExpired:
                            logger.error(f"❌ Timeout reloading Xray for user {telegram_id}")
                            return False
                    else:
                        return True  # Пользователь уже существует
            else:
                logger.error(f"❌ Xray config not found at {self.xray_config_path}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"❌ Error adding user {telegram_id} to Xray: {e}")
            return False
    
    async def remove_user_from_xray(self, telegram_id: int) -> bool:
        """Удаляет пользователя из Xray"""
        try:
            logger.info(f"Removing user {telegram_id} from Xray...")
            email = f"user_{telegram_id}"
            
            if os.path.exists(self.xray_config_path):
                with open(self.xray_config_path, 'r') as f:
                    config = json.load(f)
                
                if 'inbounds' in config and len(config['inbounds']) > 0:
                    if 'settings' in config['inbounds'][0] and 'clients' in config['inbounds'][0]['settings']:
                        # Удаляем клиента по email
                        original_count = len(config['inbounds'][0]['settings']['clients'])
                        config['inbounds'][0]['settings']['clients'] = [
                            c for c in config['inbounds'][0]['settings']['clients']
                            if c.get('email') != email
                        ]
                        new_count = len(config['inbounds'][0]['settings']['clients'])
                        
                        if new_count < original_count:
                            # Сохраняем конфиг
                            with open(self.xray_config_path, 'w') as f:
                                json.dump(config, f, indent=2)
                            
                            # Перезагружаем Xray
                            try:
                                subprocess.run(
                                    ['systemctl', 'reload', 'xray'],
                                    capture_output=True,
                                    timeout=10
                                )
                                await asyncio.sleep(1)
                                logger.info(f"✅ User {telegram_id} removed from Xray successfully")
                                return True
                            except subprocess.TimeoutExpired:
                                logger.error(f"❌ Timeout reloading Xray for user {telegram_id}")
                                return False
                        else:
                            logger.warning(f"⚠️ User {telegram_id} not found in Xray")
                            return True
            else:
                logger.error(f"❌ Xray config not found at {self.xray_config_path}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"❌ Error removing user {telegram_id} from Xray: {e}")
            return False
    
    async def setup_reality_inbound(self) -> bool:
        """Настраивает REALITY inbound в Xray"""
        from config import REALITY_SETTINGS
        
        try:
            logger.info("Setting up REALITY inbound...")
            
            if not self.reality_keys:
                logger.error("❌ REALITY keys not initialized")
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
            
            # Читаем существующий конфиг
            if os.path.exists(self.xray_config_path):
                with open(self.xray_config_path, 'r') as f:
                    config = json.load(f)
            else:
                logger.warning(f"⚠️ Xray config not found, creating new one")
                config = {
                    "log": {"loglevel": "warning"},
                    "inbounds": [],
                    "outbounds": [{"protocol": "freedom", "tag": "direct"}]
                }
            
            # Заменяем или добавляем inbound
            inbound_exists = False
            for i, inbound in enumerate(config.get('inbounds', [])):
                if inbound.get('port') == 443:
                    config['inbounds'][i] = inbound_config
                    inbound_exists = True
                    logger.info("✅ REALITY inbound updated")
                    break
            
            if not inbound_exists:
                if 'inbounds' not in config:
                    config['inbounds'] = []
                config['inbounds'].append(inbound_config)
                logger.info("✅ REALITY inbound created")
            
            # Сохраняем конфиг
            os.makedirs(os.path.dirname(self.xray_config_path), exist_ok=True)
            with open(self.xray_config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Перезапускаем Xray
            try:
                subprocess.run(
                    ['systemctl', 'restart', 'xray'],
                    capture_output=True,
                    timeout=15
                )
                await asyncio.sleep(2)
                logger.info("✅ Xray restarted successfully")
                return True
            except subprocess.TimeoutExpired:
                logger.error("❌ Timeout restarting Xray")
                return False
        except Exception as e:
            logger.error(f"❌ Error setting up REALITY inbound: {e}")
            return False

xray_manager = XrayManager()

async def generate_vpn_config(telegram_id: int, device_name: str) -> Optional[Dict[str, Any]]:
    """Генерирует VPN конфиг для пользователя"""
    from db import get_user, add_device, get_devices
    
    try:
        logger.info(f"Generating VPN config for user {telegram_id}, device: {device_name}")
        
        # Проверяем подписку
        user = await get_user(telegram_id)
        if not user or user['subscription_end'] < int(datetime.now().timestamp()):
            logger.warning(f"⚠️ User {telegram_id} has no active subscription")
            return None
        
        # Проверяем количество устройств
        devices = await get_devices(telegram_id)
        if len(devices) >= 5:
            logger.warning(f"⚠️ User {telegram_id} reached device limit")
            return None
        
        # Генерируем UUID и конфиг
        new_uuid = xray_manager.generate_uuid()
        vless_link = xray_manager.generate_vless_reality_link(new_uuid, telegram_id)
        
        # Добавляем пользователя в Xray
        success = await xray_manager.add_user_to_xray(new_uuid, telegram_id)
        if not success:
            logger.error(f"❌ Failed to add user {telegram_id} to Xray")
            return None
        
        # Сохраняем устройство
        config_hash = hashlib.md5(vless_link.encode()).hexdigest()
        await add_device(telegram_id, device_name, new_uuid, config_hash)
        
        logger.info(f"✅ VPN config generated for user {telegram_id}")
        
        return {
            'uuid': new_uuid,
            'vless_link': vless_link,
            'device_name': device_name
        }
    except Exception as e:
        logger.error(f"❌ Error generating VPN config for user {telegram_id}: {e}")
        return None

async def revoke_device(telegram_id: int, device_id: int) -> bool:
    """Отзывает доступ для устройства"""
    from db import get_devices, remove_device
    
    try:
        logger.info(f"Revoking device {device_id} for user {telegram_id}...")
        
        devices = await get_devices(telegram_id)
        device = next((d for d in devices if d['id'] == device_id), None)
        
        if device:
            await xray_manager.remove_user_from_xray(telegram_id)
            result = await remove_device(device_id, telegram_id)
            logger.info(f"✅ Device {device_id} revoked for user {telegram_id}")
            return result
        else:
            logger.warning(f"⚠️ Device {device_id} not found for user {telegram_id}")
            return False
    except Exception as e:
        logger.error(f"❌ Error revoking device {device_id} for user {telegram_id}: {e}")
        return False
