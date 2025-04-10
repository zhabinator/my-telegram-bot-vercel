# -*- coding: utf-8 -*-
import os
import asyncio
import json
import logging
from typing import List # Для типизации списков

# --- НОВЫЕ ИМПОРТЫ ---
from vercel_kv import kv # Клиент для Vercel KV
# --------------------

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
logging.getLogger("vercel_kv").setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

# --- Ключ Telegram ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
if not TELEGRAM_TOKEN:
    logger.critical("Переменная окружения TELEGRAM_TOKEN не установлена!")

# --- Список поздравлений ---
congratulations_list: List[str] = [
    "Будть всегда very sugar🎉",
    "Ты - ловушка для мужского Вау! 💖",
    "Главная статья в кодексе красоты 🥳",
    "Ты делаешь аппетит приятнее ✨",
    "Ароматного дня, миледи🥰",
    "Рядом с вами не хочется моргать🥰",
    "Если красота спасет мир, то вся надежда только на тебя!🥰",
    "Целуем тот день, когда ты родилась!💖",
    "Море удачи и дачи у моря! 💖",
]

# --- Список URL картинок ---
# ЗАМЕНИТЕ НА СВОИ РЕАЛЬНЫЕ ПРЯМЫЕ ССЫЛКИ!
image_urls: List[str] = [
    "https://i.imgur.com/P14dISY.jpeg",
    "https://i.imgur.com/SrFv5sw.jpeg",
    "https://i.imgur.com/xEsRHUU.jpeg",
    "https://i.imgur.com/Hqe3MOI.jpeg",
    "https://i.imgur.com/WkdZRkw.jpeg" # Пример 3 (другой)
    # Добавьте больше ваших ссылок
]
if not image_urls:
     logger.warning("Список image_urls пуст! Картинки не будут отправляться.")
     # Можно добавить запасной вариант или оставить пустым

# --- ID Вашего Аудиофайла ---
HAPPY_BIRTHDAY_AUDIO_ID = "CQACAgIAAxkBAAEd2Z9n99j8nLv08edj8YC2UjLcN_AlNQAC1nEAAm2gwEuxk0AF1ieRlDYE" # Вставили ваш ID

# --- Обновленная Клавиатура ---
reply_keyboard = [
    [KeyboardButton("Полить сердечко сиропом ❤️"), KeyboardButton("Сделай красиво ✨")],
    [KeyboardButton("Хеппи бездей 🎂")] # Добавили кнопку "Хеппи бездей"
]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)

# --- Вспомогательная функция для получения следующего элемента из списка через KV ---
async def get_next_item(user_id: int, list_key: str, item_list: List[str]) -> str:
    """
    Получает следующий индекс из KV, возвращает элемент и сохраняет новый индекс.
    :param user_id: ID пользователя Telegram.
    :param list_key: Уникальный ключ для этого списка (напр., 'syrup', 'beauty_img').
    :param item_list: Список элементов (сообщений или URL).
    :return: Следующий элемент из списка.
    """
    if not item_list:
        logger.warning(f"Список для ключа '{list_key}' пуст.")
        return "Список пуст." # Возвращаем сообщение об ошибке или пустую строку

    kv_key = f"next_idx:{user_id}:{list_key}" # Немного изменил формат ключа
    logger.debug(f"KV ключ для получения индекса: {kv_key}")
    current_index: int = 0
    try:
        stored_value = await kv.get(kv_key)
        if isinstance(stored_value, int):
            current_index = stored_value
        # Добавим проверку на строку, на всякий случай
        elif isinstance(stored_value, str) and stored_value.isdigit():
             current_index = int(stored_value)
        else:
            # Если ничего нет или не число, начинаем с 0
            logger.info(f"Индекс для {kv_key} не найден или не является числом ({stored_value}), начинаем с 0.")
            current_index = 0

        # Проверка на выход за пределы списка
        if not (0 <= current_index < len(item_list)):
            logger.warning(f"Сохраненный индекс {current_index} вне диапазона для {kv_key}. Сброс на 0.")
            current_index = 0

    except Exception as e:
        logger.error(f"Ошибка чтения из Vercel KV для {kv_key}: {e}", exc_info=True)
        current_index = 0 # Начинаем с 0 в случае ошибки чтения

    item_to_return = item_list[current_index]
    next_index = (current_index + 1) % len(item_list) # Вычисляем следующий индекс с зацикливанием

    try:
        await kv.set(kv_key, next_index) # Сохраняем СЛЕДУЮЩИЙ индекс
        logger.info(f"Сохранен следующий индекс {next_index} для {kv_key}")
    except Exception as e:
        logger.error(f"Ошибка записи в Vercel KV для {kv_key}: {e}", exc_info=True)
        # Не критично для отправки текущего элемента

    return item_to_return


