# -*- coding: utf-8 -*-
import os
import asyncio
import json
import logging
import aiohttp
import re

from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

# Все необходимые импорты
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler # Используем для погоды
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
OWM_API_KEY = os.environ.get('OWM_API_KEY') # Нужен для погоды

# --- !!! ИЗМЕНЕНИЕ: Добавлена кнопка Цитата !!! ---
reply_keyboard = [
    [KeyboardButton("Шутка 🎲"), KeyboardButton("Погода 🌦️"), KeyboardButton("Цитата 📜")], # Добавлена кнопка
    [KeyboardButton("О боте ℹ️")]
]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
# --- КОНЕЦ ИЗМЕНЕНИЯ ---

# --- Состояния для диалога погоды ---
GET_CITY = range(1)

# --- Вспомогательная функция погоды (без изменений) ---
async def fetch_and_send_weather(update: Update, context: ContextTypes.DEFAULT_TYPE, city_name: str):
    # ... (код fetch_and_send_weather без изменений) ...
    logger.info(f"fetch_and_send_weather: Запрос погоды для '{city_name}'")
    if not OWM_API_KEY: logger.error("fetch: Ключ OWM не найден."); await update.message.reply_text("Ключ погоды не настроен.", reply_markup=markup); return
    weather_api_url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={OWM_API_KEY}&units=metric&lang=ru"; logger.info(f"fetch: URL: {weather_api_url}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(weather_api_url) as response:
                if response.status == 401: logger.error(f"fetch: 401 OWM для '{city_name}'."); await update.message.reply_text("Ошибка авторизации погоды.", reply_markup=markup); return
                if response.status == 404: logger.warning(f"fetch: 404 OWM для '{city_name}'."); await update.message.reply_text(f"Не найден город '{city_name}'.", reply_markup=markup); return
                response.raise_for_status(); data = await response.json(); logger.info(f"fetch: Ответ OWM: {data}")
        weather_list = data.get("weather", []); main_weather = weather_list[0].get("description", "N/A") if weather_list else "N/A"; main_data = data.get("main", {}); temp = main_data.get("temp", "N/A"); feels_like = main_data.get("feels_like", "N/A"); humidity = main_data.get("humidity", "N/A"); wind_data = data.get("wind", {}); wind_speed = wind_data.get("speed", "N/A"); city_display_name = data.get("name", city_name)
        weather_text = f"Погода в {city_display_name}:\nОписание: {main_weather.capitalize()}\nТемпература: {temp}°C\nОщущается: {feels_like}°C\nВлажность: {humidity}%\nВетер: {wind_speed} м/с"; await update.message.reply_text(weather_text, reply_markup=markup)
    except Exception as e: logger.error(f"fetch: Ошибка для '{city_name}': {e}", exc_info=True); await update.message.reply_text("Ошибка при получении погоды.", reply_markup=markup)


# --- Обработчики вне диалога ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (код start без изменений) ...
    logger.info("Вызвана /start"); user_name = update.effective_user.first_name or "User"; await update.message.reply_text(f'Привет, {user_name}! Выбери:', reply_markup=markup)

