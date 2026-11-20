from src.utils.lesson_widget import get_current_lesson_status, format_current_lesson_message

mock_lessons = [
    {
        "subject": "Базы данных",
        "type": "лаб.",
        "room": "А-312",
        "teacher": "Жумадилов А.К.",
        "day": "Четверг",
        "time": "12:35-13:25"
    },
    {
        "subject": "Компьютерные сети",
        "type": "пр.",
        "room": "Б-204",
        "teacher": "Сейткалиев М.Б.",
        "day": "Четверг",
        "time": "13:35-14:25"
    }
]

status = get_current_lesson_status(today_lessons=mock_lessons)
msg = format_current_lesson_message(status)
print("=== CURRENT ACTIVE LESSON MESSAGE ===")
print(msg)
