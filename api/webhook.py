# -*- coding: utf-8 -*-
import os
import asyncio
import json
import logging
from typing import List

# --- ИСПРАВЛЕННЫЙ ИМПОРТ ---
from vercel_kv import KV # Импортируем КЛАСС
# --------------------------

from http.server import BaseHTTPRequestHandler

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# --- Настройка логирования ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO # Возвращаем INFO
)
logger = logging.getLogger(__name__)
logging.getLogger("vercel_kv").setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

# --- Ключ Telegram ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
if not TELEGRAM_TOKEN:
    logger.critical("Переменная окружения TELEGRAM_TOKEN не установлена!")

# --- СОЗДАЕМ ЭКЗЕМПЛЯР KV КЛИЕНТА ---
kv_client = KV() # Создаем объект один раз
# ------------------------------------

# --- Список поздравлений ---
congratulations_list: List[str] = [
    "Будть всегда very sugar🎉", "Ты - ловушка для мужского Вау! 💖", "Главная статья в кодексе красоты 🥳",
    "Ты делаешь аппетит приятнее ✨", "Ароматного дня, миледи🥰", "Рядом с вами не хочется моргать🥰",
    "Если красота спасет мир, то вся надежда только на тебя!🥰", "Целуем тот день, когда ты родилась!💖",
    "Море удачи и дачи у моря! 💖",
]

# --- Список URL картинок ---
image_urls: List[str] = [
    "https://i.imgur.com/P14dISY.jpeg",
    "https://i.imgur.com/SrFv5sw.jpeg",
    "https://i.imgur.com/UjL4C4Q.jpeg",
    "https://i.imgur.com/exIooZ0.jpeg",
    "https://i.imgur.com/Hqe3MOI.jpeg",
    "https://i.imgur.com/xEsRHUU.jpeg",
]
if not image_urls: logger.warning("Список image_urls пуст!")

# --- ID Аудиофайла ---
HAPPY_BIRTHDAY_AUDIO_ID = "CQACAgIAAxkBAAEd2Z9n99j8nLv08edj8YC2UjLcN_AlNQAC1nEAAm2gwEuxk0AF1ieRlDYE"

# --- Клавиатура ---
reply_keyboard = [
    [KeyboardButton("Полить сердечко сиропом ❤️"), KeyboardButton("Сделай красиво ✨")],
    [KeyboardButton("Хеппи бездей 🎂")]
]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)

# --- Вспомогательная функция с ИСПРАВЛЕННЫМ использованием KV ---
async def get_next_item(user_id: int, list_key: str, item_list: List[str]) -> str:
    if not item_list: logger.warning(f"Список для ключа '{list_key}' пуст."); return "Список пуст."

    kv_key = f"next_idx:{user_id}:{list_key}"
    logger.debug(f"KV ключ: {kv_key}")
    current_index: int = 0
    item_to_return: str = item_list[0]

    try:
        logger.debug(f"KV Чтение: {kv_key}...")
        # --- ИСПОЛЬЗУЕМ ЭКЗЕМПЛЯР kv_client ---
        stored_value = await kv_client.get(kv_key)
        # ------------------------------------
        logger.debug(f"KV Прочитано: {kv_key} = {stored_value} (тип: {type(stored_value)})")

        if isinstance(stored_value, int): current_index = stored_value
        elif isinstance(stored_value, str) and stored_value.isdigit(): current_index = int(stored_value)
        else: logger.info(f"KV Индекс не найден/не число для {kv_key}, начинаем с 0."); current_index = 0

        if not (0 <= current_index < len(item_list)):
            logger.warning(f"KV Индекс {current_index} вне диапазона для {kv_key}. Сброс на 0.")
            current_index = 0

        item_to_return = item_list[current_index]
        logger.info(f"KV Выбран индекс {current_index} для {kv_key}.")

    except Exception as e:
        logger.error(f"KV Ошибка чтения {kv_key}: {e}", exc_info=True)
        current_index = 0
        item_to_return = item_list[0]

    next_index = (current_index + 1) % len(item_list)
    try:
        logger.debug(f"KV Запись: {kv_key} = {next_index}...")
        # --- ИСПОЛЬЗУЕМ ЭКЗЕМПЛЯР kv_client ---
        await kv_client.set(kv_key, next_index)
        # ------------------------------------
        logger.info(f"KV Сохранен след. индекс {next_index} для {kv_key}")
    except Exception as e:
        logger.error(f"KV Ошибка записи {kv_key}: {e}", exc_info=True)

    return item_to_return

# --- Обработчики (без изменений) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): # ... (код start) ...
async def syrup_heart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): # ... (код syrup_heart_handler) ...
async def beauty_image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): # ... (код beauty_image_handler) ...
async def happy_birthday_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): # ... (код happy_birthday_handler) ...

# --- Обработка обновления (без изменений) ---
async def process_one_update(update_data): # ... (код process_one_update) ...

# --- Точка входа Vercel (без изменений) ---
class handler(BaseHTTPRequestHandler): # ... (код handler) ...
    def do_POST(self): # ... (код do_POST) ...
    def do_GET(self): # ... (код do_GET) ...