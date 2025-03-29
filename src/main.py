import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, ChatMemberUpdated

from dotenv import load_dotenv
import os

from bot import BotService
from config import settings
from models.bot_models import BotConfig
from scheduler.reminder import schedule_reminders
from services.openai_service import OpenAIClient
from services.data_service import Storage
from services.user_repository import UserRepository
from utils.logger import setup_logger

# Настройка логирования
setup_logger("main")
import logging
logger = logging.getLogger("main")

# Загрузка переменных окружения
load_dotenv()
TELEGRAM_TOKEN = settings.TELEGRAM_TOKEN
OPENAI_KEY = settings.OPENAI_API_KEY

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN не задан")

# Telegram Bot
bot = Bot(
    token=TELEGRAM_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Загрузка данных
storage = Storage("data.json")
loaded = storage.load()
config = loaded["config"]
if isinstance(config, dict):
    config = BotConfig.from_dict(config)
users = UserRepository(loaded["user_data"])

# Инициализация OpenAI
openai_client = None
if OPENAI_KEY:
    try:
        openai_client = OpenAIClient(api_key=OPENAI_KEY)
        logger.info("OpenAI подключен")
    except Exception as e:
        logger.warning(f"OpenAI не доступен: {e}")

# Инициализация сервиса
service = BotService(config, users, storage, openai_client)


# === Команды ===

@dp.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer("Привет! Отправь мне количество отжиманий или используй /help.")

@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "📋 Команды:\n"
        "/mystats — ваша личная статистика\n"
        "/stats — статистика всей группы\n"
        "/changemydailystats N — изменить количество за сегодня\n"
        "/setgroup — назначить эту группу основной\n"
        "/config — показать текущую конфигурацию\n\n"
        "Пример отчёта: 25+25+25=75"
    )

@dp.message(Command("mystats"))
async def mystats_cmd(message: Message):
    await service.handle_mystats(message)

@dp.message(Command("stats"))
async def stats_cmd(message: Message):
    await service.handle_stats(message)

@dp.message(Command("changemydailystats"))
async def change_stat_cmd(message: Message):
    await service.handle_change_stat(message)

@dp.message(Command("setgroup"))
async def setgroup_cmd(message: Message):
    await service.handle_setgroup(message)

@dp.message(Command("config"))
async def config_cmd(message: Message):
    await service.handle_config(message)

@dp.message(Command("adminstats"))
async def adminstats_cmd(message: Message):
    await service.handle_adminstats(message, bot)


# === Приветствие новых участников ===

@dp.chat_member()
async def on_new_chat_member(event: ChatMemberUpdated):
    if event.new_chat_member.status == "member":
        fake_message = Message(
            message_id=0,
            date=event.date,
            chat=event.chat,
            from_user=event.new_chat_member.user,
            message_thread_id=None,
            text="",
            new_chat_members=[event.new_chat_member.user],
        )
        await service.handle_welcome_new(fake_message)


# === Обработка всех сообщений ===

@dp.message()
async def any_text(message: Message):
    await service.handle_message(message)


# === Запуск ===

async def main():
    if not os.path.exists("data.json"):
        storage.save(config, users.users)

    schedule_reminders(bot, service)

    logger.info("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
