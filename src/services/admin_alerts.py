import logging
from datetime import datetime
from aiogram import Bot
from src.config import ADMIN_IDS

logger = logging.getLogger(__name__)

# Состояние портала ToU в памяти, чтобы избежать спама админу при каждом сбое
_portal_down_reported: bool = False


async def notify_admins(bot: Bot, text: str) -> None:
    """Безопасно рассылает служебное сообщение всем администраторам."""
    if not ADMIN_IDS:
        return

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=text, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Не удалось отправить уведомление админу {admin_id}: {e}")


async def notify_admin_startup(bot: Bot, user_count: int) -> None:
    """Уведомление администраторам о запуске бота."""
    now_str = datetime.now().strftime("%d.%m.%Y в %H:%M:%S")
    text = (
        "🟢 <b>ToU Bot успешно запущен!</b>\n\n"
        f"🕒 Время запуска: <code>{now_str}</code>\n"
        f"⚡ СУБД: <b>SQLite (aiosqlite, Async)</b>\n"
        f"👥 Зарегистрировано студентов: <b>{user_count}</b>\n"
        "🚀 Система мониторинга и планировщик активны."
    )
    await notify_admins(bot, text)


async def notify_admin_shutdown(bot: Bot) -> None:
    """Уведомление администраторам об остановке бота."""
    now_str = datetime.now().strftime("%d.%m.%Y в %H:%M:%S")
    text = (
        "🔴 <b>ToU Bot останавливается...</b>\n\n"
        f"🕒 Время остановки: <code>{now_str}</code>\n"
        "💤 Все сессии корректно закрыты."
    )
    await notify_admins(bot, text)


async def notify_portal_incident(bot: Bot, is_down: bool, reason: str = "") -> None:
    """
    Отправляет админам алерт о падении или восстановлении портала ToU.
    Использует дедупликацию, чтобы не спамить при каждом запросе студента.
    """
    global _portal_down_reported
    now_str = datetime.now().strftime("%d.%m.%Y в %H:%M")

    if is_down and not _portal_down_reported:
        _portal_down_reported = True
        text = (
            "🚨 <b>Алерт: Портал ToU недоступен!</b>\n\n"
            f"🕒 Время: <code>{now_str}</code>\n"
            f"⚠️ Причина: <code>{reason or 'Сервер ToU не отвечает'}</code>\n\n"
            "ℹ️ <i>Студенты автоматически переводятся на резервный оффлайн-кэш.</i>"
        )
        await notify_admins(bot, text)

    elif not is_down and _portal_down_reported:
        _portal_down_reported = False
        text = (
            "✅ <b>Портал ToU снова в сети!</b>\n\n"
            f"🕒 Время: <code>{now_str}</code>\n"
            "🎉 Связь с сайтом университета полностью восстановлена."
        )
        await notify_admins(bot, text)


async def notify_admin_error(bot: Bot, error: Exception, context_info: str = "") -> None:
    """Отправляет администраторам уведомление о критической ошибке или сбое хендлера."""
    now_str = datetime.now().strftime("%d.%m.%Y в %H:%M:%S")
    error_type = type(error).__name__
    error_msg = str(error)[:300]

    text = (
        "🚨 <b>Исключение в работе бота!</b>\n\n"
        f"🕒 Время: <code>{now_str}</code>\n"
        f"📌 Контекст: <code>{context_info or 'Global Error'}</code>\n"
        f"⚠️ Ошибка: <b>{error_type}</b>\n"
        f"<code>{error_msg}</code>"
    )
    await notify_admins(bot, text)
