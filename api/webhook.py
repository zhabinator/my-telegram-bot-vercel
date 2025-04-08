# -*- coding: utf-8 -*-
import os
import asyncio
import json
import logging
import aiohttp # Для асинхронных HTTP-запросов

from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

# Импорты Telegram: Добавляем KeyboardButton и ReplyKeyboardMarkup
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO # Можно вернуть INFO, если DEBUG больше не нужен для отладки
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

# --- Получаем ключ Telegram ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
# --- Ключ OWM_API_KEY не нужен, если нет погоды ---
# --------------------------------------------

# --- Создаем клавиатуру ---
reply_keyboard = [
    [KeyboardButton("Шутка 🎲"), KeyboardButton("Цитата 📜")],
]
# Создаем объект клавиатуры для отправки
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
# -------------------------


# --- Обработчики команд ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ответ на команду /start - отправляет клавиатуру"""
    # Отступ 4 пробела
    user_name = update.effective_user.first_name or "User"
    logger.info(f"Вызвана /start пользователем {user_name}")
    # Отправляем приветствие и клавиатуру
    await update.message.reply_text(
        f'Привет, {user_name}! Нажми кнопку, чтобы получить шутку или цитату.',
        reply_markup=markup # Прикрепляем клавиатуру к сообщению
    )

async def joke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет случайную шутку (вызывается командой /joke ИЛИ кнопкой)"""
    # Отступ 4 пробела
    # Определяем, как была вызвана функция (для лога)
    is_command = hasattr(update.message, 'text') and update.message.text == "/joke"
    log_prefix = "/joke" if is_command else f"Кнопка '{update.message.text if hasattr(update.message, 'text') else 'N/A'}'"
    logger.info(f"{log_prefix}: Запрос шутки...")

    joke_api_url = "https://official-joke-api.appspot.com/random_joke"
    try:
        # Отступ 8 пробелов
        async with aiohttp.ClientSession() as session:
            # Отступ 12 пробелов
            async with session.get(joke_api_url) as response:
                # Отступ 16 пробелов
                response.raise_for_status()
                data = await response.json()
                logger.info(f"{log_prefix}: Получен ответ от API шуток: {data}")

        # Отступ 8 пробелов
        setup = data.get("setup")
        punchline = data.get("punchline")

        if setup and punchline:
            # Отступ 12 пробелов
            joke_text = f"{setup}\n\n{punchline}"
            await update.message.reply_text(joke_text, reply_markup=markup)
        else:
            # Отступ 12 пробелов
            logger.error(f"{log_prefix}: Не удалось извлечь setup/punchline из ответа: {data}")
            await update.message.reply_text("Необычный формат шутки пришел. Попробуй еще раз!", reply_markup=markup)

    # Отступ 4 пробела
    except aiohttp.ClientError as e:
        # Отступ 8 пробелов
        logger.error(f"{log_prefix}: Ошибка сети при запросе шутки: {e}", exc_info=True)
        await update.message.reply_text("Не смог связаться с сервером шуток. Попробуй позже.", reply_markup=markup)
    # Отступ 4 пробела
    except json.JSONDecodeError as e:
         # Отступ 8 пробелов
         logger.error(f"{log_prefix}: Ошибка декодирования JSON от API шуток: {e}", exc_info=True)
         await update.message.reply_text("Сервер шуток ответил что-то непонятное. Попробуй позже.", reply_markup=markup)
    # Отступ 4 пробела
    except Exception as e:
        # Отступ 8 пробелов
        logger.error(f"{log_prefix}: Непредвиденная ошибка при получении шутки: {e}", exc_info=True)
        await update.message.reply_text("Ой, что-то пошло не так при поиске шутки. Попробуй позже.", reply_markup=markup)


# --- ФУНКЦИЯ ДЛЯ ЦИТАТ С ОТКЛЮЧЕНИЕМ ПРОВЕРКИ SSL ---
async def quote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет случайную цитату"""
    # Отступ 4 пробела
    logger.info(f"Нажата кнопка '{update.message.text if hasattr(update.message, 'text') else 'N/A'}'. Запрос цитаты...")
    quote_api_url = "https://api.quotable.io/random" # API для цитат
    try:
        # Отступ 8 пробелов
        async with aiohttp.ClientSession() as session:
            # Отступ 12 пробелов
            # --- !!! ИЗМЕНЕНИЕ ЗДЕСЬ: Добавлен ssl=False !!! ---
            async with session.get(quote_api_url, ssl=False) as response:
                # Отступ 16 пробелов
                response.raise_for_status() # Проверка на ошибки HTTP (4xx, 5xx)
                data = await response.json()
                logger.info(f"Цитата: Получен ответ от API цитат: {data}")

        # Отступ 8 пробелов
        content = data.get("content")
        author = data.get("author")

        if content and author:
            # Отступ 12 пробелов
            # Форматируем цитату
            quote_text = f'"{content}"\n\n— {author}'
            await update.message.reply_text(quote_text, reply_markup=markup) # Отправляем с клавиатурой
        else:
            # Отступ 12 пробелов
            logger.error(f"Цитата: Не удалось извлечь content/author из ответа: {data}")
            await update.message.reply_text("Не смог получить цитату в ожидаемом формате. Попробуй еще раз!", reply_markup=markup)

    # Отступ 4 пробела
    except aiohttp.ClientError as e: # Теперь этот блок не должен срабатывать из-за SSL, но оставим для других сетевых ошибок
        # Отступ 8 пробелов
        logger.error(f"Цитата: Ошибка сети при запросе цитаты: {e}", exc_info=True)
        await update.message.reply_text("Не смог связаться с сервером цитат (сетевая ошибка). Попробуй позже.", reply_markup=markup)
    # Отступ 4 пробела
    except json.JSONDecodeError as e:
         # Отступ 8 пробелов
         logger.error(f"Цитата: Ошибка декодирования JSON от API цитат: {e}", exc_info=True)
         await update.message.reply_text("Сервер цитат ответил что-то непонятное. Попробуй позже.", reply_markup=markup)
    # Отступ 4 пробела
    except Exception as e:
        # Отступ 8 пробелов
        logger.error(f"Цитата: Непредвиденная ошибка при получении цитаты: {e}", exc_info=True)
        await update.message.reply_text("Ой, что-то пошло не так при поиске цитаты. Попробуй позже.", reply_markup=markup)
