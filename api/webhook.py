# -*- coding: utf-8 -*-
import os
import asyncio
import json
import logging
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

# Убедитесь, что эти строки импорта есть и правильные
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования (логи будут видны в Vercel Dashboard)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- !!! ИСПРАВЛЕННАЯ СТРОКА !!! ---
# Берем ТОКЕН из настроек Vercel (НЕ из кода!)
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
# ------------------------------------

# --- Что бот будет делать ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ответ на команду /start"""
    # Вы можете изменить этот текст, если хотите, например, добавить @имя_бота
    await update.message.reply_text('Привет! Отправь мне сообщение, и я его повторю.')

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Повторяет сообщение пользователя"""
    user_text = update.message.text
    await update.message.reply_text(f'Вы написали: {user_text}')

# --- Техническая часть для обработки сообщений от Telegram ---
async def process_update(update_data):
    if not TELEGRAM_TOKEN:
        logger.error("Токен не найден в переменных окружения!")
        return # Выходим, если токена нет

    # Создаем экземпляр приложения при каждом запросе (важно для serverless)
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Добавляем обработчики команд и сообщений
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    try:
        # Преобразуем JSON от Telegram в объект Update
        update = Update.de_json(update_data, application.bot)
        # Запускаем асинхронную обработку этого обновления
        asyncio.create_task(application.process_update(update))
        # Логируем, что обработка запущена (но не ждем ее завершения здесь)
        logger.info(f"Запущена обработка обновления {update.update_id}")
    except Exception as e:
        logger.error(f"Ошибка при десериализации или запуске process_update: {e}", exc_info=True)

# --- Точка входа, которую будет вызывать Vercel ---
class handler(BaseHTTPRequestHandler):

    # Отключаем стандартное логирование BaseHTTPRequestHandler, чтобы не дублировать
    def log_message(self, format, *args):
          # Используем наш настроенный логгер
          logger.info("%s - %s" % (self.address_string(), format%args))

    def do_POST(self):
        # --- Строка логирования для диагностики ---
        logger.info("!!! Вход в do_POST !!!")
        # ------------------------------------------

        # Проверяем, удалось ли получить токен при старте функции
        if not TELEGRAM_TOKEN:
            logger.error("POST-запрос получен, но токен не был загружен из окружения.")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Bot token not configured correctly on server")
            return

        try:
            # Получаем длину тела запроса
            content_len = int(self.headers.get('Content-Length', 0))
            if content_len == 0:
                 logger.warning("Получен POST-запрос без тела (Content-Length: 0)")
                 self.send_response(400) # Bad Request
                 self.end_headers()
                 self.wfile.write(b"Empty request body")
                 return

            # Читаем тело запроса (данные от Telegram)
            body_bytes = self.rfile.read(content_len)
            # Декодируем JSON
            body_json = json.loads(body_bytes.decode('utf-8'))
            logger.info("Получены и декодированы данные JSON от Telegram")

            # Запускаем асинхронную функцию обработки обновления
            # asyncio.run подходит для запуска основной точки входа async функции
            asyncio.run(process_update(body_json))

            # Немедленно отвечаем Telegram "ОК", не дожидаясь завершения process_update
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")
            logger.info("Отправлен ответ 200 OK для Telegram")

        except json.JSONDecodeError:
            logger.error("Не удалось декодировать JSON из тела запроса", exc_info=True)
            self.send_response(400) # Bad Request
            self.end_headers()
            self.wfile.write(b"Invalid JSON received")
        except Exception as e:
            # Ловим другие возможные ошибки внутри do_POST
            logger.error(f"Необработанная ошибка в do_POST: {e}", exc_info=True)
            self.send_response(500) # Internal Server Error
            self.end_headers()
            self.wfile.write(b"Internal Server Error occurred")

    def do_GET(self):
        """Обрабатывает GET-запросы (для проверки доступности через браузер)."""
        logger.info("Обработан GET-запрос к /api/webhook")
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        # Отправляем байты, закодированные в utf-8
        self.wfile.write(b"Hello! Telegram Bot is waiting for POST requests from Telegram.")