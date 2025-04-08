# -*- coding: utf-8 -*-
import os
import asyncio
import json
import logging
import aiohttp # Для асинхронных HTTP-запросов
import re # Для Regex

from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

# --- !!! ДОБАВЛЕНЫ НОВЫЕ ИМПОРТЫ !!! ---
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
# ReplyKeyboardRemove можно добавить, если захотите убирать клавиатуру
# --------------------------------------
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Получаем ключи из переменных окружения ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
OWM_API_KEY = os.environ.get('OWM_API_KEY')
# --------------------------------------------

# --- Определяем кнопки для клавиатуры ---
# Каждый вложенный список - это ряд кнопок
reply_keyboard = [
    [KeyboardButton("Шутка 🎲"), KeyboardButton("Погода 🌦️")],
    [KeyboardButton("О боте ℹ️")]
]
# Создаем объект клавиатуры
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)
# resize_keyboard=True - подгоняет размер кнопок
# one_time_keyboard=False - клавиатура не исчезнет после первого нажатия
# -----------------------------------------


# --- Обработчики команд и кнопок ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ответ на команду /start - теперь с клавиатурой"""
    user_name = update.effective_user.first_name or "Пользователь"
    await update.message.reply_text(
        f'Привет, {user_name}! Выбери действие:',
        reply_markup=markup # <-- Отправляем клавиатуру вместе с сообщением
    )

async def joke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет случайную шутку (вызывается и командой /joke и кнопкой)"""
    # ... (код функции joke_command остается БЕЗ ИЗМЕНЕНИЙ) ...
    joke_api_url = "https://official-joke-api.appspot.com/random_joke"
    logger.info(f"Вызвана /joke или кнопка 'Шутка'. Запрос шутки с {joke_api_url}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(joke_api_url) as response:
                response.raise_for_status()
                data = await response.json()
                logger.info(f"/joke: Получен ответ от API шуток: {data}")
        setup = data.get("setup")
        punchline = data.get("punchline")
        if setup and punchline:
            joke_text = f"{setup}\n\n{punchline}"
            await update.message.reply_text(joke_text, reply_markup=markup) # Снова показываем клавиатуру
        else:
            logger.error(f"/joke: Не удалось извлечь setup/punchline из ответа: {data}")
            await update.message.reply_text("Необычный формат шутки пришел. Попробуй еще раз!", reply_markup=markup)
    except aiohttp.ClientError as e:
        logger.error(f"/joke: Ошибка сети при запросе шутки: {e}", exc_info=True)
        await update.message.reply_text("Не смог связаться с сервером шуток. Попробуй позже.", reply_markup=markup)
    except json.JSONDecodeError as e:
         logger.error(f"/joke: Ошибка декодирования JSON от API шуток: {e}", exc_info=True)
         await update.message.reply_text("Сервер шуток ответил что-то непонятное. Попробуй позже.", reply_markup=markup)
    except Exception as e:
        logger.error(f"/joke: Непредвиденная ошибка при получении шутки: {e}", exc_info=True)
        await update.message.reply_text("Ой, что-то пошло не так при поиске шутки. Попробуй позже.", reply_markup=markup)


async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет погоду для указанного города (вызывается командой /weather Город)"""
    # ... (код функции weather_command остается БЕЗ ИЗМЕНЕНИЙ) ...
    logger.info("Вызвана команда /weather")
    if not OWM_API_KEY:
        logger.error("/weather: Ключ OWM_API_KEY не найден.")
        await update.message.reply_text("Ключ для сервиса погоды не настроен.", reply_markup=markup)
        return
    if not context.args:
        logger.info("/weather: Команда вызвана без аргументов.")
        await update.message.reply_text("Пожалуйста, укажите город после команды: /weather НазваниеГорода", reply_markup=markup)
        return
    city_name = " ".join(context.args)
    weather_api_url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={OWM_API_KEY}&units=metric&lang=ru"
    logger.info(f"/weather: Запрос погоды для '{city_name}' с {weather_api_url}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(weather_api_url) as response:
                if response.status == 401:
                     logger.error(f"/weather: Ошибка 401 от OWM API для города '{city_name}'. Проверьте API ключ.")
                     await update.message.reply_text("Ошибка авторизации на сервере погоды.", reply_markup=markup)
                     return
                if response.status == 404:
                    logger.warning(f"/weather: Город '{city_name}' не найден OWM API (404).")
                    await update.message.reply_text(f"Не могу найти город '{city_name}'.", reply_markup=markup)
                    return
                response.raise_for_status()
                data = await response.json()
                logger.info(f"/weather: Получен ответ от OWM API: {data}")
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
        await update.message.reply_text(weather_text, reply_markup=markup)
    except aiohttp.ClientError as e:
        logger.error(f"/weather: Ошибка сети для '{city_name}': {e}", exc_info=True)
        await update.message.reply_text("Не смог связаться с сервером погоды.", reply_markup=markup)
    except json.JSONDecodeError as e:
         logger.error(f"/weather: Ошибка JSON для '{city_name}': {e}", exc_info=True)
         await update.message.reply_text("Сервер погоды ответил что-то непонятное.", reply_markup=markup)
    except Exception as e:
        logger.error(f"/weather: Непредвиденная ошибка для '{city_name}': {e}", exc_info=True)
        await update.message.reply_text("Ой, что-то пошло не так с погодой.", reply_markup=markup)

# --- НОВАЯ ФУНКЦИЯ ДЛЯ КНОПКИ "Погода 🌦️" ---
async def ask_for_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Напоминает, как использовать команду погоды"""
    logger.info("Нажата кнопка 'Погода'")
    await update.message.reply_text(
        "Чтобы узнать погоду, пожалуйста, отправьте команду в формате: /weather НазваниеГорода",
        reply_markup=markup # Показываем клавиатуру снова
    )

# --- НОВАЯ ФУНКЦИЯ ДЛЯ КНОПКИ "О боте ℹ️" ---
async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет информацию о боте"""
    logger.info("Нажата кнопка 'О боте'")
    # Можете изменить этот текст
    await update.message.reply_text(
        "Я простой бот, созданный для демонстрации. Я умею рассказывать шутки и показывать погоду!",
        reply_markup=markup # Показываем клавиатуру снова
    )


# --- Функция обработки ОДНОГО обновления ---
async def process_one_update(update_data):
    if not TELEGRAM_TOKEN:
        logger.error("process_one_update: Токен не найден!")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # --- !!! ОБНОВЛЕННАЯ РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ !!! ---
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("joke", joke_command)) # Оставляем для совместимости
    application.add_handler(CommandHandler("weather", weather_command)) # Оставляем команду

    # Обработчики для кнопок (реагируем на точный текст кнопки)
    # Используем filters.Regex с ^ и $ для точного совпадения текста кнопки
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^Шутка 🎲$'), joke_command))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^Погода 🌦️$'), ask_for_city))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^О боте ℹ️$'), about_command))

    # Важно: НЕ добавляем обработчик для всех остальных текстовых сообщений,
    # чтобы он не мешал кнопкам и командам. Если нужен echo, добавлять его ПОСЛЕ всех.
    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    # -----------------------------------------------------

    logger.info("process_one_update: Обработчики добавлены (с кнопками ReplyKeyboard).")

    try:
        await application.initialize()
        update = Update.de_json(update_data, application.bot)

        if update.message:
            logger.info(f"process_one_update: Получено сообщение: type={update.message.chat.type}, text='{update.message.text}'")
        elif update.callback_query:
             logger.info(f"process_one_update: Получен callback_query: data='{update.callback_query.data}'")
        else:
             logger.info(f"process_one_update: Получен другой тип обновления: {update}")

        await application.process_update(update)
        await application.shutdown()
    except Exception as e:
        logger.error(f"Критическая ошибка при обработке обновления {update_data.get('update_id', 'N/A')}: {e}", exc_info=True)
        if application.initialized:
            try:
                await application.shutdown()
            except Exception as shutdown_e:
                logger.error(f"Ошибка при shutdown после критической ошибки: {shutdown_e}", exc_info=True)


