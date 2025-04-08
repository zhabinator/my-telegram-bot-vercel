# -*- coding: utf-8 -*-
import os
import asyncio
import json
import logging
from http.server import BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования (чтобы видеть сообщения о работе в Vercel)
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
    def do_POST(self):
        if not TELEGRAM_TOKEN:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Bot token not configured")
            return

        try:
            content_len = int(self.headers.get('Content-Length', 0))
            body_bytes = self.rfile.read(content_len)
            body_json = json.loads(body_bytes.decode('utf-8'))

            # Запускаем нашу асинхронную функцию обработки
            asyncio.run(process_update(body_json))

            # Сразу отвечаем Telegram "ОК", чтобы он не ждал
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")
        except Exception as e:
            logger.error(f"Ошибка в do_POST: {e}", exc_info=True)
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Internal Server Error")

    def do_GET(self):
        # Просто для проверки, что URL работает
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Hello! Telegram Bot is waiting for POST requests.")