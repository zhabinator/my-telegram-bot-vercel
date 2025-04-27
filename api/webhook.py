# -*- coding: utf-8 -*-
import os
import asyncio
import json
import logging
import random

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
    level=logging.INFO # INFO достаточно, т.к. используем CRITICAL для ID
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

# --- ID Аудиофайла (Пока оставляем старый, вы его замените новым позже) ---
HAPPY_BIRTHDAY_AUDIO_ID = "CQACAgIAAxkBAAEeFGVoDgLIaXacb0EQl_xL-M7bDs5ENwACwnAAAp1ncEhC4mDMqXl-wjYE" # ЗАМЕНИТЕ ЭТО ПОЗЖЕ

# --- Клавиатура ---
reply_keyboard = [
    [KeyboardButton("Полить сердечко сиропом ❤️"), KeyboardButton("Сделай красиво ✨")],
    [KeyboardButton("Хеппи бездей 🎂")]
]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)

# --- Обработчики ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет приветствие и показывает клавиатуру."""
    logger.info(f"Команда /start от user_id: {update.effective_user.id}")
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.mention_html()}! Выбирай!",
        parse_mode='HTML',
        reply_markup=markup
    )

async def syrup_heart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет СЛУЧАЙНОЕ 'сиропное' сообщение."""
    user_id = update.effective_user.id
    logger.info(f"Нажата кнопка 'Полить сердечко сиропом' от user_id: {user_id}")
    try:
        if not congratulations_list:
             logger.warning("Список congratulations_list пуст!")
             await update.message.reply_text("Извини, поздравления закончились.", reply_markup=markup)
             return
        message = random.choice(congratulations_list)
        await update.message.reply_text(message, reply_markup=markup)
        logger.info(f"Отправлено случайное 'сиропное' сообщение для user_id: {user_id}")
    except Exception as e:
        logger.error(f"Ошибка в syrup_heart_handler для user_id: {user_id}: {e}", exc_info=True)
        try: await update.message.reply_text("Ой, не получилось полить сиропом!", reply_markup=markup)
        except Exception as send_err: logger.error(f"Не удалось отправить сообщение об ошибке: {send_err}")

async def beauty_image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет СЛУЧАЙНУЮ картинку из списка."""
    user_id = update.effective_user.id
    logger.info(f"Нажата кнопка 'Сделай красиво' от user_id: {user_id}")
    if not image_urls:
        logger.error(f"Список image_urls пуст для user_id: {user_id}")
        await update.message.reply_text("Извините, красивые картинки сейчас не загружены.", reply_markup=markup)
        return
    try:
        image_url = random.choice(image_urls)
        logger.info(f"Выбран случайный URL картинки: {image_url} для user_id: {user_id}")
        await update.message.reply_photo(
            photo=image_url, caption="Лови красоту! ✨", reply_markup=markup
            )
        logger.info(f"Случайная картинка успешно отправлена для user_id: {user_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке фото для user_id: {user_id}: {e}", exc_info=True)
        try: await update.message.reply_text("Ой, не получилось отправить картинку!", reply_markup=markup)
        except Exception as send_err: logger.error(f"Не удалось отправить сообщение об ошибке отправки фото: {send_err}")

