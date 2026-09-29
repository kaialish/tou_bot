import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from src.config import BOT_TOKEN
from src.database import init_db
from src.handlers import main_router
from src.services import start_scheduler

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
dp.include_router(main_router)

# Глобальная переменная для хранения экземпляра планировщика
scheduler_instance = None


async def main():
    global scheduler_instance

    init_db()

    # Запускаем планировщик для уведомлений об окончании пар
    scheduler_instance = start_scheduler(bot)

    await bot.set_my_commands([
        BotCommand(command="start", description="Перезапустить бота / Авторизация"),
        BotCommand(command="admin", description="Панель администратора"),
    ])
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