# --- Обработчики ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет приветствие и показывает обновленную клавиатуру."""
    logger.info(f"Команда /start от user_id: {update.effective_user.id}")
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.mention_html()}! Выбирай!", # Обновили приветствие
        parse_mode='HTML',
        reply_markup=markup
    )

async def syrup_heart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет СЛЕДУЮЩЕЕ 'сиропное' сообщение по порядку."""
    user_id = update.effective_user.id
    logger.info(f"Нажата кнопка 'Полить сердечко сиропом' от user_id: {user_id}")
    try:
        message = await get_next_item(user_id, "syrup", congratulations_list) # Используем новую функцию
        await update.message.reply_text(message, reply_markup=markup)
        logger.info(f"Отправлено 'сиропное' сообщение для user_id: {user_id}")
    except Exception as e:
        logger.error(f"Ошибка в syrup_heart_handler для user_id: {user_id}: {e}", exc_info=True)
        try: await update.message.reply_text("Ой, не получилось полить сиропом!", reply_markup=markup)
        except Exception as send_err: logger.error(f"Не удалось отправить сообщение об ошибке: {send_err}")

async def beauty_image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет СЛЕДУЮЩУЮ картинку из списка по порядку."""
    user_id = update.effective_user.id
    logger.info(f"Нажата кнопка 'Сделай красиво' от user_id: {user_id}")

    if not image_urls:
        logger.error(f"Список image_urls пуст для user_id: {user_id}")
        await update.message.reply_text("Извините, красивые картинки сейчас не загружены.", reply_markup=markup)
        return

    try:
        image_url = await get_next_item(user_id, "beauty_img", image_urls) # Используем новую функцию
        logger.info(f"Выбран URL картинки: {image_url} для user_id: {user_id}")

        await update.message.reply_photo(
            photo=image_url,
            caption="Лови красоту! ✨",
            reply_markup=markup
            )
        logger.info(f"Картинка успешно отправлена для user_id: {user_id}")

    except Exception as e:
        logger.error(f"Ошибка при отправке фото для user_id: {user_id}: {e}", exc_info=True)
        try: await update.message.reply_text("Ой, не получилось отправить картинку!", reply_markup=markup)
        except Exception as send_err: logger.error(f"Не удалось отправить сообщение об ошибке отправки фото: {send_err}")

# --- НОВЫЙ Обработчик для кнопки "Хеппи бездей" ---
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
# --- КОНЕЦ НОВОГО Обработчика ---


# --- Обработка обновления ---
async def process_one_update(update_data):
    if not TELEGRAM_TOKEN:
        logger.error("Токен не найден при обработке обновления!")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # --- Добавляем ВСЕ нужные обработчики ---
    application.add_handler(CommandHandler("start", start))
    # Обработчик для кнопки "Полить сердечко сиропом ❤️"
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^Полить сердечко сиропом ❤️$'), syrup_heart_handler))
    # Обработчик для кнопки "Сделай красиво ✨"
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^Сделай красиво ✨$'), beauty_image_handler))
    # Обработчик для кнопки "Хеппи бездей 🎂" (ВАЖНО: убедитесь, что Regex точный!)
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^Хеппи бездей 🎂$'), happy_birthday_handler))

    logger.info("Обработчики (start, syrup, beauty, hb) добавлены.")
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


# --- Точка входа Vercel (стандартная, без изменений) ---
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
        self.wfile.write(b"Bot OK (Sequential Messages/Pictures + HB Audio Version)"); return # Обновили текст