# VPN Telegram Bot

Telegram бот для выдачи VPN доступа (протокол VLESS) с интеграцией крипто-платежей через CryptoBot.

## Функционал

- ✅ Автоматическая регистрация пользователей
- ✅ Продажа VPN подписки через криптовалюту (USDT)
- ✅ Реферальная система с бонусами
- ✅ Генерация VLESS конфигов
- ✅ Управление устройствами (до 5 на пользователя)
- ✅ Админ-панель с статистикой и рассылками

## Установка

### 1. Установка Python и зависимостей

```bash
# Установка Python 3.10+
sudo apt update
sudo apt install python3.10 python3.10-venv python3-pip -y

# Создание виртуального окружения
python3.10 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
