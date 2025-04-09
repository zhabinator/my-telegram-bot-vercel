# -*- coding: utf-8 -*-
import os
import asyncio
import json
import logging
import random # Добавили для выбора случайного поздравления

from http.server import BaseHTTPRequestHandler
# Убрали urllib.parse, так как он больше не нужен

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton # Убрали ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
    # Убрали ConversationHandler и связанные импорты
)

# --- Настройка логирования (можно вернуть INFO, если DEBUG не нужен) ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO # Можно поставить INFO для менее подробных логов
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING) # Подавляем лишние логи httpx

# --- Ключи ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
# OWM_API_KEY больше не нужен

# --- Список поздравлений (Добавьте или измените по своему вкусу!) ---
congratulations_list = [
    "Будть всегда very sugar🎉",
    "Ты - ловушка для мужского Вау! 💖",
    "Главная статья в кодексе красоты 🥳",
    "Ты делаешь аппетит приятнее ✨",
    "Ароматного дня, миледи🥰"
    "Рядом с вами не хочется моргать🥰"
    "Если красота спасет мир, то вся надежда только на тебя!🥰"
    "Целуем тот день, когда ты родилась!💖"
    "Море удачи и дачи у моря! 💖"
]

# --- Новая Клавиатура ---
reply_keyboard = [
    [KeyboardButton("Полить сердечко сиропом ❤️")] # Одна кнопка
]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False) # one_time_keyboard=False, чтобы не скрывалась сразу

# --- Новые Обработчики ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет приветствие и показывает кнопку."""
    logger.info("Вызвана /start")
    user = update.effective_user
    # Более простое приветствие
    await update.message.reply_text(
        f"Привет, {user.mention_html()}! Готов полить сердечко? ❤️",
        parse_mode='HTML',
        reply_markup=markup
    )

async def syrup_heart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет случайное поздравление при нажатии кнопки."""
    logger.info("Нажата кнопка 'Полить сердечко сиропом'")
    # Выбираем случайное поздравление из списка
    random_congrats = random.choice(congratulations_list)
    await update.message.reply_text(random_congrats, reply_markup=markup)

# --- Упрощенная Обработка обновления ---
async def process_one_update(update_data):
    # Отступ 4 пробела
    if not TELEGRAM_TOKEN:
        # Отступ 8 пробелов
        logger.error("Токен не найден!")
        return
    # Отступ 4 пробела
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # --- Добавляем ТОЛЬКО нужные обработчики ---
    # Отступ 4 пробела
    logger.debug("Добавление CommandHandler(start)...")
    application.add_handler(CommandHandler("start", start))
    logger.debug("Добавление MessageHandler(Полить сердечко)...")
    # ВАЖНО: Regex должен ТОЧНО совпадать с текстом кнопки!
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^Полить сердечко сиропом ❤️$'), syrup_heart_handler))

    # Отступ 4 пробела
    logger.info("Упрощенные обработчики добавлены.")
    try:
        # Отступ 8 пробелов
        logger.debug(f"Инит приложения для {update_data.get('update_id')}")
        await application.initialize()
        update = Update.de_json(update_data, application.bot)
        # Логгируем входящее сообщение
        if update.message:
            # Отступ 12 пробелов
            logger.info(f"Получено сообщение: type={update.message.chat.type}, text='{update.message.text}'")
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


# --- Точка входа Vercel (Оставляем БЕЗ ИЗМЕНЕНИЙ) ---
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
        # Отступ 8 пробелов перед if not TELEGRAM_TOKEN:
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
        self.wfile.write(b"Bot OK (Syrup Heart Version)") # Можно изменить текст для GET запроса
        return
# Конец класса handler