async def joke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (код joke_command без изменений) ...
    joke_api_url = "https://official-joke-api.appspot.com/random_joke"; logger.info(f"Вызвана /joke или кнопка 'Шутка'. Запрос шутки с {joke_api_url}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(joke_api_url) as response: response.raise_for_status(); data = await response.json(); logger.info(f"/joke: Получен ответ от API шуток: {data}")
        setup = data.get("setup"); punchline = data.get("punchline")
        if setup and punchline: await update.message.reply_text(f"{setup}\n\n{punchline}", reply_markup=markup)
        else: logger.error(f"/joke: Не удалось извлечь setup/punchline: {data}"); await update.message.reply_text("Необычный формат шутки.", reply_markup=markup)
    except aiohttp.ClientError as e: logger.error(f"/joke: Ошибка сети: {e}", exc_info=True); await update.message.reply_text("Не связаться с сервером шуток.", reply_markup=markup)
    except json.JSONDecodeError as e: logger.error(f"/joke: Ошибка JSON: {e}", exc_info=True); await update.message.reply_text("Сервер шуток ответил непонятное.", reply_markup=markup)
    except Exception as e: logger.error(f"/joke: Непредвиденная ошибка: {e}", exc_info=True); await update.message.reply_text("Ошибка при поиске шутки.", reply_markup=markup)

# --- !!! НОВАЯ ФУНКЦИЯ для ЦИТАТ !!! ---
async def quote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет случайную известную цитату."""
    # Отступ 4 пробела
    quote_api_url = "https://api.quotable.io/random" # API для получения случайной цитаты
    logger.info(f"Вызвана /quote или кнопка 'Цитата'. Запрос цитаты с {quote_api_url}")
    try:
        # Отступ 8 пробелов
        async with aiohttp.ClientSession() as session:
            # Отступ 12 пробелов
            async with session.get(quote_api_url) as response:
                # Отступ 16 пробелов
                response.raise_for_status() # Проверяем на ошибки HTTP (4xx, 5xx)
                data = await response.json()
                logger.info(f"/quote: Получен ответ от API цитат: {data}")

        # Отступ 8 пробелов
        content = data.get("content") # Текст цитаты
        author = data.get("author")   # Автор цитаты

        if content and author:
            # Отступ 12 пробелов
            quote_text = f'"{content}"\n\n— {author}' # Форматируем красиво
            await update.message.reply_text(quote_text, reply_markup=markup)
        else:
            # Отступ 12 пробелов
            logger.error(f"/quote: Не удалось извлечь content/author из ответа: {data}")
            await update.message.reply_text("Необычный формат цитаты пришел. Попробуй еще раз!", reply_markup=markup)

    # Отступ 4 пробела
    except aiohttp.ClientError as e:
        # Отступ 8 пробелов
        logger.error(f"/quote: Ошибка сети при запросе цитаты: {e}", exc_info=True)
        await update.message.reply_text("Не смог связаться с сервером цитат. Попробуй позже.", reply_markup=markup)
    # Отступ 4 пробела
    except json.JSONDecodeError as e:
        # Отступ 8 пробелов
        logger.error(f"/quote: Ошибка декодирования JSON от API цитат: {e}", exc_info=True)
        await update.message.reply_text("Сервер цитат ответил что-то непонятное. Попробуй позже.", reply_markup=markup)
    # Отступ 4 пробела
    except Exception as e:
        # Отступ 8 пробелов
        logger.error(f"/quote: Непредвиденная ошибка при получении цитаты: {e}", exc_info=True)
        await update.message.reply_text("Ой, что-то пошло не так при поиске цитаты. Попробуй позже.", reply_markup=markup)
# --- КОНЕЦ НОВОЙ ФУНКЦИИ ---

async def weather_command_direct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (код weather_command_direct без изменений) ...
    logger.info("Вызвана /weather Город"); city = " ".join(context.args) if context.args else None
    if city: await fetch_and_send_weather(update, context, city)
    else: await update.message.reply_text("Укажите город: /weather Город", reply_markup=markup)

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (код about_command без изменений) ...
     logger.info("Вызвана О боте"); await update.message.reply_text("Бот для шуток и погоды.", reply_markup=markup)

# --- Функции диалога погоды (без изменений) ---
async def weather_button_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # ... (код weather_button_entry без изменений) ...
    logger.info("Вход в диалог погоды через кнопку"); await update.message.reply_text("Введите название города:", reply_markup=ReplyKeyboardRemove()); return GET_CITY

async def received_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # ... (код received_city без изменений) ...
    city=update.message.text; logger.info(f"Диалог: получен город: {city}"); await fetch_and_send_weather(update, context, city); logger.info("Диалог погоды завершен."); return ConversationHandler.END

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # ... (код cancel_conversation без изменений) ...
    logger.info("Диалог (вероятно, погоды) отменен командой /cancel"); await update.message.reply_text('Действие отменено.', reply_markup=markup); return ConversationHandler.END

# --- Обработка обновления ---
async def process_one_update(update_data):
    # Отступ 4 пробела
    if not TELEGRAM_TOKEN: logger.error("Токен не найден!"); return
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # --- Добавляем ConversationHandler для погоды ПЕРВЫМ ---
    logger.debug("Определение ConversationHandler для погоды...")
    conv_handler_weather = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex(r'^Погода 🌦️$'), weather_button_entry)],
        states={GET_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_city)]},
        fallbacks=[CommandHandler('cancel', cancel_conversation)]
    )
    logger.debug("Добавление ConversationHandler...")
    application.add_handler(conv_handler_weather)

    # --- Добавляем остальные обработчики ---
    logger.debug("Добавление CommandHandler(start)...")
    application.add_handler(CommandHandler("start", start))
    logger.debug("Добавление CommandHandler(joke)...")
    application.add_handler(CommandHandler("joke", joke_command))
    # --- !!! ИЗМЕНЕНИЕ: Добавлен обработчик команды /quote !!! ---
    logger.debug("Добавление CommandHandler(quote)...")
    application.add_handler(CommandHandler("quote", quote_command))
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---
    logger.debug("Добавление CommandHandler(weather)...")
    application.add_handler(CommandHandler("weather", weather_command_direct)) # Для прямого вызова /weather Город

    logger.debug("Добавление MessageHandler(Шутка)...")
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^Шутка 🎲$'), joke_command))
    # --- !!! ИЗМЕНЕНИЕ: Добавлен обработчик кнопки Цитата !!! ---
    logger.debug("Добавление MessageHandler(Цитата)...")
    # --- ВАЖНО: Проверьте по логам Vercel, если кнопка не сработает ---
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^Цитата 📜$'), quote_command))
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---
    logger.debug("Добавление MessageHandler(О боте)...")
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^О боте ℹ️$'), about_command))

    logger.info("Все обработчики добавлены.")
    # ... (остальной код try...except блока без изменений) ...
    try:
        logger.debug(f"Инит приложения для {update_data.get('update_id')}"); await application.initialize(); update = Update.de_json(update_data, application.bot)
        if update.message: logger.info(f"Получено сообщение: type={update.message.chat.type}, text='{update.message.text}'")
        elif update.callback_query: logger.info(f"Получен callback_query: data='{update.callback_query.data}'")
        else: logger.info(f"Получен другой тип обновления: {update}")
        logger.debug(f"Запуск process_update для {update.update_id}"); await application.process_update(update)
        logger.debug(f"Завершение shutdown для {update.update_id}"); await application.shutdown()
    except Exception as e: logger.error(f"Критическая ошибка {update_data.get('update_id', 'N/A')}: {e}", exc_info=True); await application.shutdown() if application.initialized else None


# --- Точка входа Vercel (без изменений) ---
class handler(BaseHTTPRequestHandler): # Начало класса, нет отступа
    # ... (код log_message, do_POST, do_GET без изменений) ...
    def log_message(self, format, *args): logger.info("%s - %s" % (self.address_string(), format % args))
    def do_POST(self): logger.info("!!! Вход в do_POST !!!");
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