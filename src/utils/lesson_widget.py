"""
Утилита для виджета "Текущая пара".
Определяет, идёт ли сейчас пара, перемена, или занятий нет,
сопоставляя текущее время с индивидуальным расписанием занятий студента
(предмет, тип пары, аудитория, преподаватель).
"""
import re
from datetime import time as dt_time
from src.config import LESSONS_SCHEDULE, get_kz_now


def _parse_time(t_str: str) -> dt_time:
    """Разбирает строку 'HH:MM' в объект time."""
    h, m = map(int, t_str.split(":"))
    return dt_time(h, m)


def _to_minutes(t_str: str) -> int:
    """Переводит время 'HH:MM' в количество минут от начала суток."""
    h, m = map(int, t_str.split(":"))
    return h * 60 + m


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
    слоту звонков из LESSONS_SCHEDULE.
    """
    time_raw = item.get("time", "")
    if not time_raw:
        return False

    found_times = re.findall(r'\b\d{1,2}[:.]\d{2}\b', time_raw)
    normalized = [_normalize_time_str(t) for t in found_times]

    slot_start = slot["start"]
    slot_end = slot["end"]

    if slot_end in normalized or slot_start in normalized:
        return True

    clean_raw = time_raw.replace(" ", "").replace(".", ":")
    if f"{slot_start}-{slot_end}" in clean_raw or slot_end in clean_raw or slot_start in clean_raw:
        return True

    return False


def get_current_lesson_status(today_lessons: list[dict] | None = None) -> dict:
    """
    Возвращает словарь с информацией о текущем состоянии учебного дня.
    Если передан список today_lessons, персонализирует информацию
    (название предмета, аудитория, преподаватель).

    Возможные статусы:
      - 'in_lesson'         — сейчас идёт пара
      - 'break'             — перемена между парами
      - 'before_day'        — занятия ещё не начались
      - 'after_day'         — занятия закончились
      - 'no_lessons_today'  — сегодня у студента нет занятий по расписанию
      - 'weekend'           — выходной день (воскресенье)
    """
    now = get_kz_now()
    weekday = now.weekday()  # 0=пн, 6=вс

    if weekday >= 6:
        return {"status": "weekend"}

    current_time = now.time().replace(second=0, microsecond=0)
    now_minutes = current_time.hour * 60 + current_time.minute

    # Если расписание студента доступно
    if today_lessons is not None:
        if len(today_lessons) == 0:
            return {"status": "no_lessons_today"}

        # Сопоставляем пары студента со слотами звонков
        user_slots: list[tuple[dict, dict]] = []
        for slot in LESSONS_SCHEDULE:
            for item in today_lessons:
                if _matches_lesson_slot(item, slot):
                    user_slots.append((slot, item))
                    break

        if not user_slots:
            return {"status": "no_lessons_today"}

        first_slot, first_item = user_slots[0]
        last_slot, _ = user_slots[-1]

        first_start_min = _to_minutes(first_slot["start"])
        last_end_min = _to_minutes(last_slot["end"])

        # 1. До начала занятий
        if now_minutes < first_start_min:
            return {
                "status": "before_day",
                "first_slot": first_slot,
                "first_lesson": first_item,
                "remaining_minutes": first_start_min - now_minutes,
            }

        # 2. После окончания всех занятий студента
        if now_minutes > last_end_min:
            return {"status": "after_day"}

        # 3. Проверяем, идёт ли сейчас конкретная пара студента
        for i, (slot, item) in enumerate(user_slots):
            s_start = _to_minutes(slot["start"])
            s_end = _to_minutes(slot["end"])
            if s_start <= now_minutes <= s_end:
                next_pair = user_slots[i + 1] if i + 1 < len(user_slots) else None
                return {
                    "status": "in_lesson",
                    "slot": slot,
                    "lesson": item,
                    "remaining_minutes": s_end - now_minutes,
                    "break_duration": slot.get("break_duration", 0),
                    "next_slot": next_pair[0] if next_pair else None,
                    "next_lesson": next_pair[1] if next_pair else None,
                }

        # 4. Проверяем перемену или окно между парами
        past_slots = [(s, it) for s, it in user_slots if _to_minutes(s["end"]) < now_minutes]
        upcoming_slots = [(s, it) for s, it in user_slots if _to_minutes(s["start"]) > now_minutes]

        if upcoming_slots:
            next_slot, next_item = upcoming_slots[0]
            prev_slot, prev_item = past_slots[-1] if past_slots else (None, None)
            rem = _to_minutes(next_slot["start"]) - now_minutes
            return {
                "status": "break",
                "prev_slot": prev_slot,
                "prev_lesson": prev_item,
                "next_slot": next_slot,
                "next_lesson": next_item,
                "remaining_minutes": rem,
            }

        return {"status": "after_day"}

    # Резервный режим (по звонкам университета), если расписание студента недоступно
    for i, lesson in enumerate(LESSONS_SCHEDULE):
        start = _parse_time(lesson["start"])
        end = _parse_time(lesson["end"])

        if start <= current_time <= end:
            end_minutes = end.hour * 60 + end.minute
            remaining = end_minutes - now_minutes
            next_lesson = LESSONS_SCHEDULE[i + 1] if i + 1 < len(LESSONS_SCHEDULE) else None

            return {
                "status": "in_lesson",
                "slot": lesson,
                "lesson": None,
                "remaining_minutes": remaining,
                "next_slot": next_lesson,
                "next_lesson": None,
                "break_duration": lesson["break_duration"],
            }

        if i + 1 < len(LESSONS_SCHEDULE):
            next_lesson = LESSONS_SCHEDULE[i + 1]
            next_start = _parse_time(next_lesson["start"])
            if end < current_time < next_start:
                next_start_minutes = next_start.hour * 60 + next_start.minute
                return {
                    "status": "break",
                    "prev_slot": lesson,
                    "prev_lesson": None,
                    "next_slot": next_lesson,
                    "next_lesson": None,
                    "remaining_minutes": next_start_minutes - now_minutes,
                }

    first_start = _parse_time(LESSONS_SCHEDULE[0]["start"])
    last_end = _parse_time(LESSONS_SCHEDULE[-1]["end"])

    if current_time < first_start:
        start_minutes = first_start.hour * 60 + first_start.minute
        return {
            "status": "before_day",
            "first_slot": LESSONS_SCHEDULE[0],
            "first_lesson": None,
            "remaining_minutes": start_minutes - now_minutes,
        }

    return {"status": "after_day"}


def format_current_lesson_message(status_dict: dict) -> str:
    """Формирует красивое текстовое сообщение для виджета с аудиторией и предметом."""
    status = status_dict["status"]

    if status == "weekend":
        return (
            "🏖️ <b>Сегодня выходной!</b>\n\n"
            "Отдыхай и восстанавливай силы 💪\n"
            "Следующие занятия — в понедельник."
        )

    if status == "no_lessons_today":
        return (
            "🎉 <b>Сегодня у вас нет пар по расписанию!</b>\n\n"
            "Свободный день для отдыха и подготовки ✨\n"
            "Расписание на другие дни доступно во вкладке <b>Расписание</b>."
        )

    if status == "before_day":
        lesson = status_dict.get("first_lesson")
        slot = status_dict.get("first_slot")
        remaining = status_dict["remaining_minutes"]
        hours, mins = divmod(remaining, 60)
        time_str = f"{hours} ч {mins} мин" if hours else f"{mins} мин"

        text = (
            "🌅 <b>Занятия ещё не начались</b>\n\n"
            f"⏳ До первой пары: <b>{time_str}</b>\n\n"
        )
        if lesson and slot:
            subj = lesson.get("subject", "Не указан")
            l_type = f" ({lesson['type']})" if lesson.get("type") else ""
            room = lesson.get("room") or "Не указана"
            teacher = lesson.get("teacher")
            text += (
                f"📚 <b>Первая пара №{slot['number']}:</b> {subj}{l_type}\n"
                f"🕐 <b>Время:</b> {slot['start']} – {slot['end']}\n"
                f"📍 <b>Аудитория:</b> <code>{room}</code>\n"
            )
            if teacher:
                text += f"👨‍🏫 Преподаватель: <i>{teacher}</i>\n"
        elif slot:
            text += (
                f"📚 Первая пара: <b>пара №{slot['number']}</b>\n"
                f"🕐 Начало: <b>{slot['start']}</b>\n"
            )
        return text

    if status == "in_lesson":
        slot = status_dict.get("slot")
        lesson = status_dict.get("lesson")
        remaining = status_dict["remaining_minutes"]
        next_slot = status_dict.get("next_slot")
        next_lesson = status_dict.get("next_lesson")
        break_dur = status_dict.get("break_duration", 0)

        hours, mins = divmod(remaining, 60)
        time_str = f"{hours} ч {mins} мин" if hours else f"{mins} мин"

        text = "📖 <b>Сейчас идёт пара!</b>\n\n"
        if lesson and slot:
            subj = lesson.get("subject", "Предмет не указан")
            l_type = f" ({lesson['type']})" if lesson.get("type") else ""
            room = lesson.get("room") or "Не указана"
            teacher = lesson.get("teacher")
            text += (
                f"🔢 <b>Пара №{slot['number']}</b> ({slot['start']} – {slot['end']})\n"
                f"📚 <b>Предмет:</b> {subj}{l_type}\n"
                f"📍 <b>Аудитория:</b> <code>{room}</code>\n"
            )
            if teacher:
                text += f"👨‍🏫 Преподаватель: <i>{teacher}</i>\n"
            text += f"⏳ До конца пары: <b>{time_str}</b>\n"
        elif slot:
            text += (
                f"🔢 <b>Пара №{slot['number']}</b>\n"
                f"🕐 Время: <b>{slot['start']} – {slot['end']}</b>\n"
                f"⏳ До конца пары: <b>{time_str}</b>\n"
            )

        if next_slot and next_lesson:
            n_subj = next_lesson.get("subject", "Следующая пара")
            n_type = f" ({next_lesson['type']})" if next_lesson.get("type") else ""
            n_room = next_lesson.get("room") or "Не указана"
            text += (
                f"\n☕ <b>Перемена:</b> {break_dur} мин\n"
                f"➡️ <b>Следующая пара №{next_slot['number']}:</b> {n_subj}{n_type}\n"
                f"📍 <b>Куда идти:</b> аудитория <code>{n_room}</code> (в <b>{next_slot['start']}</b>)"
            )
        elif next_slot and break_dur > 0:
            text += (
                f"\n☕ <b>Следующая перемена:</b> {break_dur} мин\n"
                f"📚 Следующая пара: <b>№{next_slot['number']}</b> в <b>{next_slot['start']}</b>"
            )
        elif not next_slot:
            text += "\n🎉 <b>Это ваша последняя пара на сегодня!</b>"

        return text

    if status == "break":
        prev_slot = status_dict.get("prev_slot")
        next_slot = status_dict.get("next_slot")
        next_lesson = status_dict.get("next_lesson")
        remaining = status_dict["remaining_minutes"]

        hours, mins = divmod(remaining, 60)
        time_str = f"{hours} ч {mins} мин" if hours else f"{mins} мин"

        text = (
            "☕ <b>Сейчас перемена!</b>\n\n"
            f"⏳ До начала пары: <b>{time_str}</b>\n\n"
        )
        if next_slot and next_lesson:
            n_subj = next_lesson.get("subject", "Предмет не указан")
            n_type = f" ({next_lesson['type']})" if next_lesson.get("type") else ""
            n_room = next_lesson.get("room") or "Не указана"
            n_teacher = next_lesson.get("teacher")
            text += (
                f"📚 <b>Следующая пара №{next_slot['number']}:</b> {n_subj}{n_type}\n"
                f"🕐 <b>Время:</b> <b>{next_slot['start']}</b> – {next_slot['end']}\n"
                f"📍 <b>Куда идти:</b> аудитория <code>{n_room}</code>\n"
            )
            if n_teacher:
                text += f"👨‍🏫 Преподаватель: <i>{n_teacher}</i>\n"
        elif next_slot:
            text += (
                f"📚 <b>Следующая пара №{next_slot['number']}</b>\n"
                f"🕐 Начало: <b>{next_slot['start']}</b> – <b>{next_slot['end']}</b>\n"
            )

        if prev_slot:
            text += f"\n<i>(Пара №{prev_slot['number']} завершилась)</i>"

        return text

    if status == "after_day":
        return (
            "🌙 <b>Все занятия на сегодня завершены!</b>\n\n"
            "Хорошего отдыха 🌟\n"
            "Расписание на завтра можно посмотреть в разделе <b>Расписание</b>."
        )

    return "❓ Не удалось определить статус учебного дня."
