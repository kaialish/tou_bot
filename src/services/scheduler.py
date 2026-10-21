"""
Планировщик для отправки автоматических уведомлений об окончании пар.
Уведомления привязаны к индивидуальному расписанию пар каждого студента,
чтобы исключить бессмысленную рассылку до 12-й пары при раннем окончании занятий.
"""
import re
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
)
from src.services.parser import parse_schedule_items
from src.services.tou_client import get_schedule_html


# Хранилище отправленных уведомлений: {today_key: {(user_id, slot_number), ...}}
# Отслеживает, чтобы пользователь не получал уведомление по одной и той же паре дважды за день
_sent_user_notifications: dict[str, set[tuple[int, int]]] = {}

try:
    _KZ_TZ = zoneinfo.ZoneInfo("Asia/Almaty")
except Exception:
    _KZ_TZ = None


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
    """
    Определяет, какой слот расписания звонков заканчивается в течение следующих 5 минут.
    Возвращает словарь пары из LESSONS_SCHEDULE или None, если таких пар нет.
    """
    now = _get_now()
    for lesson in LESSONS_SCHEDULE:
        end_hour, end_minute = map(int, lesson["end"].split(":"))
        lesson_end = now.replace(
            hour=end_hour,
            minute=end_minute,
            second=0,
            microsecond=0,
        )
        notification_time = lesson_end - timedelta(minutes=5)

        # Проверяем, находится ли текущее время в интервале [время-уведомления, время-окончания)
        if notification_time <= now < lesson_end:
            return lesson

    return None


def _normalize_time_str(val: str) -> str:
    """Нормализует строку времени, например '8:15' -> '08:15'."""
    val = val.replace(".", ":").strip()
    parts = val.split(":")
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
    return val


def _matches_lesson_slot(item: dict, slot: dict) -> bool:
    """
    Проверяет, соответствует ли пара из расписания пользователя
    данному слоту звонков (slot из LESSONS_SCHEDULE).
    """
    time_raw = item.get("time", "")
    if not time_raw:
        return False

    found_times = re.findall(r'\b\d{1,2}[:.]\d{2}\b', time_raw)
    normalized = [_normalize_time_str(t) for t in found_times]

    slot_start = slot["start"]
    slot_end = slot["end"]

    # Проверка по времени окончания (наиболее точная для оповещения о конце пары)
    if slot_end in normalized:
        return True

    # Проверка по времени начала
    if slot_start in normalized:
        return True

    # Текстовая проверка подстроки для нестандартных форматов
    clean_raw = time_raw.replace(" ", "").replace(".", ":")
    if f"{slot_start}-{slot_end}" in clean_raw or slot_end in clean_raw or slot_start in clean_raw:
        return True

    return False


def _get_user_slots_today(today_lessons: list[dict]) -> list[tuple[dict, dict]]:
    """
    Сопоставляет все сегодняшние пары пользователя со слотами звонков LESSONS_SCHEDULE.
    Возвращает список кортежей (slot, lesson_item), отсортированный по номеру пары.
    """
    user_slots = []
    seen_slots = set()
    for item in today_lessons:
        for slot in LESSONS_SCHEDULE:
            if _matches_lesson_slot(item, slot):
                if slot["number"] not in seen_slots:
                    seen_slots.add(slot["number"])
                    user_slots.append((slot, item))
                break
    user_slots.sort(key=lambda x: x[0]["number"])
    return user_slots


