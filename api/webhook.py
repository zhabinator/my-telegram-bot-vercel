# -*- coding: utf-8 -*-
import os
import asyncio
import json
import logging
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
    await update.message.reply_text('Привет! Отправь мне сообщение, и я его повторю.')

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await update.message.reply_text(f'Вы написали: {user_text}')

# --- Функция обработки ОДНОГО обновления ---
async def process_one_update(update_data):
    if not TELEGRAM_TOKEN:
        logger.error("Токен не найден в переменных окружения!")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    try:
        # --- !!! ВАЖНЫЕ ИЗМЕНЕНИЯ ЗДЕСЬ !!! ---
        await application.initialize() # Инициализируем приложение
        update = Update.de_json(update_data, application.bot)
        await application.process_update(update) # Обрабатываем обновление (ждем завершения)
        await application.shutdown() # Корректно завершаем работу приложения
        # -------------------------------------
        logger.info(f"Успешно обработано обновление {update.update_id}")
    except Exception as e:
        logger.error(f"Ошибка при обработке обновления {update_data.get('update_id', 'N/A')}: {e}", exc_info=True)
        # Попытаемся завершить приложение даже при ошибке, если оно было инициализировано
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

            # Запускаем обработку одного обновления
            # asyncio.run подходит для вызова async функции из sync контекста
            asyncio.run(process_one_update(body_json)) # Используем новую функцию

            # Отвечаем Telegram OK *после* попытки обработки
            # (В serverless это обычно нормально, функция не будет работать слишком долго)
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