# --- КОНЕЦ ФУНКЦИИ ЦИТАТЫ ---


# --- Функция обработки ОДНОГО обновления ---
async def process_one_update(update_data):
    # Отступ 4 пробела
    if not TELEGRAM_TOKEN:
        # Отступ 8 пробелов
        logger.error("Токен не найден в переменных окружения!")
        return
    # Отступ 4 пробела
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # --- РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ---
    # Отступ 4 пробела
    # 1. Обработчик команды /start
    application.add_handler(CommandHandler("start", start))
    # 2. Обработчик команды /joke (оставляем на всякий случай)
    application.add_handler(CommandHandler("joke", joke_command))
    # 3. Обработчик для НАЖАТИЯ КНОПКИ "Шутка 🎲"
    # Убедитесь, что текст в Regex ТОЧНО совпадает с тем, что приходит в логах Vercel
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^Шутка 🎲$'),
        joke_command
    ))
    # 4. Обработчик для НАЖАТИЯ КНОПКИ "Цитата 📜"
    # Убедитесь, что текст в Regex ТОЧНО совпадает с тем, что приходит в логах Vercel
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^Цитата 📜$'),
        quote_command
    ))
    # --------------------------------

    # Отступ 4 пробела
    logger.info("Обработчики для start, joke, кнопки 'Шутка', кнопки 'Цитата' добавлены.")
    try:
        # Отступ 8 пробелов
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
        await application.process_update(update)
        await application.shutdown()
    # Отступ 4 пробела
    except Exception as e:
        # Отступ 8 пробелов
        logger.error(f"Критическая ошибка при обработке обновления {update_data.get('update_id', 'N/A')}: {e}", exc_info=True)
        if application.initialized:
            # Отступ 12 пробелов
            try:
                await application.shutdown()
            except Exception as shutdown_e:
                logger.error(f"Ошибка при shutdown после критической ошибки: {shutdown_e}", exc_info=True)


# --- Точка входа для Vercel (остается без изменений) ---
class handler(BaseHTTPRequestHandler): # Начало класса, нет отступа

    # Отступ 4 пробела перед def log_message
    def log_message(self, format, *args):
          # Отступ 8 пробелов перед logger.info
          logger.info("%s - %s" % (self.address_string(), format%args))

    # Отступ 4 пробела перед def do_POST
    def do_POST(self):
        # Отступ 8 пробелов перед logger.info
        logger.info("!!! Вход в do_POST !!!")
        # Отступ 8 пробелов перед if not TELEGRAM_TOKEN:
        if not TELEGRAM_TOKEN:
            # Отступ 12 пробелов перед logger.error и далее внутри if
            logger.error("POST-запрос: Токен не загружен.")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Bot token not configured")
            return
        # Отступ 8 пробелов перед try
        try:
            # Отступ 12 пробелов перед content_len
            content_len = int(self.headers.get('Content-Length', 0))
            # Отступ 12 пробелов перед if content_len == 0:
            if content_len == 0:
                 # Отступ 16 пробелов перед logger.warning и далее внутри if
                 logger.warning("POST-запрос: Пустое тело.")
                 self.send_response(400)
                 self.end_headers()
                 self.wfile.write(b"Empty request body")
                 return
            # Отступ 12 пробелов перед body_bytes
            body_bytes = self.rfile.read(content_len)
            # Отступ 12 пробелов перед body_json
            body_json = json.loads(body_bytes.decode('utf-8'))
            # Отступ 12 пробелов перед logger.info
            logger.info("POST-запрос: JSON получен и декодирован.")
            # Отступ 12 пробелов перед asyncio.run
            asyncio.run(process_one_update(body_json))
            # Отступ 12 пробелов перед self.send_response
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")
            # Отступ 12 пробелов перед logger.info
            logger.info("POST-запрос: Ответ 200 OK отправлен.")
        # Отступ 8 пробелов перед except json.JSONDecodeError
        except json.JSONDecodeError:
            # Отступ 12 пробелов перед logger.error и далее внутри except
            logger.error("POST-запрос: Ошибка декодирования JSON.", exc_info=True)
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid JSON received")
            return
        # Отступ 8 пробелов перед except Exception
        except Exception as e:
            # Отступ 12 пробелов перед logger.error и далее внутри except
            logger.error(f"POST-запрос: Необработанная ошибка в do_POST: {e}", exc_info=True)
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Internal Server Error occurred")
            return

    # Отступ 4 пробела перед def do_GET
    def do_GET(self):
        # Отступ 8 пробелов перед logger.info
        logger.info("Обработан GET-запрос к /api/webhook")
        # Отступ 8 пробелов перед self.send_response
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Hello! Joke/Quote Bot webhook endpoint is active.") # Обновил текст
        return
# Конец класса handler