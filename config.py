import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "0").split(",")))

# Реквизиты оплаты
BANK_NAME = os.getenv("BANK_NAME", "Monobank")
CARD_NUMBER = os.getenv("CARD_NUMBER", "4441111009513544")
CARD_HOLDER = os.getenv("CARD_HOLDER", "Ivan Petrenko")

# Канал/группа для уведомлений (опционально)
NOTIFY_CHANNEL = os.getenv("NOTIFY_CHANNEL", "")

# Валюта и символ
CURRENCY = os.getenv("CURRENCY", "грн")
CURRENCY_SYMBOL = os.getenv("CURRENCY_SYMBOL", "₴")
