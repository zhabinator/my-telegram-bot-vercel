# -*- coding: utf-8 -*-
import os
import asyncio
import json
import logging
import aiohttp
import re

from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

# Настройка логирования (оставляем DEBUG)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

# --- Ключи ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
OWM_API_KEY = os.environ.get('OWM_API_KEY')

# --- Клавиатура ---
reply_keyboard = [
    [KeyboardButton("Шутка 🎲"), KeyboardButton("Погода 🌦️")],
    [KeyboardButton("О боте ℹ️")]
]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

# --- Состояния ---
GET_CITY = range(1)

# --- Вспомогательная функция погоды ---
async def fetch_and_send_weather(update: Update, context: ContextTypes.DEFAULT_TYPE, city_name: str):
    # ... (код fetch_and_send_weather как в предыдущем ответе) ...
    logger.info(f"fetch_and_send_weather: Запрос погоды для '{city_name}'")
    if not OWM_API_KEY: logger.error("fetch: Ключ OWM не найден."); await update.message.reply_text("Ключ погоды не настроен.", reply_markup=markup); return
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


# --- Обработчики вне диалога ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): logger.info("Вызвана /start"); user_name = update.effective_user.first_name or "User"; await update.message.reply_text(f'Привет, {user_name}! Выбери:', reply_markup=markup)
async def joke_command(update: Update, context: ContextTypes.DEFAULT_TYPE): logger.info("Вызвана /joke или кнопка 'Шутка'"); joke_api_url = "https://official-joke-api.appspot.com/random_joke"; try: async with aiohttp.ClientSession() as s, s.get(joke_api_url) as r: r.raise_for_status(); data=await r.json(); logger.info(f"/joke: Ответ API: {data}"); setup=data.get("setup"); p=data.get("punchline"); await update.message.reply_text(f"{setup}\n\n{p}" if setup and p else "Шутка не пришла :(", reply_markup=markup) except Exception as e: logger.error(f"/joke Ошибка: {e}", exc_info=True); await update.message.reply_text("Не вышло пошутить.", reply_markup=markup)
async def weather_command_direct(update: Update, context: ContextTypes.DEFAULT_TYPE): logger.info("Вызвана /weather Город"); city = " ".join(context.args) if context.args else None; await fetch_and_send_weather(update, context, city) if city else await update.message.reply_text("Укажите город: /weather Город", reply_markup=markup)
async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE): logger.info("Вызвана О боте"); await update.message.reply_text("Бот для шуток и погоды.", reply_markup=markup)

# --- Функции диалога погоды ---
async def weather_button_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает диалог погоды после нажатия кнопки."""
    logger.info("Вход в диалог погоды (weather_button_entry)")
    await update.message.reply_text(
        "Хорошо! Введите название города, для которого хотите узнать погоду:",
        reply_markup=ReplyKeyboardRemove() # Убираем основную клавиатуру на время ввода
    )
    logger.info("Сообщение 'Введите город' отправлено. Возвращаем состояние GET_CITY.") # <-- Новый лог
    return GET_CITY # Переходим в состояние ожидания города

async def received_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает введенное название города."""
    # --- !!! НОВЫЙ ЛОГ В НАЧАЛЕ ФУНКЦИИ !!! ---
    logger.info("Вход в функцию received_city.")
    # -----------------------------------------
    city_name = update.message.text
    user_id = update.effective_user.id
    logger.info(f"Пользователь {user_id} ввел город: '{city_name}'")

    # --- !!! НОВЫЙ ЛОГ ПЕРЕД ВЫЗОВОМ ПОГОДЫ !!! ---
    logger.info(f"Вызов fetch_and_send_weather для города '{city_name}'.")
    # -------------------------------------------
    # Вызываем общую функцию для получения погоды
    await fetch_and_send_weather(update, context, city_name)

    # Завершаем диалог
    logger.info(f"Диалог погоды для пользователя {user_id} завершен.")
    return ConversationHandler.END # Выход из диалога

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет текущий диалог."""
    logger.info("Диалог отменен")
    await update.message.reply_text('Отменено.', reply_markup=markup)
    return ConversationHandler.END
# --- Конец функций для ConversationHandler ---


# --- Обработка обновления ---
async def process_one_update(update_data):
    # ... (код до регистрации обработчиков без изменений) ...
    if not TELEGRAM_TOKEN: logger.error("Токен не найден!"); return
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    conv_handler_weather = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex(r'^Погода 🌦️$'), weather_button_entry)],
        states={
            GET_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_city)] # <-- Этот обработчик должен сработать
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)]
    )
    application.add_handler(conv_handler_weather)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("joke", joke_command))
    application.add_handler(CommandHandler("weather", weather_command_direct))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^Шутка 🎲$'), joke_command))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^О боте ℹ️$'), about_command))
    application.add_handler(CommandHandler('cancel', cancel_conversation))
    logger.info("Обработчики добавлены.")

    try:
        # ... (остальной код try/except блока без изменений) ...
        logger.debug(f"Инит приложения для {update_data.get('update_id')}")
        await application.initialize()
        update = Update.de_json(update_data, application.bot)
        if update.message: logger.info(f"Получено сообщение: type={update.message.chat.type}, text='{update.message.text}'")
        elif update.callback_query: logger.info(f"Получен callback_query: data='{update.callback_query.data}'")
        else: logger.info(f"Получен другой тип обновления: {update}")
        logger.debug(f"Запуск process_update для {update.update_id}")
        await application.process_update(update)
        logger.debug(f"Завершение shutdown для {update.update_id}")
        await application.shutdown()
    except Exception as e: logger.error(f"Критическая ошибка {update_data.get('update_id', 'N/A')}: {e}", exc_info=True); await application.shutdown() if application.initialized else None


# --- Точка входа Vercel ---
class handler(BaseHTTPRequestHandler):
    # ... (log_message, do_POST, do_GET без изменений) ...
    def log_message(self, format, *args): logger.info("%s - %s" % (self.address_string(), format % args))
    def do_POST(self): logger.info("!!! Вход в do_POST !!!"); # ... (далее как раньше) ...
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