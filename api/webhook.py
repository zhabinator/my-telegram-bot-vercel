# -*- coding: utf-8 -*-
import os
import asyncio
import json
import logging
import random # Для выбора случайного поздравления

from http.server import BaseHTTPRequestHandler

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# --- Настройка логирования ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

# --- Ключ Telegram ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')

# --- Список поздравлений (С ИСПРАВЛЕННОЙ ЗАПЯТОЙ!) ---
congratulations_list = [
    "Будть всегда very sugar🎉",
    "Ты - ловушка для мужского Вау! 💖",
    "Главная статья в кодексе красоты 🥳",
    "Ты делаешь аппетит приятнее ✨",
    "Ароматного дня, миледи🥰",
    "Рядом с вами не хочется моргать🥰",
    "Если красота спасет мир, то вся надежда только на тебя!🥰", # <-- ИСПРАВЛЕНО: Добавлена запятая
    "Целуем тот день, когда ты родилась!💖",
    "Море удачи и дачи у моря! 💖",
]

# --- Клавиатура ---
reply_keyboard = [
    [KeyboardButton("Полить сердечко сиропом ❤️")]
]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)

# --- Обработчики ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет приветствие и показывает кнопку."""
    logger.info("Вызвана /start")
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.mention_html()}! Готов полить сердечко? ❤️",
        parse_mode='HTML',
        reply_markup=markup
    )

async def syrup_heart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет случайное поздравление при нажатии кнопки."""
    logger.info("Нажата кнопка 'Полить сердечко сиропом'")
    random_congrats = random.choice(congratulations_list)
    await update.message.reply_text(random_congrats, reply_markup=markup)

# --- Обработка обновления ---
async def process_one_update(update_data):
    if not TELEGRAM_TOKEN:
        logger.error("Токен не найден!")
        return
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    # Убедитесь, что Regex ТОЧНО совпадает с текстом кнопки
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^Полить сердечко сиропом ❤️$'), syrup_heart_handler))

    logger.info("Упрощенные обработчики добавлены.")
    try:
        await application.initialize()
        update = Update.de_json(update_data, application.bot)
        if update.message:
            logger.info(f"Получено сообщение: type={update.message.chat.type}, text='{update.message.text}'")
        else:
            logger.info(f"Получен другой тип обновления: {update}")
        await application.process_update(update)
        await application.shutdown()
    except Exception as e:
        logger.error(f"Критическая ошибка {update_data.get('update_id', 'N/A')}: {e}", exc_info=True)
        if application.initialized:
             await application.shutdown()


# --- Точка входа Vercel (без изменений) ---
class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logger.info("%s - %s" % (self.address_string(), format % args))
    def do_POST(self):
        logger.info("!!! Вход в do_POST !!!")
        if not TELEGRAM_TOKEN:
            logger.error("POST: Токен не найден")
            self.send_response(500); self.end_headers(); self.wfile.write(b"Token error"); return
        try:
            content_len = int(self.headers.get('Content-Length', 0))
            if content_len == 0:
                 logger.warning("POST: Пустое тело")
                 self.send_response(400); self.end_headers(); self.wfile.write(b"Empty body"); return
            body_bytes = self.rfile.read(content_len)
            body_json = json.loads(body_bytes.decode('utf-8'))
            logger.info("POST: JSON получен")
            asyncio.run(process_one_update(body_json))
            self.send_response(200); self.send_header('Content-type', 'text/plain'); self.end_headers(); self.wfile.write(b"OK")
            logger.info("POST: Ответ 200 OK")
        except json.JSONDecodeError:
            logger.error("POST: Ошибка JSON", exc_info=True)
            self.send_response(400); self.end_headers(); self.wfile.write(b"Invalid JSON"); return
        except Exception as e:
            logger.error(f"POST: Ошибка в do_POST: {e}", exc_info=True)
            self.send_response(500); self.end_headers(); self.wfile.write(b"Internal Error"); return
    def do_GET(self):
        logger.info("GET /api/webhook")
        self.send_response(200); self.send_header('Content-type', 'text/plain'); self.end_headers()
        self.wfile.write(b"Bot OK (Syrup Heart Version)"); return