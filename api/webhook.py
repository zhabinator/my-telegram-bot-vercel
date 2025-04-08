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
    ConversationHandler # Теперь используем
)

# --- Настройка логирования ---
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

# --- Состояния для диалога погоды ---
GET_CITY = range(1)

# --- Вспомогательная функция погоды ---
async def fetch_and_send_weather(update: Update, context: ContextTypes.DEFAULT_TYPE, city_name: str):
    # Отступ 4 пробела
    logger.info(f"fetch_and_send_weather: Запрос погоды для '{city_name}'")
    if not OWM_API_KEY:
        # Отступ 8 пробелов
        logger.error("fetch: Ключ OWM не найден.")
        await update.message.reply_text("Ключ погоды не настроен.", reply_markup=markup)
        return
    # Отступ 4 пробела
    weather_api_url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={OWM_API_KEY}&units=metric&lang=ru"
    logger.info(f"fetch: URL: {weather_api_url}")
    try:
        # Отступ 8 пробелов
        async with aiohttp.ClientSession() as session:
            # Отступ 12 пробелов
            async with session.get(weather_api_url) as response:
                # Отступ 16 пробелов
                if response.status == 401:
                    # Отступ 20 пробелов
                    logger.error(f"fetch: 401 OWM для '{city_name}'.")
                    await update.message.reply_text("Ошибка авторизации погоды.", reply_markup=markup)
                    return
                # Отступ 16 пробелов
                if response.status == 404:
                    # Отступ 20 пробелов
                    logger.warning(f"fetch: 404 OWM для '{city_name}'.")
                    await update.message.reply_text(f"Не найден город '{city_name}'.", reply_markup=markup)
                    return
                # Отступ 16 пробелов
                response.raise_for_status()
                data = await response.json()
                logger.info(f"fetch: Ответ OWM: {data}")
        # Отступ 8 пробелов
        weather_list = data.get("weather", [])
        main_weather = weather_list[0].get("description", "N/A") if weather_list else "N/A"
        main_data = data.get("main", {})
        temp = main_data.get("temp", "N/A")
        feels_like = main_data.get("feels_like", "N/A")
        humidity = main_data.get("humidity", "N/A")
        wind_data = data.get("wind", {})
        wind_speed = wind_data.get("speed", "N/A")
        city_display_name = data.get("name", city_name)
        weather_text = f"Погода в {city_display_name}:\nОписание: {main_weather.capitalize()}\nТемпература: {temp}°C\nОщущается: {feels_like}°C\nВлажность: {humidity}%\nВетер: {wind_speed} м/с"
        await update.message.reply_text(weather_text, reply_markup=markup)
    # Отступ 4 пробела
    except Exception as e:
        # Отступ 8 пробелов
        logger.error(f"fetch: Ошибка для '{city_name}': {e}", exc_info=True)
        await update.message.reply_text("Ошибка при получении погоды.", reply_markup=markup)


# --- Обработчики вне диалога ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Отступ 4 пробела
    logger.info("Вызвана /start")
    user_name = update.effective_user.first_name or "User"
    await update.message.reply_text(f'Привет, {user_name}! Выбери:', reply_markup=markup)

