# -*- coding: utf-8 -*-
import os
import asyncio
import json
import logging
import aiohttp # Для асинхронных HTTP-запросов

from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

# Убедитесь, что эти строки импорта есть и правильные
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO # Установите logging.DEBUG для более подробных логов библиотеки, если нужно
)
logger = logging.getLogger(__name__)

# --- Получаем ключи из переменных окружения ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
OWM_API_KEY = os.environ.get('OWM_API_KEY') # Ключ для OpenWeatherMap
# --------------------------------------------

# --- Обработчики команд ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ответ на команду /start"""
    await update.message.reply_text(
        'Привет! Я бот. Могу рассказать шутку по команде /joke, '
        'или показать погоду: /weather Город'
    )

async def joke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет случайную шутку"""
    joke_api_url = "https://official-joke-api.appspot.com/random_joke"
    logger.info(f"Вызвана /joke. Запрос шутки с {joke_api_url}")
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
            await update.message.reply_text(joke_text)
        else:
            logger.error(f"/joke: Не удалось извлечь setup/punchline из ответа: {data}")
            await update.message.reply_text("Необычный формат шутки пришел. Попробуй еще раз!")

    except aiohttp.ClientError as e:
        logger.error(f"/joke: Ошибка сети при запросе шутки: {e}", exc_info=True)
        await update.message.reply_text("Не смог связаться с сервером шуток. Попробуй позже.")
    except json.JSONDecodeError as e:
         logger.error(f"/joke: Ошибка декодирования JSON от API шуток: {e}", exc_info=True)
         await update.message.reply_text("Сервер шуток ответил что-то непонятное. Попробуй позже.")
    except Exception as e:
        logger.error(f"/joke: Непредвиденная ошибка при получении шутки: {e}", exc_info=True)
        await update.message.reply_text("Ой, что-то пошло не так при поиске шутки. Попробуй позже.")

async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет погоду для указанного города"""
    logger.info("Вызвана команда /weather") # Лог вызова команды

    if not OWM_API_KEY:
        logger.error("/weather: Ключ OWM_API_KEY не найден в переменных окружения.")
        await update.message.reply_text("Ключ для сервиса погоды не настроен на сервере.")
        return

    if not context.args:
        logger.info("/weather: Команда вызвана без аргументов.")
        await update.message.reply_text("Пожалуйста, укажите город после команды: /weather НазваниеГорода")
        return
    city_name = " ".join(context.args)

    weather_api_url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={OWM_API_KEY}&units=metric&lang=ru"
    logger.info(f"/weather: Запрос погоды для '{city_name}' с {weather_api_url}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(weather_api_url) as response:
                if response.status == 401:
                     logger.error(f"/weather: Ошибка 401 от OWM API для города '{city_name}'. Проверьте API ключ.")
                     await update.message.reply_text("Ошибка авторизации на сервере погоды. Возможно, неверный API ключ.")
                     return
                if response.status == 404:
                    logger.warning(f"/weather: Город '{city_name}' не найден OWM API (404).")
                    await update.message.reply_text(f"Не могу найти город '{city_name}'. Убедитесь в правильности написания.")
                    return
                response.raise_for_status() # Проверка на другие ошибки (5xx, 4xx)

                data = await response.json()
                logger.info(f"/weather: Получен ответ от OWM API: {data}")

        # Извлечение данных (с проверками на случай отсутствия полей)
        weather_list = data.get("weather", [])
        main_weather = weather_list[0].get("description", "Нет данных") if weather_list else "Нет данных"
        main_data = data.get("main", {})
        temp = main_data.get("temp", "N/A")
        feels_like = main_data.get("feels_like", "N/A")
        humidity = main_data.get("humidity", "N/A")
        wind_data = data.get("wind", {})
        wind_speed = wind_data.get("speed", "N/A")
        city_display_name = data.get("name", city_name)

        # Формирование текста ответа
        weather_text = (
            f"Погода в городе {city_display_name}:\n"
            f"Описание: {main_weather.capitalize()}\n"
            f"Температура: {temp}°C\n"
            f"Ощущается как: {feels_like}°C\n"
            f"Влажность: {humidity}%\n"
            f"Скорость ветра: {wind_speed} м/с"
        )
        await update.message.reply_text(weather_text)

    except aiohttp.ClientError as e:
        logger.error(f"/weather: Ошибка сети при запросе погоды для '{city_name}': {e}", exc_info=True)
        await update.message.reply_text("Не смог связаться с сервером погоды. Попробуй позже.")
    except json.JSONDecodeError as e:
         logger.error(f"/weather: Ошибка декодирования JSON от OWM API для '{city_name}': {e}", exc_info=True)
         await update.message.reply_text("Сервер погоды ответил что-то непонятное. Попробуй позже.")
    except Exception as e:
        logger.error(f"/weather: Непредвиденная ошибка при получении погоды для '{city_name}': {e}", exc_info=True)
        await update.message.reply_text("Ой, что-то пошло не так при получении погоды. Попробуй позже.")


# --- Функция обработки ОДНОГО обновления ---
async def process_one_update(update_data):
    if not TELEGRAM_TOKEN:
        logger.error("process_one_update: Токен не найден в переменных окружения!")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # --- РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("joke", joke_command))
    application.add_handler(CommandHandler("weather", weather_command))
    # --------------------------------

    logger.info("process_one_update: Обработчики команд добавлены.")

    try:
        logger.debug(f"process_one_update: Инициализация приложения для update_id {update_data.get('update_id')}")
        await application.initialize()
        update = Update.de_json(update_data, application.bot)

        # --- !!! ЛОГИРУЕМ ВХОДЯЩЕЕ СООБЩЕНИЕ !!! ---
        if update.message:
            logger.info(f"process_one_update: Получено сообщение: type={update.message.chat.type}, text='{update.message.text}'")
        elif update.callback_query:
             logger.info(f"process_one_update: Получен callback_query: data='{update.callback_query.data}'")
        else:
             logger.info(f"process_one_update: Получен другой тип обновления: {update}")
        # --------------------------------------------

        logger.debug(f"process_one_update: Запуск process_update для update_id {update.update_id}")
        await application.process_update(update) # <-- Здесь происходит магия (или нет)
        logger.debug(f"process_one_update: Завершение shutdown для update_id {update.update_id}")
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

    def log_message(self, format, *args):
          logger.info("%s - %s" % (self.address_string(), format%args))

    def do_POST(self):
        logger.info("!!! Вход в do_POST !!!")
        if not TELEGRAM_TOKEN:
            logger.error("POST-запрос: Токен не загружен.")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Bot token not configured")
            return
        try:
            content_len = int(self.headers.get('Content-Length', 0))
            if content_len == 0:
                 logger.warning("POST-запрос: Пустое тело.")
                 self.send_response(400)
                 self.end_headers()
                 self.wfile.write(b"Empty request body")
                 return
            body_bytes = self.rfile.read(content_len)
            body_json = json.loads(body_bytes.decode('utf-8'))
            logger.info("POST-запрос: JSON получен и декодирован.")
            asyncio.run(process_one_update(body_json))
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")
            logger.info("POST-запрос: Ответ 200 OK отправлен.")
        except json.JSONDecodeError:
            logger.error("POST-запрос: Ошибка декодирования JSON.", exc_info=True)
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid JSON received")
        except Exception as e:
            logger.error(f"POST-запрос: Необработанная ошибка в do_POST: {e}", exc_info=True)
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Internal Server Error occurred")

    def do_GET(self):
        logger.info("Обработан GET-запрос к /api/webhook")
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Hello! Telegram Bot webhook endpoint is active. Ready for POST requests.")