async def happy_birthday_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет аудиофайл по file_id при нажатии кнопки."""
    user_id = update.effective_user.id
    logger.info(f"Нажата кнопка 'Хеппи бездей' от user_id: {user_id}")
    if not HAPPY_BIRTHDAY_AUDIO_ID:
        logger.error("HAPPY_BIRTHDAY_AUDIO_ID не задан в коде!")
        await update.message.reply_text("Извини, файл поздравления сейчас недоступен.", reply_markup=markup)
        return
    try:
        logger.info(f"Отправка аудио с file_id: {HAPPY_BIRTHDAY_AUDIO_ID} для user_id: {user_id}")
        await update.message.reply_audio(audio=HAPPY_BIRTHDAY_AUDIO_ID, caption="С Днем Рождения! 🎉", reply_markup=markup)
        logger.info(f"Аудио 'Хеппи бездей' успешно отправлено user_id: {user_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке аудио 'Хеппи бездей' для user_id: {user_id}: {e}", exc_info=True)
        try: await update.message.reply_text("Не получилось отправить поздравление. Попробуй еще раз!", reply_markup=markup)
        except Exception as send_err: logger.error(f"Не удалось отправить сообщение об ошибке отправки аудио HB: {send_err}")

# !!! ВРЕМЕННАЯ ФУНКЦИЯ ДЛЯ ЛОГГИРОВАНИЯ ID АУДИО !!!
async def log_received_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Логгирует file_id полученного аудио и отвечает пользователю."""
    if update.message and update.message.audio:
        audio = update.message.audio
        the_file_id = audio.file_id
        # Выводим в лог КРИТИЧЕСКИМ уровнем, чтобы точно заметить
        logger.critical(f"--- !!! ПОЛУЧЕН AUDIO FILE ID: {the_file_id} !!! ---")
        # Отвечаем пользователю, чтобы было видно и в чате
        await update.message.reply_text(f"Audio ID получен:\n\n`{the_file_id}`\n\nСкопируйте этот ID.", parse_mode='MarkdownV2')
    else:
        logger.warning("log_received_audio вызван для сообщения без аудио.")
# !!! КОНЕЦ ВРЕМЕННОЙ ФУНКЦИИ !!!


# --- Обработка обновления ---
async def process_one_update(update_data):
    if not TELEGRAM_TOKEN: logger.error("Нет токена!"); return
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # !!! ДОБАВЛЯЕМ ВРЕМЕННЫЙ ОБРАБОТЧИК АУДИО ПЕРВЫМ !!!
    application.add_handler(MessageHandler(filters.AUDIO, log_received_audio))
    # ---------------------------------------------

    # Добавляем остальные обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^Полить сердечко сиропом ❤️$'), syrup_heart_handler))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^Сделай красиво ✨$'), beauty_image_handler))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^Хеппи бездей 🎂$'), happy_birthday_handler))

    logger.info("Обработчики добавлены (ВКЛЮЧАЯ ЛОГ АУДИО).")
    try:
        logger.debug("Init app...")
        await application.initialize()
        update = Update.de_json(update_data, application.bot)
        if update.message: logger.info(f"Msg rcvd: u={update.effective_user.id}, t='{update.message.text}'")
        else: logger.info(f"Update rcvd: {update}")
        logger.debug("Processing update...")
        await application.process_update(update)
        logger.debug("Shutdown app...")
        await application.shutdown()
    except Exception as e: logger.error(f"Critical error: {e}", exc_info=True); # ... (обработка ошибки shutdown) ...

# --- Точка входа Vercel (стандартная) ---
class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): logger.info("%s - %s" % (self.address_string(), format % args))
    def do_POST(self): # ... (стандартный код do_POST) ...
        logger.info("!!! Вход в do_POST !!!")
        if not TELEGRAM_TOKEN: logger.error("POST: Токен не найден"); self.send_response(500); self.end_headers(); self.wfile.write(b"Bot token not configured"); return
        try:
            content_len = int(self.headers.get('Content-Length', 0))
            if content_len == 0: logger.warning("POST: Пустое тело"); self.send_response(400); self.end_headers(); self.wfile.write(b"Empty body"); return
            body_bytes = self.rfile.read(content_len)
            logger.debug(f"POST: Тело: {body_bytes[:200]}...")
            body_json = json.loads(body_bytes.decode('utf-8'))
            logger.info("POST: JSON получен")
            asyncio.run(process_one_update(body_json))
            self.send_response(200); self.send_header('Content-type', 'text/plain'); self.end_headers(); self.wfile.write(b"OK")
            logger.info("POST: Ответ 200 OK")
        except json.JSONDecodeError as e: logger.error("POST: Ошибка JSON", exc_info=True); self.send_response(400); self.end_headers(); self.wfile.write(b"Invalid JSON"); return
        except Exception as e: logger.error(f"POST: Ошибка в do_POST: {e}", exc_info=True); self.send_response(500); self.end_headers(); self.wfile.write(b"Internal Error"); return
    def do_GET(self): # ... (стандартный код do_GET) ...
        logger.info("GET /api/webhook")
        self.send_response(200); self.send_header('Content-type', 'text/plain'); self.end_headers()
        self.wfile.write(b"Bot OK (Audio ID Logging Active)"); return # Поменяли текст для GET