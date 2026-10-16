import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, ErrorEvent

from src.config import BOT_TOKEN
from src.database import (
    init_db,
    get_all_user_ids,
    set_maintenance_status,
    is_maintenance_active,
)
from src.handlers import main_router
from src.services import (
    start_scheduler,
    notify_admin_startup,
    notify_admin_shutdown,
    notify_admin_error,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
dp.include_router(main_router)

# Глобальная переменная для хранения экземпляра планировщика
scheduler_instance = None

MAINTENANCE_TEXT = (
    "🔧 <b>Бот временно недоступен</b>\n\n"
    "Сейчас проводятся технические работы и обновление бота. "
    "Он скоро вернётся в строй! 🚀\n\n"
    "Спасибо за понимание 🙏"
)

RESUME_TEXT = (
    "🚀 <b>Бот снова в строю!</b>\n\n"
    "Технические работы успешно завершены, все функции восстановлены и работают в штатном режиме.\n\n"
    "Нажмите /start, чтобы открыть главное меню ✨"
)


@dp.error()
async def global_error_handler(event: ErrorEvent):
    """Глобальный перехватчик ошибок для логирования и отправки алертов администраторам."""
    logging.exception(f"Необработанное исключение: {event.exception}")
    try:
        user_info = "Системное событие"
        if event.update.message and event.update.message.from_user:
            u = event.update.message.from_user
            user_info = f"Пользователь {u.id} (@{u.username or 'нет_username'})"
        elif event.update.callback_query and event.update.callback_query.from_user:
            u = event.update.callback_query.from_user
            user_info = f"Callback от {u.id} (@{u.username or 'нет_username'}) [{event.update.callback_query.data}]"

        await notify_admin_error(bot, event.exception, context_info=user_info)
    except Exception as e:
        logging.error(f"Не удалось отправить алерт об ошибке админам: {e}")


async def broadcast_shutdown():
    """Рассылает уведомление о техническом обслуживании перед выключением."""
    user_ids = await get_all_user_ids()

    # Сначала уведомляем администраторов
    await notify_admin_shutdown(bot)

    if not user_ids:
        await set_maintenance_status(True)
        return

    logging.info(f"Рассылка уведомления об отключении {len(user_ids)} пользователям...")
    sent = 0
    for user_id in user_ids:
        try:
            await bot.send_message(chat_id=user_id, text=MAINTENANCE_TEXT, parse_mode="HTML")
            sent += 1
            await asyncio.sleep(0.05)  # Соблюдаем лимиты Telegram API
        except Exception:
            pass  # Игнорируем заблокировавших бота
    logging.info(f"Уведомление отправлено {sent} из {len(user_ids)} пользователей.")
    await set_maintenance_status(True)


async def broadcast_startup_resumed():
    """Если бот уходил на техническое обслуживание, уведомляет пользователей о возобновлении работы."""
    if not await is_maintenance_active():
        return

    user_ids = await get_all_user_ids()
    if not user_ids:
        await set_maintenance_status(False)
        return

    logging.info(f"Рассылка уведомления о возобновлении работы {len(user_ids)} пользователям...")
    sent = 0
    for user_id in user_ids:
        try:
            await bot.send_message(chat_id=user_id, text=RESUME_TEXT, parse_mode="HTML")
            sent += 1
            await asyncio.sleep(0.05)  # Соблюдаем лимиты Telegram API
        except Exception:
            pass
    logging.info(f"Уведомление о возобновлении отправлено {sent} из {len(user_ids)} пользователей.")
    await set_maintenance_status(False)


async def on_shutdown():
    """Выполняется при остановке бота: рассылка + остановка планировщика."""
    global scheduler_instance

    await broadcast_shutdown()

    if scheduler_instance and scheduler_instance.running:
        scheduler_instance.shutdown(wait=False)
        logging.info("Планировщик остановлен.")

    await bot.session.close()
    logging.info("Сессия бота закрыта.")


async def main():
    global scheduler_instance

    # Асинхронная инициализация SQLite (aiosqlite)
    await init_db()

    # Запускаем планировщик для уведомлений об окончании пар
    scheduler_instance = start_scheduler(bot)

    # Уведомляем администраторов о старте
    all_users = await get_all_user_ids()
    await notify_admin_startup(bot, len(all_users))

    # Если бот до этого уходил на техперерыв — уведомляем пользователей о возобновлении
    await broadcast_startup_resumed()

    await bot.set_my_commands([
        BotCommand(command="start", description="Главное меню / Авторизация"),
        BotCommand(command="admin", description="Панель администратора"),
    ])

    try:
        await dp.start_polling(bot)
    finally:
        await on_shutdown()


if __name__ == "__main__":
    asyncio.run(main())