# --- Точка входа для Vercel (остается без изменений) ---
class handler(BaseHTTPRequestHandler):
    # ... (log_message, do_POST, do_GET без изменений) ...
    def log_message(self, format, *args):
          logger.info("%s - %s" % (self.address_string(), format%args))
    def do_POST(self):
        logger.info("!!! Вход в do_POST !!!")
        if not TELEGRAM_TOKEN: logger.error("POST-запрос: Токен не загружен."); self.send_response(500); self.end_headers(); self.wfile.write(b"Bot token not configured"); return
        try:
            content_len = int(self.headers.get('Content-Length', 0))
            if content_len == 0: logger.warning("POST-запрос: Пустое тело."); self.send_response(400); self.end_headers(); self.wfile.write(b"Empty request body"); return
            body_bytes = self.rfile.read(content_len)
            body_json = json.loads(body_bytes.decode('utf-8'))
            logger.info("POST-запрос: JSON получен и декодирован.")
            asyncio.run(process_one_update(body_json))
            self.send_response(200); self.send_header('Content-type', 'text/plain'); self.end_headers(); self.wfile.write(b"OK"); logger.info("POST-запрос: Ответ 200 OK отправлен.")
        except json.JSONDecodeError: logger.error("POST-запрос: Ошибка декодирования JSON.", exc_info=True); self.send_response(400); self.end_headers(); self.wfile.write(b"Invalid JSON received"); return
        except Exception as e: logger.error(f"POST-запрос: Необработанная ошибка в do_POST: {e}", exc_info=True); self.send_response(500); self.end_headers(); self.wfile.write(b"Internal Server Error occurred"); return
    def do_GET(self): logger.info("Обработан GET-запрос к /api/webhook"); self.send_response(200); self.send_header('Content-type', 'text/plain'); self.end_headers(); self.wfile.write(b"Hello! Telegram Bot webhook endpoint is active."); return