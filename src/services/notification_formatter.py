"""
Сопоставление пар со слотами звонков, распознавание МООК и форматирование уведомлений.
"""
import re

from src.config import LESSONS_SCHEDULE


def _normalize_time_str(val: str) -> str:
    """Нормализует строку времени, например '8:15' -> '08:15'."""
    val = val.replace(".", ":").strip()
    parts = val.split(":")
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
    return val


def matches_lesson_slot(item: dict, slot: dict) -> bool:
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

    if slot_end in normalized or slot_start in normalized:
        return True

    clean_raw = time_raw.replace(" ", "").replace(".", ":")
    return f"{slot_start}-{slot_end}" in clean_raw or slot_end in clean_raw or slot_start in clean_raw


def get_user_slots_today(today_lessons: list[dict]) -> list[tuple[dict, dict]]:
    """
    Сопоставляет все сегодняшние пары пользователя со слотами звонков LESSONS_SCHEDULE.
    Возвращает список кортежей (slot, lesson_item), отсортированный по номеру пары.
    """
    user_slots = []
    seen_slots = set()
    for item in today_lessons:
        for slot in LESSONS_SCHEDULE:
            if matches_lesson_slot(item, slot):
                if slot["number"] not in seen_slots:
                    seen_slots.add(slot["number"])
                    user_slots.append((slot, item))
                break
    user_slots.sort(key=lambda x: x[0]["number"])
    return user_slots


def is_mook_lesson(lesson: dict | None) -> bool:
    """
    Определяет, является ли занятие дистанционным / МООК.
    Проверяет поля 'room', 'type', 'subject' на ключевые маркеры дистанционного обучения.
    """
    if not lesson or not isinstance(lesson, dict):
        return False

    room = str(lesson.get("room") or "").strip().lower()
    l_type = str(lesson.get("type") or "").strip().lower()
    subject = str(lesson.get("subject") or "").strip().lower()
    combined = f"{room} {l_type} {subject}"

    patterns = (
        "моок", "mook", "mooc",
        "дистанц", "дистант", "онлайн", "online",
        "zoom", "teams", "google meet", "webex",
    )
    if any(p in combined for p in patterns):
        return True

    return bool(re.search(r'\b(сдо|sdo)\b', combined, re.IGNORECASE))


def _format_break_line(current_slot: dict, next_slot: dict, in_person_only: bool = False) -> str:
    """Форматирует строку о перемене или окне до следующей пары."""
    if next_slot["number"] == current_slot["number"] + 1:
        minutes = current_slot.get("break_duration", 10)
        if minutes == 30:
            return f"🍽️ Сейчас будет {minutes}-минутная перемена (большой перерыв)."
        if minutes == 5:
            return f"⏰ Сейчас будет {minutes}-минутная перемена."
        return f"☕ Сейчас будет {minutes}-минутная перемена."
    if in_person_only:
        return f"☕ У вас окно/перерыв! Следующая очная пара начнётся в <b>{next_slot['start']}</b>."
    return f"☕ У вас окно! Следующая пара начнётся в <b>{next_slot['start']}</b>."


def _format_lesson_desc(prefix: str, lesson: dict, is_mook: bool) -> str | None:
    """Форматирует строку описания пары (предмет, тип, аудитория/онлайн)."""
    subj = lesson.get("subject", "").strip()
    if not subj:
        return None
    l_type = lesson.get("type", "").strip()
    room = lesson.get("room", "").strip()

    desc = f"{prefix}<b>{subj}</b>"
    if l_type:
        desc += f" (<i>{l_type}</i>)"
    if room:
        if is_mook:
            desc += f" • 🌐 {room} (дистанционно)"
        else:
            desc += f" • 📍 Ауд. {room}"
    return desc


def format_user_notification(
    current_slot: dict,
    current_lesson: dict,
    user_slots: list[tuple[dict, dict]],
    notify_mook: bool = True,
) -> str:
    """Формирует персональный текст уведомления об окончании пары."""
    slot_num = current_slot["number"]
    lines = [
        f"⏰ <b>До окончания {slot_num}-й пары осталось 5 минут!</b>",
        f"⏱ <i>{current_slot['start']} - {current_slot['end']}</i>",
    ]

    curr_desc = _format_lesson_desc("📚 ", current_lesson, is_mook_lesson(current_lesson))
    if curr_desc:
        lines.append(curr_desc)
    lines.append("")

    subsequent_slots = [(s, it) for s, it in user_slots if s["number"] > slot_num]
    if not subsequent_slots:
        lines.append("🎉 <b>Это была ваша последняя пара на сегодня!</b>")
        lines.append("Отличного отдыха!")
        return "\n".join(lines)

    if not notify_mook:
        next_in_person = [(s, it) for s, it in subsequent_slots if not is_mook_lesson(it)]
        if not next_in_person:
            lines.append("🎉 <b>Это была ваша последняя очная пара на сегодня!</b>")
            lines.append("<i>(Далее по расписанию: дистанционные занятия МООК)</i>")
            lines.append("Отличного отдыха!")
            return "\n".join(lines)

        next_slot, next_lesson = next_in_person[0]
        lines.append(_format_break_line(current_slot, next_slot, in_person_only=True))
        next_desc = _format_lesson_desc("🔜 Следующая пара: ", next_lesson, is_mook=False)
        if next_desc:
            lines.append(next_desc)
        return "\n".join(lines)

    next_slot, next_lesson = subsequent_slots[0]
    lines.append(_format_break_line(current_slot, next_slot, in_person_only=False))
    next_desc = _format_lesson_desc("🔜 Следующая пара: ", next_lesson, is_mook=is_mook_lesson(next_lesson))
    if next_desc:
        lines.append(next_desc)
    return "\n".join(lines)
