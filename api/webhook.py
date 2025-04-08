# -*- coding: utf-8 -*-
import os
import asyncio
import json
import logging
import aiohttp
import re

from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

# --- !!! НУЖНЫ НОВЫЕ ИМПОРТЫ ДЛЯ ConversationHandler !!! ---
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler # <-- Главный импорт для диалогов
)
# -----------------------------------------------------------

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Ключи ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
OWM_API_KEY = os.environ.get('OWM_API_KEY')

# --- Клавиатура ---
reply_keyboard = [
    [KeyboardButton("Шутка 🎲"), KeyboardButton("Погода 🌦️")],
    [KeyboardButton("О боте ℹ️")]
]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

# --- Определяем состояния для ConversationHandler ---
GET_CITY = range(1) # Одно состояние для ожидания города
# ----------------------------------------------------


# --- Вспомогательная функция для получения и отправки погоды ---
async def fetch_and_send_weather(update: Update, context: ContextTypes.DEFAULT_TYPE, city_name: str):
    """Получает погоду для city_name и отправляет сообщение."""
    logger.info(f"fetch_and_send_weather: Запрос погоды для '{city_name}'")
    if not OWM_API_KEY:
        logger.error("fetch_and_send_weather: Ключ OWM_API_KEY не найден.")
        await update.message.reply_text("Ключ для сервиса погоды не настроен.", reply_markup=markup)
        return

    weather_api_url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={OWM_API_KEY}&units=metric&lang=ru"
    logger.info(f"fetch_and_send_weather: URL запроса: {weather_api_url}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(weather_api_url) as response:
                if response.status == 401:
                     logger.error(f"fetch_and_send_weather: Ошибка 401 от OWM API для '{city_name}'.")
                     await update.message.reply_text("Ошибка авторизации на сервере погоды.", reply_markup=markup)
                     return
                if response.status == 404:
                    logger.warning(f"fetch_and_send_weather: Город '{city_name}' не найден OWM API (404).")
                    await update.message.reply_text(f"Не могу найти город '{city_name}'.", reply_markup=markup)
                    return
                response.raise_for_status()
                data = await response.json()
                logger.info(f"fetch_and_send_weather: Получен ответ от OWM API: {data}")

        weather_list = data.get("weather", [])
        main_weather = weather_list[0].get("description", "Нет данных") if weather_list else "Нет данных"
        main_data = data.get("main", {})
        temp = main_data.get("temp", "N/A")
        feels_like = main_data.get("feels_like", "N/A")
        humidity = main_data.get("humidity", "N/A")
        wind_data = data.get("wind", {})
        wind_speed = wind_data.get("speed", "N/A")
        city_display_name = data.get("name", city_name)

        weather_text = (
            f"Погода в городе {city_display_name}:\n"
            f"Описание: {main_weather.capitalize()}\n"
            f"Температура: {temp}°C\n"
            f"Ощущается как: {feels_like}°C\n"
            f"Влажность: {humidity}%\n"
            f"Скорость ветра: {wind_speed} м/с"
        )
        await update.message.reply_text(weather_text, reply_markup=markup) # Возвращаем основную клавиатуру

    except aiohttp.ClientError as e:
        logger.error(f"fetch_and_send_weather: Ошибка сети для '{city_name}': {e}", exc_info=True)
        await update.message.reply_text("Не смог связаться с сервером погоды.", reply_markup=markup)
    except json.JSONDecodeError as e:
         logger.error(f"fetch_and_send_weather: Ошибка JSON для '{city_name}': {e}", exc_info=True)
         await update.message.reply_text("Сервер погоды ответил что-то непонятное.", reply_markup=markup)
    except Exception as e:
        logger.error(f"fetch_and_send_weather: Непредвиденная ошибка для '{city_name}': {e}", exc_info=True)
        await update.message.reply_text("Ой, что-то пошло не так с погодой.", reply_markup=markup)
# --- Конец вспомогательной функции ---


# --- Обработчики команд и сообщений (вне диалога) ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет приветствие и клавиатуру."""
    user_name = update.effective_user.first_name or "Пользователь"
    await update.message.reply_text(
        f'Привет, {user_name}! Выбери действие:',
        reply_markup=markup
    )

async def joke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет шутку."""
    # ... (код функции joke_command как в предыдущей версии) ...
    joke_api_url = "https://official-joke-api.appspot.com/random_joke"
    logger.info(f"Вызвана /joke или кнопка 'Шутка'. Запрос шутки с {joke_api_url}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(joke_api_url) as response:
                response.raise_for_status()
                data = await response.json()
                logger.info(f"/joke: Получен ответ от API шуток: {data}")
        setup = data.get("setup"); punchline = data.get("punchline")
        if setup and punchline: await update.message.reply_text(f"{setup}\n\n{punchline}", reply_markup=markup)
        else: logger.error(f"/joke: Не удалось извлечь setup/punchline: {data}"); await update.message.reply_text("Необычный формат шутки.", reply_markup=markup)
    except Exception as e: logger.error(f"/joke: Ошибка: {e}", exc_info=True); await update.message.reply_text("Не удалось получить шутку.", reply_markup=markup)


async def weather_command_direct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает прямую команду /weather Город."""
    logger.info("Вызвана прямая команда /weather Город")
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите город: /weather НазваниеГорода", reply_markup=markup)
        return
    city_name = " ".join(context.args)
    # Вызываем общую функцию для получения погоды
    await fetch_and_send_weather(update, context, city_name)

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
     """Отправляет информацию о боте."""
     logger.info("Нажата кнопка 'О боте'")
     await update.message.reply_text("Я бот для шуток и погоды!", reply_markup=markup)


# --- Функции для ConversationHandler (Погода по кнопке) ---

async def weather_button_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает диалог погоды после нажатия кнопки."""
    logger.info("Нажата кнопка 'Погода', вход в диалог.")
    await update.message.reply_text(
        "Хорошо! Введите название города, для которого хотите узнать погоду:",
        reply_markup=ReplyKeyboardRemove() # Убираем основную клавиатуру на время ввода
    )
    return GET_CITY # Переходим в состояние ожидания города

async def received_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает введенное название города."""
    city_name = update.message.text
    user_id = update.effective_user.id
    logger.info(f"Пользователь {user_id} ввел город: '{city_name}'")

    # Вызываем общую функцию для получения погоды
    await fetch_and_send_weather(update, context, city_name)

    # Завершаем диалог
    logger.info(f"Диалог погоды для пользователя {user_id} завершен.")
    return ConversationHandler.END # Выход из диалога

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет текущий диалог."""
    user_id = update.effective_user.id
    logger.info(f"Пользователь {user_id} отменил диалог.")
    await update.message.reply_text(
        'Действие отменено.',
        reply_markup=markup # Возвращаем основную клавиатуру
    )
    return ConversationHandler.END
# --- Конец функций для ConversationHandler ---


# --- Функция обработки ОДНОГО обновления ---
async def process_one_update(update_data):
    if not TELEGRAM_TOKEN: logger.error("Токен не найден!"); return

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # --- !!! СОЗДАЕМ ConversationHandler ДЛЯ ПОГОДЫ ПО КНОПКЕ !!! ---
    conv_handler_weather = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex(r'^Погода 🌦️$'), weather_button_entry)],
        states={
            GET_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_city)]
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)]
    )
    # -------------------------------------------------------------

    # --- !!! РЕГИСТРАЦИЯ ВСЕХ ОБРАБОТЧИКОВ !!! ---
    application.add_handler(conv_handler_weather) # Добавляем обработчик диалога
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("joke", joke_command))
    application.add_handler(CommandHandler("weather", weather_command_direct)) # Обработчик для /weather Город
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^Шутка 🎲$'), joke_command))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^О боте ℹ️$'), about_command))
    # Обработчик для /cancel (если он не указан в fallbacks, он не сработает внутри диалога)
    application.add_handler(CommandHandler('cancel', cancel_conversation))
    # ------------------------------------------

    logger.info("process_one_update: Обработчики добавлены (включая ConversationHandler).")

    try:
        await application.initialize()
        update = Update.de_json(update_data, application.bot)
        await application.process_update(update)
        await application.shutdown()
    except Exception as e:
        logger.error(f"Критическая ошибка при обработке {update_data.get('update_id', 'N/A')}: {e}", exc_info=True)
        if application.initialized: await application.shutdown()

# --- Точка входа для Vercel (остается без изменений) ---
class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): logger.info("%s - %s" % (self.address_string(), format % args))
    def do_POST(self):
        logger.info("!!! Вход в do_POST !!!")
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