def _format_user_notification(
    current_slot: dict,
    current_lesson: dict,
    user_slots: list[tuple[dict, dict]]
) -> str:
    """
    Формирует персональный текст уведомления для студента:
    - Информацию о завершающейся паре (предмет, тип, аудитория)
    - Информацию о перемене или об окончании всех пар на сегодня
    - Информацию о следующей паре (если есть)
    """
    slot_num = current_slot["number"]
    start_time = current_slot["start"]
    end_time = current_slot["end"]

    subj = current_lesson.get("subject", "").strip()
    l_type = current_lesson.get("type", "").strip()
    room = current_lesson.get("room", "").strip()

    # Ищем следующую пару для этого студента сегодня
    subsequent_slots = [
        (s, it) for s, it in user_slots
        if s["number"] > slot_num
    ]

    lines = [
        f"⏰ <b>До окончания {slot_num}-й пары осталось 5 минут!</b>",
        f"⏱ <i>{start_time} - {end_time}</i>",
    ]

    if subj:
        curr_desc = f"📚 <b>{subj}</b>"
        if l_type:
            curr_desc += f" (<i>{l_type}</i>)"
        if room:
            curr_desc += f" • 📍 Ауд. {room}"
        lines.append(curr_desc)

    lines.append("")

    if not subsequent_slots:
        # Это была последняя пара для данного студента на сегодня!
        lines.append("🎉 <b>Это была ваша последняя пара на сегодня!</b>")
        lines.append("Отличного отдыха!")
    else:
        next_slot, next_lesson = subsequent_slots[0]
        # Проверяем, идёт ли следующая пара сразу следом или через окно
        if next_slot["number"] == slot_num + 1:
            minutes = current_slot.get("break_duration", 10)
            if minutes == 30:
                break_line = f"🍽️ Сейчас будет {minutes}-минутная перемена (большой перерыв)."
            elif minutes == 5:
                break_line = f"⏰ Сейчас будет {minutes}-минутная перемена."
            else:
                break_line = f"☕ Сейчас будет {minutes}-минутная перемена."
        else:
            break_line = f"☕ У вас окно! Следующая пара начнётся в <b>{next_slot['start']}</b>."

        lines.append(break_line)

        # Добавляем информацию о следующей паре
        next_subj = next_lesson.get("subject", "").strip()
        next_type = next_lesson.get("type", "").strip()
        next_room = next_lesson.get("room", "").strip()
        if next_subj:
            next_desc = f"🔜 Следующая пара: <b>{next_subj}</b>"
            if next_type:
                next_desc += f" (<i>{next_type}</i>)"
            if next_room:
                next_desc += f" • 📍 {next_room}"
            lines.append(next_desc)

    return "\n".join(lines)


async def send_notification_task(bot: Bot) -> None:
    """
    Основная задача планировщика.
    Проверяет, какая пара заканчивается в ближайшие 5 минут,
    и отправляет персональные уведомления только тем подписанным пользователям,
    у которых эта пара действительно есть сегодня в расписании занятий.
    """
    try:
        now = _get_now()
        # В воскресенье (6) учебных занятий нет
        if now.weekday() >= 6:
            return

        # Определяем слот звонков, который заканчивается в течение 5 минут
        slot = _get_lesson_ending_in_5_minutes()
        if not slot:
            return

        today_key = _get_today_key()
        _cleanup_old_sent_notifications(today_key)
        if today_key not in _sent_user_notifications:
            _sent_user_notifications[today_key] = set()

        # Получаем список подписанных пользователей вместе с их сохранённым расписанием
        subscribers = await get_subscribed_users_with_schedules()
        if not subscribers:
            return

        # Фильтруем тех, кому по данному слоту сегодня ещё не отправляли уведомление
        pending_subscribers = [
            (uid, html) for uid, html in subscribers
            if (uid, slot["number"]) not in _sent_user_notifications[today_key]
        ]
        if not pending_subscribers:
            return

        sent_count = 0
        errors = 0

        for user_id, schedule_html in pending_subscribers:
            try:
                # Если кэш расписания отсутствует, пробуем разово подгрузить
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
                    # Помечаем пользователя, чтобы не зацикливаться на повторных попытках
                    _sent_user_notifications[today_key].add((user_id, slot["number"]))
                    continue

                # Парсим пары пользователя на сегодня
                today_lessons = parse_schedule_items(schedule_html, day="today", target_date=now)
                if not today_lessons:
                    # У пользователя сегодня вообще нет занятий
                    _sent_user_notifications[today_key].add((user_id, slot["number"]))
                    continue

                # Ищем текущую пару пользователя, соответствующую этому слоту звонков
                matching_lessons = [
                    item for item in today_lessons
                    if _matches_lesson_slot(item, slot)
                ]

                if not matching_lessons:
                    # У пользователя НЕТ этой пары сегодня (закончил раньше или окно)
                    _sent_user_notifications[today_key].add((user_id, slot["number"]))
                    continue

                # Пользователь действительно учится на этой паре прямо сейчас!
                current_lesson = matching_lessons[0]
                user_slots = _get_user_slots_today(today_lessons)
                message_text = _format_user_notification(slot, current_lesson, user_slots)

                await bot.send_message(
                    chat_id=user_id,
                    text=message_text,
                    parse_mode="HTML"
                )
                sent_count += 1
                _sent_user_notifications[today_key].add((user_id, slot["number"]))

            except Exception:
                errors += 1
                _sent_user_notifications[today_key].add((user_id, slot["number"]))

        if sent_count > 0:
            print(f"✅ Уведомление о {slot['number']}-й паре отправлено {sent_count} пользователям (ошибок: {errors})")

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
    try:
        kz_tz = zoneinfo.ZoneInfo("Asia/Almaty")
    except Exception:
        kz_tz = None

    scheduler = AsyncIOScheduler(timezone=kz_tz) if kz_tz else AsyncIOScheduler()

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