async def joke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет случайную шутку"""
    # Отступ 4 пробела
    joke_api_url = "https://official-joke-api.appspot.com/random_joke"
    logger.info(f"Вызвана /joke или кнопка 'Шутка'. Запрос шутки с {joke_api_url}")
    try:
        # Отступ 8 пробелов
        async with aiohttp.ClientSession() as session:
            # Отступ 12 пробелов
            async with session.get(joke_api_url) as response:
                # Отступ 16 пробелов
                response.raise_for_status()
                data = await response.json()
                logger.info(f"/joke: Получен ответ от API шуток: {data}")
        # Отступ 8 пробелов
        setup = data.get("setup")
        punchline = data.get("punchline")
        if setup and punchline:
            # Отступ 12 пробелов
            await update.message.reply_text(f"{setup}\n\n{punchline}", reply_markup=markup)
        else:
            # Отступ 12 пробелов
            logger.error(f"/joke: Не удалось извлечь setup/punchline из ответа: {data}")
            await update.message.reply_text("Необычный формат шутки пришел.", reply_markup=markup)
    # Отступ 4 пробела
    except aiohttp.ClientError as e:
        # Отступ 8 пробелов
        logger.error(f"/joke: Ошибка сети: {e}", exc_info=True)
        await update.message.reply_text("Не смог связаться с сервером шуток.", reply_markup=markup)
    # Отступ 4 пробела
    except json.JSONDecodeError as e:
        # Отступ 8 пробелов
        logger.error(f"/joke: Ошибка декодирования JSON: {e}", exc_info=True)
        await update.message.reply_text("Сервер шуток ответил непонятное.", reply_markup=markup)
    # Отступ 4 пробела
    except Exception as e:
        # Отступ 8 пробелов
        logger.error(f"/joke: Непредвиденная ошибка: {e}", exc_info=True)
        await update.message.reply_text("Ой, ошибка при поиске шутки.", reply_markup=markup)

async def weather_command_direct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Отступ 4 пробела
    logger.info("Вызвана /weather Город")
    city = " ".join(context.args) if context.args else None
    if city:
        # Отступ 8 пробелов
        await fetch_and_send_weather(update, context, city)
    else:
        # Отступ 8 пробелов
        await update.message.reply_text("Укажите город: /weather Город", reply_markup=markup)

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Отступ 4 пробела
    logger.info("Вызвана О боте")
    await update.message.reply_text("Бот для шуток и погоды.", reply_markup=markup)

# --- Функции диалога погоды ---
async def weather_button_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Отступ 4 пробела
    logger.info("Вход в диалог погоды через кнопку")
    await update.message.reply_text("Введите название города, для которого хотите узнать погоду:",
                                    reply_markup=ReplyKeyboardRemove()) # Убираем основную клавиатуру
    return GET_CITY # Переходим в состояние ожидания города

async def received_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Отступ 4 пробела
    city=update.message.text
    logger.info(f"Диалог: получен город: {city}")
    await fetch_and_send_weather(update, context, city) # Вызываем функцию погоды
    logger.info("Диалог погоды завершен.")
    # Возвращаем основную клавиатуру после показа погоды
    # await update.message.reply_text("Что дальше?", reply_markup=markup) # Можно добавить, если нужно
    return ConversationHandler.END # Завершаем диалог

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Отступ 4 пробела
    logger.info("Диалог (вероятно, погоды) отменен командой /cancel")
    await update.message.reply_text('Действие отменено.', reply_markup=markup) # Возвращаем основную клавиатуру
    return ConversationHandler.END # Завершаем диалог

# --- Обработка обновления ---
async def process_one_update(update_data):
    # Отступ 4 пробела
    if not TELEGRAM_TOKEN:
        # Отступ 8 пробелов
        logger.error("Токен не найден!")
        return
    # Отступ 4 пробела
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # --- ConversationHandler ---
    # Отступ 4 пробела
    logger.debug("Определение ConversationHandler для погоды...")
    conv_handler_weather = ConversationHandler(
        # Отступ 8 пробелов
        entry_points=[MessageHandler(filters.TEXT & filters.Regex(r'^Погода 🌦️$'), weather_button_entry)], # Точка входа - кнопка "Погода"
        states={
            # Отступ 12 пробелов
            GET_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_city)] # Ожидаем текст (город)
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)] # Выход из диалога по /cancel
    )
    # Отступ 4 пробела
    logger.debug("Добавление ConversationHandler...")
    application.add_handler(conv_handler_weather)
    # --- КОНЕЦ ConversationHandler ---

    # --- Добавляем остальные обработчики ---
    # Отступ 4 пробела
    logger.debug("Добавление CommandHandler(start)...")
    application.add_handler(CommandHandler("start", start))
    logger.debug("Добавление CommandHandler(joke)...")
    application.add_handler(CommandHandler("joke", joke_command))
    logger.debug("Добавление CommandHandler(weather)...")
    application.add_handler(CommandHandler("weather", weather_command_direct)) # Для прямого вызова /weather Город
    logger.debug("Добавление MessageHandler(Шутка)...")
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^Шутка 🎲$'), joke_command))
    logger.debug("Добавление MessageHandler(О боте)...")
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^О боте ℹ️$'), about_command))

    # --- Отдельный /cancel для общего пользования ---
    # Если добавить, то /cancel будет работать всегда, а не только в диалоге
    # application.add_handler(CommandHandler('cancel', cancel_conversation))

    # Отступ 4 пробела
    logger.info("Все обработчики добавлены.")
    try:
        # Отступ 8 пробелов
        logger.debug(f"Инит приложения для {update_data.get('update_id')}")
        await application.initialize()
        update = Update.de_json(update_data, application.bot)
        # Логгируем входящее сообщение
        if update.message:
            # Отступ 12 пробелов
            logger.info(f"Получено сообщение: type={update.message.chat.type}, text='{update.message.text}'")
        elif update.callback_query:
            # Отступ 12 пробелов
            logger.info(f"Получен callback_query: data='{update.callback_query.data}'")
        else:
            # Отступ 12 пробелов
            logger.info(f"Получен другой тип обновления: {update}")
        # Отступ 8 пробелов
        logger.debug(f"Запуск process_update для {update.update_id}")
        await application.process_update(update) # <- Основная обработка
        logger.debug(f"Завершение shutdown для {update.update_id}")
        await application.shutdown()
    # Отступ 4 пробела
    except Exception as e:
        # Отступ 8 пробелов
        logger.error(f"Критическая ошибка {update_data.get('update_id', 'N/A')}: {e}", exc_info=True)
        # Проверяем, инициализировано ли приложение перед shutdown
        if application.initialized:
             # Отступ 12 пробелов
             await application.shutdown()


# --- Точка входа Vercel ---
class handler(BaseHTTPRequestHandler): # Начало класса, нет отступа

    # Отступ 4 пробела перед def log_message
    def log_message(self, format, *args):
        # Отступ 8 пробелов перед logger.info
        logger.info("%s - %s" % (self.address_string(), format % args))

    # Отступ 4 пробела перед def do_POST
    def do_POST(self):
        """Обрабатывает входящие POST-запросы от Telegram."""
        # Отступ 8 пробелов перед logger.info
        logger.info("!!! Вход в do_POST !!!")
        # Отступ 8 пробелов перед if not TELEGRAM_TOKEN: (ЭТА СТРОКА БЫЛА ПРОБЛЕМНОЙ)
        if not TELEGRAM_TOKEN:
            # Отступ 12 пробелов перед logger.error и далее внутри if
            logger.error("POST: Токен не найден")
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Token error")
            return # Выходим, если нет токена

        # Отступ 8 пробелов перед try
        try:
            # Отступ 12 пробелов перед content_len
            content_len = int(self.headers.get('Content-Length', 0))
            # Отступ 12 пробелов перед if content_len == 0:
            if content_len == 0:
                 # Отступ 16 пробелов перед logger.warning и далее внутри if
                 logger.warning("POST: Пустое тело")
                 self.send_response(400)
                 self.send_header('Content-type', 'text/plain')
                 self.end_headers()
                 self.wfile.write(b"Empty body")
                 return

            # Отступ 12 пробелов перед body_bytes
            body_bytes = self.rfile.read(content_len)
            # Отступ 12 пробелов перед body_json
            body_json = json.loads(body_bytes.decode('utf-8'))
            # Отступ 12 пробелов перед logger.info
            logger.info("POST: JSON получен")

            # Запускаем асинхронную обработку
            # Отступ 12 пробелов перед asyncio.run
            asyncio.run(process_one_update(body_json))

            # Отвечаем Telegram НЕМЕДЛЕННО
            # Отступ 12 пробелов перед self.send_response
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")
            # Отступ 12 пробелов перед logger.info
            logger.info("POST: Ответ 200 OK")

        # Отступ 8 пробелов перед except json.JSONDecodeError
        except json.JSONDecodeError:
            # Отступ 12 пробелов перед logger.error и далее внутри except
            logger.error("POST: Ошибка JSON", exc_info=True)
            self.send_response(400)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Invalid JSON")
            return
        # Отступ 8 пробелов перед except Exception
        except Exception as e:
            # Отступ 12 пробелов перед logger.error и далее внутри except
            logger.error(f"POST: Ошибка в do_POST: {e}", exc_info=True)
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Internal Error")
            return

    # Отступ 4 пробела перед def do_GET
    def do_GET(self):
        # Отступ 8 пробелов перед logger.info
        logger.info("GET /api/webhook")
        # Отступ 8 пробелов перед self.send_response
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot OK")
        return
# Конец класса handler