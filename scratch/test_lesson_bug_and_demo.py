import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from src.utils.lesson_widget import get_current_lesson_status, format_current_lesson_message
from src.webapp_server import _build_demo_payload
from datetime import datetime
from unittest.mock import patch

# Имитируем расписание со скриншота пользователя: Вторник, 6 пар
# 1-я пара: 10:15 - 11:05 (Java)
# 2-я пара: 11:15 - 12:05 (Java)
# 3-я пара: 12:35 - 13:25 (СУБД)
today_lessons = [
    {"day": "Вторник", "time": "10:15-11:05", "subject": "Объектно-ориентированное программирование (Java)", "type": "пр./сем.", "room": "А-406", "teacher": "Айтбаева К. Ж."},
    {"day": "Вторник", "time": "11:15-12:05", "subject": "Объектно-ориентированное программирование (Java)", "type": "пр./сем.", "room": "А-406", "teacher": "Айтбаева К. Ж."},
    {"day": "Вторник", "time": "12:35-13:25", "subject": "Системы управления базами данных", "type": "пр./сем.", "room": "А-404", "teacher": "Айтбаева К. Ж."},
    {"day": "Вторник", "time": "13:35-14:25", "subject": "Системы управления базами данных", "type": "лаб.", "room": "А-404", "teacher": "Айтбаева К. Ж."},
    {"day": "Вторник", "time": "14:35-15:25", "subject": "Сетевые технологии", "type": "пр.", "room": "А-308", "teacher": "Самуратов А.Т."},
    {"day": "Вторник", "time": "15:35-16:25", "subject": "Сетевые технологии", "type": "лаб.", "room": "А-308", "teacher": "Самуратов А.Т."},
]

# Имитируем время со скриншота: Вторник, 11:04
fake_now = datetime(2026, 11, 10, 11, 4, 0) # Tuesday 11:04

with patch("src.utils.lesson_widget.get_kz_now", return_value=fake_now):
    status = get_current_lesson_status(today_lessons=today_lessons)
    print("STATUS RESULT:")
    print("status:", status.get("status"))
    print("user_lesson_number:", status.get("user_lesson_number"))
    print("bell_slot_number:", status.get("bell_slot_number"))
    print("remaining_minutes:", status.get("remaining_minutes"))
    print("lesson subject:", status.get("lesson", {}).get("subject"))
    print("next_user_lesson_number:", status.get("next_user_lesson_number"))
    print("next subject:", status.get("next_lesson", {}).get("subject"))

    formatted_msg = format_current_lesson_message(status)
    print("\nFORMATTED BOT MESSAGE:\n", formatted_msg)

    assert status.get("status") == "in_lesson", f"Expected in_lesson, got {status.get('status')}"
    assert status.get("user_lesson_number") == 1, f"Expected user_lesson_number=1, got {status.get('user_lesson_number')}"
    assert status.get("bell_slot_number") == 3, f"Expected bell_slot_number=3, got {status.get('bell_slot_number')}"
    assert status.get("remaining_minutes") == 1, f"Expected 1 min, got {status.get('remaining_minutes')}"

print("\n--- Testing Demo Payload ---")
demo = _build_demo_payload()
assert "student" in demo
assert demo["student"]["is_demo"] is True
assert "schedule" in demo
assert "Вторник" in demo["schedule"]
assert demo["schedule"]["Вторник"][0]["number"] == 1
assert demo["schedule"]["Вторник"][1]["number"] == 2
assert demo["schedule"]["Вторник"][2]["number"] == 3
print("Demo payload test PASSED!")

