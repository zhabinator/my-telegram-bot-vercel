# -*- coding: utf-8 -*-
import os
import asyncio
import json
import logging
import random # Оставляем для случайного выбора

# Убрали неиспользуемые импорты
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
    level=logging.INFO # INFO для продакшена
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

# --- Ключ Telegram ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
if not TELEGRAM_TOKEN:
    logger.critical("Переменная окружения TELEGRAM_TOKEN не установлена!")

# --- Список поздравлений ---
congratulations_list = [
    "Будть всегда very sugar🎉", "Ты - ловушка для мужского Вау! 💖", "Главная статья в кодексе красоты 🥳",
    "Ты делаешь аппетит приятнее ✨", "Ароматного дня, миледи🥰", "Рядом с вами не хочется моргать🥰",
    "Если красота спасет мир, то вся надежда только на тебя!🥰", "Целуем тот день, когда ты родилась!💖",
    "Море удачи и дачи у моря! 💖",
]

# --- Список URL картинок ---
image_urls = [
    "https://i.imgur.com/P14dISY.jpeg", "https://i.imgur.com/SrFv5sw.jpeg", "https://i.imgur.com/UjL4C4Q.jpeg",
    "https://i.imgur.com/exIooZ0.jpeg", "https://i.imgur.com/Hqe3MOI.jpeg", "https://i.imgur.com/xEsRHUU.jpeg"
]
if not image_urls: logger.warning("Список image_urls пуст!")

# --- ID Аудиофайла ---
HAPPY_BIRTHDAY_AUDIO_ID = "CQACAgIAAxkBAAEeFGVoDgLIaXacb0EQl_xL-M7bDs5ENwACwnAAAp1ncEhC4mDMqXl-wjYE" # ВАШ ПОСЛЕДНИЙ ID

# --- Клавиатура (ПРОВЕРЕНЫ СКОБКИ) ---
reply_keyboard = [ # Открыли основной список
    [KeyboardButton("Полить сердечко сиропом ❤️"), KeyboardButton("Сделай красиво ✨")], # Первый ряд, скобки парные
    [KeyboardButton("Хеппи бездей 🎂")] # Второй ряд, скобки парные
] # Закрыли основной список
# Вызов ReplyKeyboardMarkup, проверяем скобки: одна открывающая, одна закрывающая. Все параметры через запятую.
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)
# ---------------------------------------

# --- Обработчики ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет приветствие и показывает клавиатуру."""
    # Отступ 4 пробела
    logger.info(f"Команда /start от user_id: {update.effective_user.id}")
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.mention_html()}! Выбирай!",
        parse_mode='HTML',
        reply_markup=markup
    )

async def syrup_heart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет СЛУЧАЙНОЕ 'сиропное' сообщение."""
    # Отступ 4 пробела
    user_id = update.effective_user.id
    logger.info(f"Нажата кнопка 'Полить сердечко сиропом' от user_id: {user_id}")
    try:
        # Отступ 8 пробелов
        if not congratulations_list:
             # Отступ 12 пробелов
             logger.warning("Список congratulations_list пуст!")
             await update.message.reply_text("Извини, поздравления закончились.", reply_markup=markup)
             return
        # Отступ 8 пробелов
        message = random.choice(congratulations_list)
        await update.message.reply_text(message, reply_markup=markup)
        logger.info(f"Отправлено случайное 'сиропное' сообщение для user_id: {user_id}")
    # Отступ 4 пробела
    except Exception as e:
        # Отступ 8 пробелов
        logger.error(f"Ошибка в syrup_heart_handler для user_id: {user_id}: {e}", exc_info=True)
        try: await update.message.reply_text("Ой, не получилось полить сиропом!", reply_markup=markup)
        except Exception as send_err: logger.error(f"Не удалось отправить сообщение об ошибке: {send_err}")

async def beauty_image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет СЛУЧАЙНУЮ картинку из списка."""
    # Отступ 4 пробела
    user_id = update.effective_user.id
    logger.info(f"Нажата кнопка 'Сделай красиво' от user_id: {user_id}")
    # Отступ 4 пробела
    if not image_urls:
        # Отступ 8 пробелов
        logger.error(f"Список image_urls пуст для user_id: {user_id}")
        await update.message.reply_text("Извините, красивые картинки сейчас не загружены.", reply_markup=markup)
        return
    # Отступ 4 пробела
    try:
        # Отступ 8 пробелов
        image_url = random.choice(image_urls)
        logger.info(f"Выбран случайный URL картинки: {image_url} для user_id: {user_id}")
        await update.message.reply_photo(
            photo=image_url, caption="Лови красоту! ✨", reply_markup=markup
            )
        logger.info(f"Случайная картинка успешно отправлена для user_id: {user_id}")
    # Отступ 4 пробела
    except Exception as e:
        # Отступ 8 пробелов
        logger.error(f"Ошибка при отправке фото для user_id: {user_id}: {e}", exc_info=True)
        try: await update.message.reply_text("Ой, не получилось отправить картинку!", reply_markup=markup)
        except Exception as send_err: logger.error(f"Не удалось отправить сообщение об ошибке отправки фото: {send_err}")

