"""
Планировщик для отправки автоматических уведомлений об окончании пар.
Проверяет текущее время каждые 5 секунд и отправляет уведомления подписанным пользователям.
"""
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.config import LESSONS_SCHEDULE
from src.database import get_subscribed_users
from aiogram import Bot


# Глобальное хранилище отправленных уведомлений (дата + номер пары)
# Необходимо чтобы не отправлять уведомление несколько раз за один день
_sent_notifications: dict[str, set[int]] = {}


def _get_today_key() -> str:
    """Возвращает ключ в формате YYYY-MM-DD для текущего дня."""
    return datetime.now().strftime("%Y-%m-%d")


def _get_lesson_ending_in_5_minutes() -> dict | None:
    """
    Определяет, какая пара заканчивается в течение следующих 5 минут.
    Возвращает словарь пары или None если нет таких пар.
    """
    now = datetime.now()
    for lesson in LESSONS_SCHEDULE:
        end_hour, end_minute = map(int, lesson["end"].split(":"))
        lesson_end = now.replace(
            hour=end_hour,
            minute=end_minute,
            second=0,
            microsecond=0,
        )
        notification_time = lesson_end - timedelta(minutes=5)

        # Проверяем если текущее время в диапазоне [время-уведомления, время-окончания)
        if notification_time <= now < lesson_end:
            return lesson

    return None


def _get_break_after_lesson(lesson: dict) -> str:
    """Возвращает строку с информацией о перемене после пары."""
    minutes = lesson["break_duration"]
    if minutes == 0:
        return "Это последняя пара на сегодня! 🎉"
    elif minutes == 5:
        return f"Сейчас будет {minutes} минутная перемена. ⏰"
    elif minutes == 10:
        return f"Сейчас будет {minutes} минутная перемена. ☕"
    elif minutes == 30:
        return f"Сейчас будет {minutes} минутная перемена (длинный перерыв). 🍽️"
    else:
        return f"Сейчас будет {minutes} минутная перемена."


async def send_notification_task(bot: Bot) -> None:
    """
    Основная маршрутная функция планировщика.
    Проверяет какая пара заканчивается и отправляет уведомления подписанным пользователям.
    """
    try:
        # Проверяем только в рабочие дни (пн-пт)
        # 0 = понедельник, 4 = пятница, 5-6 = выходные
        if datetime.now().weekday() >= 5:
            return

        # Определяем пару которая заканчивается в течение 5 минут
        lesson = _get_lesson_ending_in_5_minutes()
        if not lesson:
            return

        # Проверяем что уведомление еще не было отправлено сегодня для этой пары
        today_key = _get_today_key()
        if today_key not in _sent_notifications:
            _sent_notifications[today_key] = set()

        if lesson["number"] in _sent_notifications[today_key]:
            return  # Уведомление уже отправлено

        # Отмечаем что уведомление отправлено
        _sent_notifications[today_key].add(lesson["number"])

        # Получаем список подписанных пользователей
        subscribed_users = await get_subscribed_users()
        if not subscribed_users:
            return

        # Формируем текст уведомления
        break_info = _get_break_after_lesson(lesson)
        message_text = (
            f"⏰ До окончания {lesson['number']}-й пары осталось 5 минут! \n"
            f"{lesson['start']} - {lesson['end']}\n\n"
            f"{break_info}"
        )

        # Отправляем уведомления всем подписанным пользователям
        errors = 0
        for user_id in subscribed_users:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=message_text,
                    parse_mode="HTML"
                )
            except Exception as e:
                errors += 1
                # Молча игнорируем ошибки (пользователь заблокировал бота и т.д.)

        if errors == 0:
            print(f"✅ Уведомление о {lesson['number']}-й паре отправлено {len(subscribed_users)} пользователям")
        else:
            print(f"⚠️ Уведомление о {lesson['number']}-й паре отправлено {len(subscribed_users) - errors} из {len(subscribed_users)} пользователям ({errors} ошибок)")

    except Exception as e:
        print(f"❌ Ошибка в планировщике уведомлений: {e}")


def start_scheduler(bot: Bot) -> AsyncIOScheduler:
    """
    Запускает планировщик для отправки уведомлений.
    Проверяет время каждые 5 секунд.

    Args:
        bot: Экземпляр aiogram Bot для отправки сообщений

    Returns:
        AsyncIOScheduler: Объект планировщика (для возможности остановки)
    """
    scheduler = AsyncIOScheduler()

    # Добавляем периодическую задачу: проверка каждые 5 секунд
    scheduler.add_job(
        send_notification_task,
        IntervalTrigger(seconds=5),
        args=[bot],
        id="lesson_notification_job"
    )

    scheduler.start()
    print("✅ Планировщик уведомлений запущен (проверка каждые 5 секунд)")

    return scheduler
