# -*- coding: utf-8 -*-
"""
Изолированный тест: только логика сопоставления пар (без БД и apscheduler).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re

# ─────────────────────────────────────────────────────────────────────────────
# Вставляем минимальные зависимости из scheduler.py напрямую, без импорта всего модуля
# ─────────────────────────────────────────────────────────────────────────────

LESSONS_SCHEDULE = [
    {"number": 1,  "start": "08:15", "end": "09:05", "break_duration": 10},
    {"number": 2,  "start": "09:15", "end": "10:05", "break_duration": 10},
    {"number": 3,  "start": "10:15", "end": "11:05", "break_duration": 10},
    {"number": 4,  "start": "11:15", "end": "12:05", "break_duration": 30},
    {"number": 5,  "start": "12:35", "end": "13:25", "break_duration": 10},
    {"number": 6,  "start": "13:35", "end": "14:25", "break_duration": 10},
    {"number": 7,  "start": "14:35", "end": "15:25", "break_duration": 5},
    {"number": 8,  "start": "15:30", "end": "16:20", "break_duration": 5},
    {"number": 9,  "start": "16:25", "end": "17:15", "break_duration": 5},
    {"number": 10, "start": "17:20", "end": "18:10", "break_duration": 5},
    {"number": 11, "start": "18:15", "end": "19:05", "break_duration": 5},
    {"number": 12, "start": "19:10", "end": "20:00", "break_duration": 0},
]


def _normalize_time_str(val: str) -> str:
    val = val.replace(".", ":").strip()
    parts = val.split(":")
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
    return val


def _matches_lesson_slot(item: dict, slot: dict) -> bool:
    time_raw = item.get("time", "")
    if not time_raw:
        return False
    found_times = re.findall(r'\b\d{1,2}[:\.]\d{2}\b', time_raw)
    normalized = [_normalize_time_str(t) for t in found_times]
    slot_start = slot["start"]
    slot_end   = slot["end"]
    if slot_end   in normalized: return True
    if slot_start in normalized: return True
    clean_raw = time_raw.replace(" ", "").replace(".", ":")
    if f"{slot_start}-{slot_end}" in clean_raw or slot_end in clean_raw or slot_start in clean_raw:
        return True
    return False


def _get_user_slots_today(today_lessons: list[dict]) -> list[tuple]:
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


def _format_user_notification(current_slot, current_lesson, user_slots) -> str:
    slot_num   = current_slot["number"]
    start_time = current_slot["start"]
    end_time   = current_slot["end"]
    subj   = current_lesson.get("subject", "").strip()
    l_type = current_lesson.get("type", "").strip()
    room   = current_lesson.get("room", "").strip()
    subsequent_slots = [(s, it) for s, it in user_slots if s["number"] > slot_num]
    lines = [
        f"⏰ <b>До окончания {slot_num}-й пары осталось 5 минут!</b>",
        f"⏱ <i>{start_time} - {end_time}</i>",
    ]
    if subj:
        curr_desc = f"📚 <b>{subj}</b>"
        if l_type: curr_desc += f" (<i>{l_type}</i>)"
        if room:   curr_desc += f" • 📍 Ауд. {room}"
        lines.append(curr_desc)
    lines.append("")
    if not subsequent_slots:
        lines.append("🎉 <b>Это была ваша последняя пара на сегодня!</b>")
        lines.append("Отличного отдыха!")
    else:
        next_slot, next_lesson = subsequent_slots[0]
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
        next_subj = next_lesson.get("subject", "").strip()
        next_type = next_lesson.get("type", "").strip()
        next_room = next_lesson.get("room", "").strip()
        if next_subj:
            next_desc = f"🔜 Следующая пара: <b>{next_subj}</b>"
            if next_type: next_desc += f" (<i>{next_type}</i>)"
            if next_room: next_desc += f" • 📍 {next_room}"
            lines.append(next_desc)
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Тесты
# ─────────────────────────────────────────────────────────────────────────────

two_lesson_student = [
    {"day": "Понедельник", "time": "08:15-09:05", "subject": "Компьютерные сети", "type": "лек.",  "room": "А-7"},
    {"day": "Понедельник", "time": "09:15-10:05", "subject": "Базы данных",        "type": "лаб.", "room": "Б-204"},
]

print("=== Тест 1: Уведомление о 1-й паре (следующая есть) ===")
slot1 = LESSONS_SCHEDULE[0]
m1 = [it for it in two_lesson_student if _matches_lesson_slot(it, slot1)]
assert len(m1) == 1, f"Ожидался 1 матч, получено {len(m1)}"
user_slots = _get_user_slots_today(two_lesson_student)
assert len(user_slots) == 2
msg1 = _format_user_notification(slot1, m1[0], user_slots)
print(msg1)
assert "Компьютерные сети" in msg1
assert "Следующая пара" in msg1
assert "Базы данных" in msg1
assert "10-минутная перемена" in msg1
print("✅ PASSED\n")

print("=== Тест 2: Уведомление о 2-й паре (ПОСЛЕДНЯЯ пара!) ===")
slot2 = LESSONS_SCHEDULE[1]
m2 = [it for it in two_lesson_student if _matches_lesson_slot(it, slot2)]
assert len(m2) == 1
msg2 = _format_user_notification(slot2, m2[0], user_slots)
print(msg2)
assert "Базы данных" in msg2
assert "последняя пара на сегодня" in msg2
assert "Следующая пара" not in msg2
print("✅ PASSED\n")

print("=== Тест 3: 3-я пара — у студента НЕТ этой пары ===")
slot3 = LESSONS_SCHEDULE[2]
m3 = [it for it in two_lesson_student if _matches_lesson_slot(it, slot3)]
assert len(m3) == 0, f"Ожидался 0 матчей, получено {len(m3)}"
print("Уведомление не отправляется (нет пары в расписании)")
print("✅ PASSED\n")

print("=== Тест 4: Студент с ОКНОМ (1-я и 3-я пары) ===")
window_student = [
    {"day": "Понедельник", "time": "08:15-09:05", "subject": "Математика", "type": "лек.", "room": "101"},
    {"day": "Понедельник", "time": "10:15-11:05", "subject": "История",    "type": "сем.", "room": "202"},
]
ws = _get_user_slots_today(window_student)
assert len(ws) == 2
msg_win = _format_user_notification(LESSONS_SCHEDULE[0], window_student[0], ws)
print(msg_win)
assert "окно" in msg_win
assert "10:15" in msg_win
print("✅ PASSED\n")

print("=== Тест 5: 4-я пара (30 мин перерыв → большой перерыв) ===")
four_lesson_student = [
    {"day": "Вторник", "time": "11:15-12:05", "subject": "Физика", "type": "лек.", "room": "А-1"},
    {"day": "Вторник", "time": "12:35-13:25", "subject": "Химия",  "type": "пр.",  "room": "А-2"},
]
slot4 = LESSONS_SCHEDULE[3]
m4 = [it for it in four_lesson_student if _matches_lesson_slot(it, slot4)]
assert len(m4) == 1
ws4 = _get_user_slots_today(four_lesson_student)
msg4 = _format_user_notification(slot4, m4[0], ws4)
print(msg4)
assert "большой перерыв" in msg4
assert "Химия" in msg4
print("✅ PASSED\n")

print("✅ ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
