"""
Планировщик для отправки автоматических уведомлений об окончании пар.
Уведомления привязаны к индивидуальному расписанию пар каждого студента,
чтобы исключить бессмысленную рассылку до 12-й пары при раннем окончании занятий.
"""
import zoneinfo
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from aiogram import Bot

from src.config import LESSONS_SCHEDULE, get_kz_now
from src.database import (
    get_subscribed_users_with_schedules,
    get_user_credentials,
    save_cached_schedule,
    set_last_notification_msg_id,
)
from src.services.notification_formatter import (  # noqa: F401
    format_user_notification,
    get_user_slots_today,
    is_mook_lesson,
    matches_lesson_slot,
)
from src.services.parser import parse_schedule_items
from src.services.tou_client import get_schedule_html


# Хранилище отправленных уведомлений: {today_key: {(user_id, slot_number), ...}}
_sent_user_notifications: dict[str, set[tuple[int, int]]] = {}


def _get_now() -> datetime:
    """Возвращает текущее время с учетом часового пояса Казахстана (Asia/Almaty, UTC+5)."""
    return get_kz_now().replace(tzinfo=None)


def _get_today_key() -> str:
    """Возвращает ключ в формате YYYY-MM-DD для текущего дня по KZ."""
    return _get_now().strftime("%Y-%m-%d")


def _cleanup_old_sent_notifications(current_today_key: str) -> None:
    """Очищает память от записей за прошлые дни."""
    for day_key in list(_sent_user_notifications.keys()):
        if day_key != current_today_key:
            del _sent_user_notifications[day_key]


def _get_lesson_ending_in_5_minutes() -> dict | None:
    """Определяет слот расписания звонков, заканчивающийся в течение 5 минут."""
    now = _get_now()
    for lesson in LESSONS_SCHEDULE:
        end_hour, end_minute = map(int, lesson["end"].split(":"))
        lesson_end = now.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
        notification_time = lesson_end - timedelta(minutes=5)
        if notification_time <= now < lesson_end:
            return lesson
    return None


async def send_notification_task(bot: Bot) -> None:
    """
    Основная задача планировщика.
    Проверяет, какая пара заканчивается в ближайшие 5 минут,
    и отправляет персональные уведомления подписанным пользователям.
    """
    try:
        now = _get_now()
        if now.weekday() >= 6:
            return

        slot = _get_lesson_ending_in_5_minutes()
        if not slot:
            return

        today_key = _get_today_key()
        _cleanup_old_sent_notifications(today_key)
        _sent_user_notifications.setdefault(today_key, set())

        subscribers = await get_subscribed_users_with_schedules()
        if not subscribers:
            return

        pending_subscribers = [
            (uid, html, notify_mook, last_msg_id)
            for uid, html, notify_mook, last_msg_id in subscribers
            if (uid, slot["number"]) not in _sent_user_notifications[today_key]
        ]
        if not pending_subscribers:
            return

        sent_count = 0
        errors = 0

        for user_id, schedule_html, notify_mook, last_msg_id in pending_subscribers:
            try:
                if not schedule_html:
                    creds = await get_user_credentials(user_id)
                    if creds:
                        login, password = creds
                        success, html_or_err = await get_schedule_html(login, password, bot=bot)
                        if success:
                            schedule_html = html_or_err
                            now_str = now.strftime("%d.%m.%Y в %H:%M")
                            await save_cached_schedule(user_id, schedule_html, now_str)

                if not schedule_html:
                    _sent_user_notifications[today_key].add((user_id, slot["number"]))
                    continue

                today_lessons = parse_schedule_items(schedule_html, day="today", target_date=now)
                matching_lessons = [
                    item for item in (today_lessons or [])
                    if matches_lesson_slot(item, slot)
                ]

                if not matching_lessons:
                    _sent_user_notifications[today_key].add((user_id, slot["number"]))
                    continue

                current_lesson = matching_lessons[0]
                if is_mook_lesson(current_lesson) and not notify_mook:
                    _sent_user_notifications[today_key].add((user_id, slot["number"]))
                    continue

                user_slots = get_user_slots_today(today_lessons)
                message_text = format_user_notification(
                    slot, current_lesson, user_slots, notify_mook=notify_mook
                )

                if last_msg_id:
                    try:
                        await bot.delete_message(chat_id=user_id, message_id=last_msg_id)
                    except Exception:
                        pass

                sent_msg = await bot.send_message(
                    chat_id=user_id,
                    text=message_text,
                    parse_mode="HTML"
                )
                sent_count += 1
                await set_last_notification_msg_id(user_id, sent_msg.message_id)
                _sent_user_notifications[today_key].add((user_id, slot["number"]))

            except Exception:
                errors += 1
                _sent_user_notifications[today_key].add((user_id, slot["number"]))

        if sent_count > 0:
            print(f"✅ Уведомление о {slot['number']}-й паре отправлено {sent_count} пользователям (ошибок: {errors})")

    except Exception as e:
        print(f"❌ Ошибка в планировщике уведомлений: {e}")


def start_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Запускает планировщик для отправки уведомлений (проверка каждые 5 секунд)."""
    try:
        kz_tz = zoneinfo.ZoneInfo("Asia/Almaty")
    except Exception:
        kz_tz = None

    scheduler = AsyncIOScheduler(timezone=kz_tz) if kz_tz else AsyncIOScheduler()
    scheduler.add_job(
        send_notification_task,
        IntervalTrigger(seconds=5),
        args=[bot],
        id="lesson_notification_job"
    )
    scheduler.start()
    print("✅ Планировщик уведомлений запущен (проверка каждые 5 секунд)")
    return scheduler