async def happy_birthday_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет аудиофайл по file_id при нажатии кнопки."""
    # Отступ 4 пробела
    user_id = update.effective_user.id
    logger.info(f"Нажата кнопка 'Хеппи бездей' от user_id: {user_id}")
    if not HAPPY_BIRTHDAY_AUDIO_ID:
        # Отступ 8 пробелов
        logger.error("HAPPY_BIRTHDAY_AUDIO_ID не задан в коде!")
        await update.message.reply_text("Извини, файл поздравления сейчас недоступен.", reply_markup=markup)
        return
    # Отступ 4 пробела
    try:
        # Отступ 8 пробелов
        logger.info(f"Отправка аудио с file_id: {HAPPY_BIRTHDAY_AUDIO_ID} для user_id: {user_id}")
        await update.message.reply_audio(audio=HAPPY_BIRTHDAY_AUDIO_ID, caption="С Днем Рождения! 🎉", reply_markup=markup)
        logger.info(f"Аудио 'Хеппи бездей' успешно отправлено user_id: {user_id}")
    # Отступ 4 пробела
    except Exception as e:
        # Отступ 8 пробелов
        logger.error(f"Ошибка при отправке аудио 'Хеппи бездей' для user_id: {user_id}: {e}", exc_info=True)
        try: await update.message.reply_text("Не получилось отправить поздравление. Попробуй еще раз!", reply_markup=markup)
        except Exception as send_err: logger.error(f"Не удалось отправить сообщение об ошибке отправки аудио HB: {send_err}")


# --- Обработка обновления ---
async def process_one_update(update_data):
    # Отступ 4 пробела
    if not TELEGRAM_TOKEN: logger.error("Нет токена!"); return
    # Отступ 4 пробела
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    # Отступ 4 пробела
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^Полить сердечко сиропом ❤️$'), syrup_heart_handler))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^Сделай красиво ✨$'), beauty_image_handler))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^Хеппи бездей 🎂$'), happy_birthday_handler))
    # Отступ 4 пробела
    logger.info("Обработчики (start, syrup(random), beauty(random), hb) добавлены.")
    try:
        # Отступ 8 пробелов
        logger.debug("Init app...")
        await application.initialize()
        update = Update.de_json(update_data, application.bot)
        if update.message: logger.info(f"Msg rcvd: u={update.effective_user.id}, t='{update.message.text}'")
        else: logger.info(f"Update rcvd: {update}")
        logger.debug("Processing update...")
        await application.process_update(update)
        logger.debug("Shutdown app...")
        await application.shutdown()
    # Отступ 4 пробела
    except Exception as e:
        # Отступ 8 пробелов
        logger.error(f"Critical error: {e}", exc_info=True)
        if application.initialized:
             try: await application.shutdown()
             except Exception as shutdown_e: logger.error(f"Ошибка при shutdown после ошибки: {shutdown_e}")

# --- Точка входа Vercel (стандартная) ---
class handler(BaseHTTPRequestHandler):
    # Отступ 4 пробела
    def log_message(self, format, *args): logger.info("%s - %s" % (self.address_string(), format % args))
    # Отступ 4 пробела
    def do_POST(self):
        # Отступ 8 пробелов
        logger.info("!!! Вход в do_POST !!!")
        if not TELEGRAM_TOKEN: logger.error("POST: Токен не найден"); self.send_response(500); self.end_headers(); self.wfile.write(b"Bot token not configured"); return
        try:
            # Отступ 12 пробелов
            content_len = int(self.headers.get('Content-Length', 0))
            if content_len == 0: logger.warning("POST: Пустое тело"); self.send_response(400); self.end_headers(); self.wfile.write(b"Empty body"); return
            body_bytes = self.rfile.read(content_len)
            logger.debug(f"POST: Тело: {body_bytes[:200]}...")
            body_json = json.loads(body_bytes.decode('utf-8'))
            logger.info("POST: JSON получен")
            asyncio.run(process_one_update(body_json))
            self.send_response(200); self.send_header('Content-type', 'text/plain'); self.end_headers(); self.wfile.write(b"OK")
            logger.info("POST: Ответ 200 OK")
        # Отступ 8 пробелов
        except json.JSONDecodeError as e: logger.error("POST: Ошибка JSON", exc_info=True); self.send_response(400); self.end_headers(); self.wfile.write(b"Invalid JSON"); return
        except Exception as e: logger.error(f"POST: Ошибка в do_POST: {e}", exc_info=True); self.send_response(500); self.end_headers(); self.wfile.write(b"Internal Error"); return
    # Отступ 4 пробела
    def do_GET(self):
        # Отступ 8 пробелов
        logger.info("GET /api/webhook")
        self.send_response(200); self.send_header('Content-type', 'text/plain'); self.end_headers()
        self.wfile.write(b"Bot OK (Random Syrup/Image + HB Audio Version)"); return