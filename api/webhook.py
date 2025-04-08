# -*- coding: utf-8 -*-
import os
import asyncio
import json
import logging
from http.server import BaseHTTPRequestHandler # Используем стандартный модуль для простоты
from urllib.parse import parse_qs

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования (логи будут видны в Vercel Dashboard)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Берем ТОКЕН из настроек Vercel (НЕ из кода!)
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')

# --- Что бот будет делать ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ответ на команду /start"""
    await update.message.reply_text('Привет! Отправь мне сообщение, и я его повторю.')

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Повторяет сообщение пользователя"""
    user_text = update.message.text
    await update.message.reply_text(f'Вы написали: {user_text}')

# --- Техническая часть для обработки сообщений от Telegram ---
async def process_update(update_data):
    if not TELEGRAM_TOKEN:
        logger.error("Токен не найден!")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    try:
        update = Update.de_json(update_data, application.bot)
        # Запускаем обработку, но не ждем ее завершения здесь
        asyncio.create_task(application.process_update(update))
        logger.info(f"Запущена обработка обновления {update.update_id}")
    except Exception as e:
        logger.error(f"Ошибка обработки: {e}", exc_info=True)

# --- Точка входа, которую будет вызывать Vercel ---
class handler(BaseHTTPRequestHandler):

    # Отключаем стандартное логирование BaseHTTPRequestHandler, используем свое
    def log_message(self, format, *args):
          logger.info("%s - %s" % (self.address_string(), format%args))

    def do_POST(self):
        # --- !!! НОВАЯ СТРОКА ЛОГИРОВАНИЯ !!! ---
        logger.info("!!! Вход в do_POST !!!")
        # ------------------------------------------

        if not TELEGRAM_TOKEN:
            logger.error("POST-запрос получен, но токен не установлен.")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Bot token not configured")
            return

        try:
            content_len = int(self.headers.get('Content-Length', 0))
            if content_len == 0:
                 logger.warning("Получен POST-запрос без тела (Content-Length: 0)")
                 self.send_response(400) # Bad Request
                 self.end_headers()
                 self.wfile.write(b"Empty request body")
                 return

            body_bytes = self.rfile.read(content_len)
            body_json = json.loads(body_bytes.decode('utf-8'))
            logger.info("Получены данные JSON от Telegram")

            # Запускаем нашу асинхронную функцию обработки
            asyncio.run(process_update(body_json))

            # Сразу отвечаем Telegram "ОК", чтобы он не ждал
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")
            logger.info("Отправлен ответ 200 OK")

        except json.JSONDecodeError:
            logger.error("Не удалось декодировать JSON из тела запроса", exc_info=True)
            self.send_response(400) # Bad Request
            self.end_headers()
            self.wfile.write(b"Invalid JSON")
        except Exception as e:
            logger.error(f"Необработанная ошибка в do_POST: {e}", exc_info=True)
            self.send_response(500) # Internal Server Error
            self.end_headers()
            self.wfile.write(b"Internal Server Error")

    def do_GET(self):
        """Обрабатывает GET-запросы (например, для проверки доступности)."""
        # Просто для проверки, что URL работает
        logger.info("Обработан GET-запрос")
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Hello! Telegram Bot is waiting for POST requests.".encode('utf-8'))