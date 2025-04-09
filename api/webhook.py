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

# --- Настройка логирования (INFO для продакшена) ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING) # Подавляем лишние логи

# --- Ключ Telegram ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
if not TELEGRAM_TOKEN:
    # Логгируем критическую ошибку, если токен не найден при старте
    logger.critical("Переменная окружения TELEGRAM_TOKEN не установлена!")
    # В реальных условиях это приведет к ошибке 500 при запросе,
    # но лучше залоггировать сразу.

# --- Список поздравлений (С ИСПРАВЛЕННОЙ ЗАПЯТОЙ!) ---
congratulations_list = [
    "Будть всегда very sugar🎉",
    "Ты - ловушка для мужского Вау! 💖",
    "Главная статья в кодексе красоты 🥳",
    "Ты делаешь аппетит приятнее ✨",
    "Ароматного дня, миледи🥰",
    "Рядом с вами не хочется моргать🥰",
    "Если красота спасет мир, то вся надежда только на тебя!🥰", # <-- ИСПРАВЛЕНО
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
    # Отступ 4 пробела
    logger.info(f"Команда /start от user_id: {update.effective_user.id}")
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.mention_html()}! Готов полить сердечко? ❤️",
        parse_mode='HTML',
        reply_markup=markup
    )

async def syrup_heart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет случайное поздравление при нажатии кнопки."""
    # Отступ 4 пробела
    logger.info(f"Нажата кнопка 'Полить сердечко сиропом' от user_id: {update.effective_user.id}")
    try:
        # Отступ 8 пробелов
        random_congrats = random.choice(congratulations_list)
        await update.message.reply_text(random_congrats, reply_markup=markup)
        logger.info(f"Отправлено поздравление для user_id: {update.effective_user.id}")
    # Отступ 4 пробела
    except Exception as e:
        # Отступ 8 пробелов
        logger.error(f"Ошибка в syrup_heart_handler для user_id: {update.effective_user.id}: {e}", exc_info=True)
        # Попытка уведомить пользователя об ошибке
        try: await update.message.reply_text("Ой, что-то пошло не так при выборе поздравления!", reply_markup=markup)
        except Exception as send_err: logger.error(f"Не удалось отправить сообщение об ошибке: {send_err}")


# --- Обработка обновления ---
async def process_one_update(update_data):
    # Отступ 4 пробела
    if not TELEGRAM_TOKEN:
        # Отступ 8 пробелов
        logger.error("Токен не найден при обработке обновления!")
        # Не можем работать без токена
        return

    # Отступ 4 пробела
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # --- Добавляем ТОЛЬКО нужные обработчики ---
    # Отступ 4 пробела
    application.add_handler(CommandHandler("start", start))
    # ВАЖНО: Убедитесь, что Regex точно совпадает с текстом кнопки
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^Полить сердечко сиропом ❤️$'), syrup_heart_handler))

    # Отступ 4 пробела
    logger.info("Простые обработчики (start, кнопка) добавлены.")
    try:
        # Отступ 8 пробелов
        logger.debug(f"Инициализация приложения для update_id: {update_data.get('update_id')}")
        await application.initialize()
        update = Update.de_json(update_data, application.bot)

        # Логгируем входящее сообщение
        if update.message:
            # Отступ 12 пробелов
            logger.info(f"Получено сообщение: chat_id={update.message.chat.id}, user_id={update.effective_user.id}, text='{update.message.text}'")
        else:
            # Отступ 12 пробелов
            logger.info(f"Получен другой тип обновления: {update}")

        # Отступ 8 пробелов
        logger.debug(f"Запуск process_update для update_id: {update.update_id}")
        await application.process_update(update) # <- Основная обработка
        logger.debug(f"Завершение shutdown для update_id: {update.update_id}")
        await application.shutdown()
    # Отступ 4 пробела
    except Exception as e:
        # Отступ 8 пробелов
        logger.error(f"Критическая ошибка при обработке обновления {update_data.get('update_id', 'N/A')}: {e}", exc_info=True)
        if application.initialized:
             # Отступ 12 пробелов
             try: await application.shutdown()
             except Exception as shutdown_e: logger.error(f"Ошибка при shutdown после ошибки: {shutdown_e}", exc_info=True)


# --- Точка входа Vercel (стандартная) ---
class handler(BaseHTTPRequestHandler):
    # Отступ 4 пробела
    def log_message(self, format, *args):
        # Отступ 8 пробелов
        # Используем стандартное логирование Python вместо print
        logger.info("%s - %s" % (self.address_string(), format % args))

    # Отступ 4 пробела
    def do_POST(self):
        # Отступ 8 пробелов
        logger.info("!!! Вход в do_POST !!!")
        if not TELEGRAM_TOKEN:
            # Отступ 12 пробелов
            logger.error("POST: Токен не найден (проверка в do_POST)")
            self.send_response(500); self.end_headers(); self.wfile.write(b"Bot token not configured"); return
        try:
            # Отступ 12 пробелов
            content_len = int(self.headers.get('Content-Length', 0))
            if content_len == 0:
                 # Отступ 16 пробелов
                 logger.warning("POST: Пустое тело запроса")
                 self.send_response(400); self.end_headers(); self.wfile.write(b"Empty request body"); return

            # Отступ 12 пробелов
            body_bytes = self.rfile.read(content_len)
            logger.debug(f"POST: Получено тело запроса (байты): {body_bytes[:200]}...") # Логгируем начало тела
            body_json = json.loads(body_bytes.decode('utf-8'))
            logger.info("POST: JSON получен и декодирован")

            # Запускаем обработку
            # Отступ 12 пробелов
            asyncio.run(process_one_update(body_json))

            # Отвечаем Telegram
            # Отступ 12 пробелов
            self.send_response(200); self.send_header('Content-type', 'text/plain'); self.end_headers(); self.wfile.write(b"OK")
            logger.info("POST: Ответ 200 OK отправлен Telegram.")

        # Отступ 8 пробелов
        except json.JSONDecodeError as e:
            # Отступ 12 пробелов
            logger.error("POST: Ошибка декодирования JSON.", exc_info=True)
            self.send_response(400); self.end_headers(); self.wfile.write(b"Invalid JSON"); return
        # Отступ 8 пробелов
        except Exception as e:
            # Отступ 12 пробелов
            logger.error(f"POST: Необработанная ошибка в do_POST: {e}", exc_info=True)
            self.send_response(500); self.end_headers(); self.wfile.write(b"Internal Server Error"); return

    # Отступ 4 пробела
    def do_GET(self):
        # Отступ 8 пробелов
        logger.info("Обработан GET-запрос к /api/webhook")
        self.send_response(200); self.send_header('Content-type', 'text/plain'); self.end_headers()
        self.wfile.write(b"Bot OK (Simple Syrup Heart Version)"); return