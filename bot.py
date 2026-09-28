import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from src.config import BOT_TOKEN
from src.database import init_db
from src.handlers import main_router

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.include_router(main_router)


async def main():
    init_db()
    await bot.set_my_commands([
        BotCommand(command="start", description="Перезапустить бота / Авторизация"),
        BotCommand(command="admin", description="Панель администратора"),
    ])
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())