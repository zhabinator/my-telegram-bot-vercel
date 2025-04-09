# -*- coding: utf-8 -*-
import os
import asyncio
import json
import logging
import random # Для выбора случайной картинки

from http.server import BaseHTTPRequestHandler

# Убрали aiohttp, он больше не нужен для этой версии
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
if not TELEGRAM_TOKEN:
    logger.critical("Переменная окружения TELEGRAM_TOKEN не установлена!")

# --- ВАШ СПИСОК URL-АДРЕСОВ КАРТИНОК ---
# ЗАМЕНИТЕ ЭТИ ССЫЛКИ НА СВОИ РЕАЛЬНЫЕ ПРЯМЫЕ ССЫЛКИ НА КАРТИНКИ!
image_urls = [
    "https://i.imgur.com/SrFv5sw.jpeg", # Пример 1
    "https://i.imgur.com/AR8Bsjv.jpeg", # Пример 2
        # Добавьте сюда столько URL, сколько хотите
]
# Убедитесь, что ссылки рабочие и картинки доступны публично!
if not image_urls or image_urls[0].startswith("https://example.com"):
     logger.warning("Список image_urls пуст или содержит примеры! Картинки не будут отправляться.")
     # Можно добавить одну картинку по умолчанию, если список пуст
     # image_urls = ["https://picsum.photos/500/300"] # Как запасной вариант

# --- Новая Клавиатура ---
reply_keyboard = [
    [KeyboardButton("Сделай красиво ✨")] # Новая кнопка
]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)

# --- Обработчики ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет приветствие и показывает кнопку."""
    logger.info(f"Команда /start от user_id: {update.effective_user.id}")
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.mention_html()}! Хочешь красоту? ✨",
        parse_mode='HTML',
        reply_markup=markup
    )

async def send_beautiful_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет случайную картинку из списка при нажатии кнопки."""
    logger.info(f"Нажата кнопка 'Сделай красиво' от user_id: {update.effective_user.id}")

    if not image_urls or image_urls[0].startswith("https://example.com"):
        logger.error(f"Список image_urls пуст или не настроен для user_id: {update.effective_user.id}")
        await update.message.reply_text("Извините, красивые картинки сейчас не загружены.", reply_markup=markup)
        return

    try:
        # Выбираем случайный URL из списка
        random_image_url = random.choice(image_urls)
        logger.info(f"Выбран URL картинки: {random_image_url} для user_id: {update.effective_user.id}")

        # Отправляем фото по URL
        await update.message.reply_photo(
            photo=random_image_url,
            caption="Лови красоту! ✨", # Необязательная подпись
            reply_markup=markup # Возвращаем клавиатуру
            )
        logger.info(f"Картинка успешно отправлена для user_id: {update.effective_user.id}")

    except Exception as e:
        logger.error(f"Ошибка при отправке фото для user_id: {update.effective_user.id}: {e}", exc_info=True)
        try:
            await update.message.reply_text("Ой, не получилось отправить картинку. Попробуй еще раз!", reply_markup=markup)
        except Exception as send_err:
            logger.error(f"Не удалось отправить сообщение об ошибке отправки фото: {send_err}")


# --- Обработка обновления ---
async def process_one_update(update_data):
    if not TELEGRAM_TOKEN:
        logger.error("Токен не найден при обработке обновления!")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    # Обработчик для НОВОЙ кнопки
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^Сделай красиво ✨$'), send_beautiful_image))

    logger.info("Обработчики (start, кнопка 'Сделай красиво') добавлены.")
    try:
        logger.debug(f"Инициализация приложения для update_id: {update_data.get('update_id')}")
        await application.initialize()
        update = Update.de_json(update_data, application.bot)

        if update.message:
            logger.info(f"Получено сообщение: chat_id={update.message.chat.id}, user_id={update.effective_user.id}, text='{update.message.text}'")
        else:
            logger.info(f"Получен другой тип обновления: {update}")

        logger.debug(f"Запуск process_update для update_id: {update.update_id}")
        await application.process_update(update)
        logger.debug(f"Завершение shutdown для update_id: {update.update_id}")
        await application.shutdown()
    except Exception as e:
        logger.error(f"Критическая ошибка при обработке обновления {update_data.get('update_id', 'N/A')}: {e}", exc_info=True)
        if application.initialized:
             try: await application.shutdown()
             except Exception as shutdown_e: logger.error(f"Ошибка при shutdown после ошибки: {shutdown_e}", exc_info=True)


# --- Точка входа Vercel (стандартная) ---
class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logger.info("%s - %s" % (self.address_string(), format % args))
    def do_POST(self):
        logger.info("!!! Вход в do_POST !!!")
        if not TELEGRAM_TOKEN:
            logger.error("POST: Токен не найден (проверка в do_POST)")
            self.send_response(500); self.end_headers(); self.wfile.write(b"Bot token not configured"); return
        try:
            content_len = int(self.headers.get('Content-Length', 0))
            if content_len == 0:
                 logger.warning("POST: Пустое тело запроса")
                 self.send_response(400); self.end_headers(); self.wfile.write(b"Empty request body"); return
            body_bytes = self.rfile.read(content_len)
            logger.debug(f"POST: Получено тело запроса (байты): {body_bytes[:200]}...")
            body_json = json.loads(body_bytes.decode('utf-8'))
            logger.info("POST: JSON получен и декодирован")
            asyncio.run(process_one_update(body_json))
            self.send_response(200); self.send_header('Content-type', 'text/plain'); self.end_headers(); self.wfile.write(b"OK")
            logger.info("POST: Ответ 200 OK отправлен Telegram.")
        except json.JSONDecodeError as e:
            logger.error("POST: Ошибка декодирования JSON.", exc_info=True)
            self.send_response(400); self.end_headers(); self.wfile.write(b"Invalid JSON"); return
        except Exception as e:
            logger.error(f"POST: Необработанная ошибка в do_POST: {e}", exc_info=True)
            self.send_response(500); self.end_headers(); self.wfile.write(b"Internal Server Error"); return
    def do_GET(self):
        logger.info("Обработан GET-запрос к /api/webhook")
        self.send_response(200); self.send_header('Content-type', 'text/plain'); self.end_headers()
        self.wfile.write(b"Bot OK (Beautiful Picture Version)"); return # Изменил текст ответа