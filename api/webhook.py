# -*- coding: utf-8 -*-
import os
import asyncio
import json
import logging
import aiohttp
import re

from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

# Импорты оставлены, хотя ConversationHandler не используется временно
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler # Оставлен импорт, но сам хендлер отключен ниже
)

# --- Настройка логирования ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG # Оставляем DEBUG для подробных логов
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

# --- Ключи ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
OWM_API_KEY = os.environ.get('OWM_API_KEY') # Оставляем, вдруг нужен для /weather Город

# --- Клавиатура ---
reply_keyboard = [
    [KeyboardButton("Шутка 🎲"), KeyboardButton("Погода 🌦️")], # Кнопка Погода осталась, но обработчик диалога отключен
    [KeyboardButton("О боте ℹ️")]
]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

# --- Состояния (ВРЕМЕННО НЕ ИСПОЛЬЗУЮТСЯ) ---
# GET_CITY = range(1) # Закомментировано, т.к. ConversationHandler отключен

# --- Вспомогательная функция погоды (оставляем, используется /weather Город) ---
async def fetch_and_send_weather(update: Update, context: ContextTypes.DEFAULT_TYPE, city_name: str):
    logger.info(f"fetch_and_send_weather: Запрос погоды для '{city_name}'")
    if not OWM_API_KEY: logger.error("fetch: Ключ OWM не найден."); await update.message.reply_text("Ключ погоды не настроен.", reply_markup=markup); return
    # ... (остальной код fetch_and_send_weather без изменений) ...
    weather_api_url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={OWM_API_KEY}&units=metric&lang=ru"
    logger.info(f"fetch: URL: {weather_api_url}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(weather_api_url) as response:
                if response.status == 401: logger.error(f"fetch: 401 OWM для '{city_name}'."); await update.message.reply_text("Ошибка авторизации погоды.", reply_markup=markup); return
                if response.status == 404: logger.warning(f"fetch: 404 OWM для '{city_name}'."); await update.message.reply_text(f"Не найден город '{city_name}'.", reply_markup=markup); return
                response.raise_for_status(); data = await response.json(); logger.info(f"fetch: Ответ OWM: {data}")
        weather_list = data.get("weather", []); main_weather = weather_list[0].get("description", "N/A") if weather_list else "N/A"; main_data = data.get("main", {}); temp = main_data.get("temp", "N/A"); feels_like = main_data.get("feels_like", "N/A"); humidity = main_data.get("humidity", "N/A"); wind_data = data.get("wind", {}); wind_speed = wind_data.get("speed", "N/A"); city_display_name = data.get("name", city_name)
        weather_text = f"Погода в {city_display_name}:\nОписание: {main_weather.capitalize()}\nТемпература: {temp}°C\nОщущается: {feels_like}°C\nВлажность: {humidity}%\nВетер: {wind_speed} м/с"
        await update.message.reply_text(weather_text, reply_markup=markup)
    except Exception as e: logger.error(f"fetch: Ошибка для '{city_name}': {e}", exc_info=True); await update.message.reply_text("Ошибка при получении погоды.", reply_markup=markup)


# --- Обработчики вне диалога (оставляем) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Вызвана /start")
    user_name = update.effective_user.first_name or "User"
    await update.message.reply_text(f'Привет, {user_name}! Выбери:', reply_markup=markup)

async def joke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет случайную шутку"""
    joke_api_url = "https://official-joke-api.appspot.com/random_joke"
    logger.info(f"Вызвана /joke или кнопка 'Шутка'. Запрос шутки с {joke_api_url}")
    # ... (остальной код joke_command без изменений) ...
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(joke_api_url) as response:
                response.raise_for_status()
                data = await response.json()
                logger.info(f"/joke: Получен ответ от API шуток: {data}")
        setup = data.get("setup"); punchline = data.get("punchline")
        if setup and punchline: await update.message.reply_text(f"{setup}\n\n{punchline}", reply_markup=markup)
        else: logger.error(f"/joke: Не удалось извлечь setup/punchline из ответа: {data}"); await update.message.reply_text("Необычный формат шутки пришел.", reply_markup=markup)
    except aiohttp.ClientError as e: logger.error(f"/joke: Ошибка сети: {e}", exc_info=True); await update.message.reply_text("Не смог связаться с сервером шуток.", reply_markup=markup)
    except json.JSONDecodeError as e: logger.error(f"/joke: Ошибка декодирования JSON: {e}", exc_info=True); await update.message.reply_text("Сервер шуток ответил непонятное.", reply_markup=markup)
    except Exception as e: logger.error(f"/joke: Непредвиденная ошибка: {e}", exc_info=True); await update.message.reply_text("Ой, ошибка при поиске шутки.", reply_markup=markup)


async def weather_command_direct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Вызвана /weather Город")
    city = " ".join(context.args) if context.args else None
    if city: await fetch_and_send_weather(update, context, city)
    else: await update.message.reply_text("Укажите город: /weather Город", reply_markup=markup)

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
     logger.info("Вызвана О боте")
     await update.message.reply_text("Бот для шуток и погоды.", reply_markup=markup)

# --- Функции диалога погоды (ВРЕМЕННО НЕ ИСПОЛЬЗУЮТСЯ) ---
# async def weather_button_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     logger.info("Вход в диалог погоды")
#     await update.message.reply_text("Введите город:", reply_markup=ReplyKeyboardRemove())
#     return GET_CITY
#
# async def received_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     city=update.message.text
#     logger.info(f"Получен город: {city}")
#     await fetch_and_send_weather(update, context, city)
#     return ConversationHandler.END
#
# async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     logger.info("Диалог отменен")
#     await update.message.reply_text('Отменено.', reply_markup=markup)
#     return ConversationHandler.END

# --- Обработка обновления ---
async def process_one_update(update_data):
    if not TELEGRAM_TOKEN: logger.error("Токен не найден!"); return
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # --- !!! ConversationHandler ВРЕМЕННО ОТКЛЮЧЕН ДЛЯ ДИАГНОСТИКИ !!! ---
    # logger.debug("Определение ConversationHandler...") # Закомментировано
    # conv_handler_weather = ConversationHandler( # Закомментировано
    #     entry_points=[MessageHandler(filters.TEXT & filters.Regex(r'^Погода 🌦️$'), weather_button_entry)], # Закомментировано
    #     states={GET_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_city)]}, # Закомментировано
    #     fallbacks=[CommandHandler('cancel', cancel_conversation)] # Закомментировано
    # ) # Закомментировано
    # logger.debug("Добавление ConversationHandler...") # Закомментировано
    # application.add_handler(conv_handler_weather) # Закомментировано
    # --- !!! КОНЕЦ ОТКЛЮЧЕНИЯ !!! ---

    # --- Добавляем остальные обработчики ---
    logger.debug("Добавление CommandHandler(start)...")
    application.add_handler(CommandHandler("start", start))
    logger.debug("Добавление CommandHandler(joke)...")
    application.add_handler(CommandHandler("joke", joke_command))
    logger.debug("Добавление CommandHandler(weather)...")
    application.add_handler(CommandHandler("weather", weather_command_direct))
    logger.debug("Добавление MessageHandler(Шутка)...")
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^Шутка 🎲$'), joke_command))
    logger.debug("Добавление MessageHandler(О боте)...")
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^О боте ℹ️$'), about_command))

    # --- Обработчик кнопки "Погода" теперь не будет работать, т.к. он вел в отключенный ConversationHandler ---
    # --- Отдельный /cancel тоже временно не нужен ---
    # logger.debug("Добавление CommandHandler(cancel)...") # Закомментировано
    # application.add_handler(CommandHandler('cancel', cancel_conversation)) # Закомментировано

    logger.info("Обработчики добавлены (БЕЗ ConversationHandler).")
    try:
        logger.debug(f"Инит приложения для {update_data.get('update_id')}")
        await application.initialize()
        update = Update.de_json(update_data, application.bot)
        # Логгируем входящее сообщение
        if update.message: logger.info(f"Получено сообщение: type={update.message.chat.type}, text='{update.message.text}'")
        elif update.callback_query: logger.info(f"Получен callback_query: data='{update.callback_query.data}'")
        else: logger.info(f"Получен другой тип обновления: {update}")
        logger.debug(f"Запуск process_update для {update.update_id}")
        await application.process_update(update) # <- Основная обработка
        logger.debug(f"Завершение shutdown для {update.update_id}")
        await application.shutdown()
    except Exception as e: logger.error(f"Критическая ошибка {update_data.get('update_id', 'N/A')}: {e}", exc_info=True); await application.shutdown() if application.initialized else None

# --- Точка входа Vercel (без изменений) ---
class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): logger.info("%s - %s" % (self.address_string(), format % args))
    def do_POST(self): logger.info("!!! Вход в do_POST !!!"); # ... (остальной код do_POST без изменений) ...
        if not TELEGRAM_TOKEN: logger.error("POST: Токен не найден"); self.send_response(500); self.end_headers(); self.wfile.write(b"Token error"); return
        try:
            content_len = int(self.headers.get('Content-Length', 0)); body_bytes = self.rfile.read(content_len)
            if content_len == 0: logger.warning("POST: Пустое тело"); self.send_response(400); self.end_headers(); self.wfile.write(b"Empty body"); return
            body_json = json.loads(body_bytes.decode('utf-8')); logger.info("POST: JSON получен")
            asyncio.run(process_one_update(body_json))
            self.send_response(200); self.send_header('Content-type', 'text/plain'); self.end_headers(); self.wfile.write(b"OK"); logger.info("POST: Ответ 200 OK")
        except json.JSONDecodeError: logger.error("POST: Ошибка JSON", exc_info=True); self.send_response(400); self.end_headers(); self.wfile.write(b"Invalid JSON"); return
        except Exception as e: logger.error(f"POST: Ошибка в do_POST: {e}", exc_info=True); self.send_response(500); self.end_headers(); self.wfile.write(b"Internal Error"); return
    def do_GET(self): logger.info("GET /api/webhook"); self.send_response(200); self.send_header('Content-type', 'text/plain'); self.end_headers(); self.wfile.write(b"Bot OK"); return