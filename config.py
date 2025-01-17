import os
from dotenv import load_dotenv

# Загрузка переменных из .env файла
load_dotenv()

# Чтение токена из переменной окружения
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("Переменная окружения BOT_TOKEN не установлена!")

API_KEY = os.getenv("API_KEY")

if not API_KEY:
    raise ValueError("Переменная окружения API_KEY не установлена!")