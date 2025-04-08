# -*- coding: utf-8 -*-
import os
import asyncio
import json
import logging
import aiohttp # <-- Добавлен импорт для HTTP-запросов

from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен из настроек Vercel
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')

# --- Обработчики команд и сообщений ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ответ на команду /start"""
    await update.message.reply_text('Привет! Я бот. Могу повторить твое сообщение или рассказать шутку по команде /joke.')

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Повторяет сообщение пользователя"""
    user_text = update.message.text
    await update.message.reply_text(f'Вы написали: {user_text}')

# --- НОВАЯ ФУНКЦИЯ ДЛЯ КОМАНДЫ /joke ---
async def joke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет случайную шутку"""
    joke_api_url = "https://official-joke-api.appspot.com/random_joke"
    logger.info(f"Запрос шутки с {joke_api_url}")
    try:
        # Используем aiohttp для асинхронного запроса
        async with aiohttp.ClientSession() as session:
            async with session.get(joke_api_url) as response:
                # Проверяем статус ответа, если не 200 OK, вызовет ошибку
                response.raise_for_status()
                # Получаем данные в формате JSON
                data = await response.json()
                logger.info(f"Получен ответ от API шуток: {data}")

        # Извлекаем части шутки
        setup = data.get("setup")
        punchline = data.get("punchline")

        if setup and punchline:
            # Формируем сообщение
            joke_text = f"{setup}\n\n{punchline}"
            await update.message.reply_text(joke_text)
        else:
            logger.error(f"Не удалось извлечь setup/punchline из ответа: {data}")
            await update.message.reply_text("Необычный формат шутки пришел. Попробуй еще раз!")

    # Обработка возможных ошибок при запросе к API
    except aiohttp.ClientError as e:
        logger.error(f"Ошибка сети при запросе шутки: {e}", exc_info=True)
        await update.message.reply_text("Не смог связаться с сервером шуток. Попробуй позже.")
    except json.JSONDecodeError as e:
         logger.error(f"Ошибка декодирования JSON от API шуток: {e}", exc_info=True)
         await update.message.reply_text("Сервер шуток ответил что-то непонятное. Попробуй позже.")
    except Exception as e:
        # Ловим любые другие непредвиденные ошибки
        logger.error(f"Непредвиденная ошибка при получении шутки: {e}", exc_info=True)
        await update.message.reply_text("Ой, что-то пошло не так при поиске шутки. Попробуй позже.")
# --- КОНЕЦ НОВОЙ ФУНКЦИИ ---


# --- Функция обработки ОДНОГО обновления ---
async def process_one_update(update_data):
    if not TELEGRAM_TOKEN:
        logger.error("Токен не найден в переменных окружения!")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # --- !!! ДОБАВЛЕН ОБРАБОТЧИК ДЛЯ /joke !!! ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("joke", joke_command)) # <-- Добавили эту строку
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    # --------------------------------------------

    try:
        await application.initialize()
        update = Update.de_json(update_data, application.bot)
        await application.process_update(update)
        await application.shutdown()
        logger.info(f"Успешно обработано обновление {update.update_id}")
    except Exception as e:
        logger.error(f"Ошибка при обработке обновления {update_data.get('update_id', 'N/A')}: {e}", exc_info=True)
        if application.initialized:
            try:
                await application.shutdown()
            except Exception as shutdown_e:
                logger.error(f"Ошибка при shutdown после ошибки: {shutdown_e}", exc_info=True)


# --- Точка входа для Vercel ---
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
        self.wfile.write(b"Hello! Telegram Bot webhook endpoint is active.")