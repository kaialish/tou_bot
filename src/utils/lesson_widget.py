"""
Утилита для виджета "Текущая пара".
Определяет, идёт ли сейчас пара, перемена, или занятий нет.
"""
from datetime import time as dt_time
from src.config import LESSONS_SCHEDULE, get_kz_now


def _parse_time(t_str: str) -> dt_time:
    """Разбирает строку 'HH:MM' в объект time."""
    h, m = map(int, t_str.split(":"))
    return dt_time(h, m)


def get_current_lesson_status() -> dict:
    """
    Возвращает словарь с информацией о текущем состоянии учебного дня.

    Возможные значения ключа 'status':
      - 'in_lesson'   — сейчас идёт пара
      - 'break'       — перемена между парами
      - 'before_day'  — занятия ещё не начались
      - 'after_day'   — занятия закончились
      - 'weekend'     — выходной
    """
    now = get_kz_now()
    weekday = now.weekday()  # 0=пн, 6=вс

    if weekday >= 6:  # только воскресенье — выходной, суббота может быть учебной
        return {"status": "weekend"}

    current_time = now.time().replace(second=0, microsecond=0)

    for i, lesson in enumerate(LESSONS_SCHEDULE):
        start = _parse_time(lesson["start"])
        end = _parse_time(lesson["end"])

        # Идёт пара
        if start <= current_time <= end:
            # Считаем оставшееся время до конца пары
            now_minutes = current_time.hour * 60 + current_time.minute
            end_minutes = end.hour * 60 + end.minute
            remaining = end_minutes - now_minutes

            # Определяем следующую пару (перемену)
            next_lesson = LESSONS_SCHEDULE[i + 1] if i + 1 < len(LESSONS_SCHEDULE) else None
            break_dur = lesson["break_duration"]

            return {
                "status": "in_lesson",
                "lesson": lesson,
                "remaining_minutes": remaining,
                "next_lesson": next_lesson,
                "break_duration": break_dur,
            }

        # Перемена: между концом текущей и началом следующей
        if i + 1 < len(LESSONS_SCHEDULE):
            next_lesson = LESSONS_SCHEDULE[i + 1]
            next_start = _parse_time(next_lesson["start"])
            if end < current_time < next_start:
                now_minutes = current_time.hour * 60 + current_time.minute
                next_start_minutes = next_start.hour * 60 + next_start.minute
                remaining = next_start_minutes - now_minutes

                return {
                    "status": "break",
                    "after_lesson": lesson,
                    "next_lesson": next_lesson,
                    "remaining_minutes": remaining,
                }

    # До начала первой пары
    first_start = _parse_time(LESSONS_SCHEDULE[0]["start"])
    last_end = _parse_time(LESSONS_SCHEDULE[-1]["end"])

    if current_time < first_start:
        now_minutes = current_time.hour * 60 + current_time.minute
        start_minutes = first_start.hour * 60 + first_start.minute
        remaining = start_minutes - now_minutes
        return {
            "status": "before_day",
            "first_lesson": LESSONS_SCHEDULE[0],
            "remaining_minutes": remaining,
        }

    if current_time > last_end:
        return {"status": "after_day"}

    return {"status": "after_day"}


def format_current_lesson_message(status_dict: dict) -> str:
    """Формирует красивое текстовое сообщение для виджета текущей пары."""
    status = status_dict["status"]

    if status == "weekend":
        return (
            "🏖️ <b>Сегодня выходной!</b>\n\n"
            "Отдыхай и восстанавливай силы 💪\n"
            "Следующие занятия — в понедельник."
        )

    if status == "before_day":
        lesson = status_dict["first_lesson"]
        remaining = status_dict["remaining_minutes"]
        hours, mins = divmod(remaining, 60)
        time_str = f"{hours} ч {mins} мин" if hours else f"{mins} мин"
        return (
            "🌅 <b>Занятия ещё не начались</b>\n\n"
            f"📚 Первая пара: <b>пара №{lesson['number']}</b>\n"
            f"🕐 Начало: <b>{lesson['start']}</b>\n"
            f"⏳ До начала: <b>{time_str}</b>"
        )

    if status == "in_lesson":
        lesson = status_dict["lesson"]
        remaining = status_dict["remaining_minutes"]
        next_lesson = status_dict.get("next_lesson")
        break_dur = status_dict.get("break_duration", 0)
        hours, mins = divmod(remaining, 60)
        time_str = f"{hours} ч {mins} мин" if hours else f"{mins} мин"

        text = (
            f"📖 <b>Сейчас идёт пара!</b>\n\n"
            f"🔢 <b>Пара №{lesson['number']}</b>\n"
            f"🕐 Время: <b>{lesson['start']} – {lesson['end']}</b>\n"
            f"⏳ До конца пары: <b>{time_str}</b>"
        )
        if next_lesson and break_dur > 0:
            text += (
                f"\n\n☕ <b>Следующая перемена:</b> {break_dur} мин\n"
                f"📚 Следующая пара: <b>№{next_lesson['number']}</b> в <b>{next_lesson['start']}</b>"
            )
        elif not next_lesson:
            text += "\n\n🎉 Это последняя пара на сегодня!"
        return text

    if status == "break":
        after = status_dict["after_lesson"]
        nxt = status_dict["next_lesson"]
        remaining = status_dict["remaining_minutes"]
        hours, mins = divmod(remaining, 60)
        time_str = f"{hours} ч {mins} мин" if hours else f"{mins} мин"

        return (
            f"☕ <b>Сейчас перемена!</b>\n\n"
            f"✅ Пара №{after['number']} завершилась\n"
            f"⏳ До начала следующей: <b>{time_str}</b>\n\n"
            f"📚 <b>Следующая пара №{nxt['number']}</b>\n"
            f"🕐 Начало: <b>{nxt['start']}</b> – <b>{nxt['end']}</b>"
        )

    if status == "after_day":
        return (
            "🌙 <b>Занятия на сегодня завершены!</b>\n\n"
            "Хорошего отдыха 🌟\n"
            "Расписание на завтра можно посмотреть в разделе <b>Расписание</b>."
        )

    return "❓ Не удалось определить статус учебного дня."
