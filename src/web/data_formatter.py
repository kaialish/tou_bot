"""
Форматирование расписания, журнала успеваемости и генерация демо-данных для WebApp API.
"""
from src.config import get_kz_now
from src.services.parser import (
    parse_schedule_items,
    parse_key_dates,
    _calc_course_real_tu,
    _format_score,
    _get_traffic_light,
    _get_part_week_range,
)
from src.utils.lesson_widget import get_current_lesson_status

WEEKDAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]


def format_schedule_for_api(schedule_html: str) -> dict[str, list[dict]]:
    """Парсит HTML расписания и группирует по дням недели."""
    all_items = parse_schedule_items(schedule_html, day="week")
    grouped: dict[str, list[dict]] = {day: [] for day in WEEKDAYS}

    for idx, item in enumerate(all_items, start=1):
        day_raw = item.get("day", "").strip()
        matched_day = None
        for w in WEEKDAYS:
            if w.lower() in day_raw.lower():
                matched_day = w
                break
        if matched_day:
            grouped[matched_day].append({
                "number": idx,
                "time": item.get("time", ""),
                "subject": item.get("subject", ""),
                "type": item.get("type", ""),
                "room": item.get("room", ""),
                "teacher": item.get("teacher", ""),
            })

    # Сортируем пары по времени/номеру внутри каждого дня
    for day in grouped:
        for i, lesson in enumerate(grouped[day], start=1):
            lesson["number"] = i

    return grouped


def format_grades_for_api(zhurnal_dict: dict) -> dict:
    """Форматирует журнал для удобного рендеринга на фронтенде с разделением по рейтингам."""
    courses = zhurnal_dict.get("courses", [])
    current_week = zhurnal_dict.get("current_week", 9)
    formatted_courses = []

    for c in courses:
        title = c.get("title", "")
        teachers = c.get("teachers", [])
        data = c.get("data") or {}
        activities = data.get("activities", [])
        summary = data.get("summary", {})

        # Рейтинг 1 (недели 1-8)
        tu1_val, has1 = _calc_course_real_tu(activities, current_week, fallback_tu=summary.get("tu1", ""), part=1)
        r1_traffic = _get_traffic_light(tu1_val, current_week=min(current_week, 8), has_any_grade=has1)

        # Рейтинг 2 (недели 9-15)
        tu2_val, has2 = _calc_course_real_tu(activities, current_week, fallback_tu=summary.get("tu2", ""), part=2)
        elapsed2 = len(_get_part_week_range(current_week, 2))
        r2_traffic = _get_traffic_light(tu2_val, current_week=elapsed2, has_any_grade=has2)

        # Разделение активностей по рейтингам
        part1_activities = []
        part2_activities = []

        for act in activities:
            raw_type = act.get("type", "")
            r1_grades = act.get("r1_grades", [])
            r2_grades = act.get("r2_grades", [])

            # Недели 1 рейтинга (1–8)
            p1_weeks = []
            for g in r1_grades:
                w_str = str(g.get("week", ""))
                val_str = str(g.get("grade", "")).strip()
                if val_str:
                    p1_weeks.append({"week": w_str, "val": _format_score(val_str)})

            part1_activities.append({
                "type": raw_type,
                "avg": _format_score(act.get("r1_avg") or "0"),
                "weeks": p1_weeks,
            })

            # Недели 2 рейтинга (9–15)
            p2_weeks = []
            for g in r2_grades:
                w_str = str(g.get("week", ""))
                val_str = str(g.get("grade", "")).strip()
                if val_str:
                    p2_weeks.append({"week": w_str, "val": _format_score(val_str)})

            part2_activities.append({
                "type": raw_type,
                "avg": _format_score(act.get("r2_avg") or "0"),
                "weeks": p2_weeks,
            })

        formatted_courses.append({
            "title": title,
            "teachers": teachers,
            "part1": {
                "tu": _format_score(tu1_val) if tu1_val is not None else "—",
                "rk": _format_score(summary.get("rk1", "")) or "—",
                "rating": _format_score(summary.get("r1", "")) or "—",
                "traffic": r1_traffic,
                "activities": part1_activities,
            },
            "part2": {
                "tu": _format_score(tu2_val) if tu2_val is not None else "—",
                "rk": _format_score(summary.get("rk2", "")) or "—",
                "rating": _format_score(summary.get("r2", "")) or "—",
                "traffic": r2_traffic,
                "activities": part2_activities,
            },
            "activities": part1_activities if current_week < 9 else part2_activities,
        })

    return {
        "current_week": current_week,
        "courses": formatted_courses,
    }


def build_demo_payload() -> dict:
    """Формирует реалистичный демонстрационный набор данных для демо-режима."""
    demo_schedule = {
        "Понедельник": [
            {"number": 1, "time": "08:15-09:05", "subject": "Архитектура компьютерных систем", "type": "лек.", "room": "А-7", "teacher": "ст.преп. Самуратов А.Т."},
            {"number": 2, "time": "09:15-10:05", "subject": "Архитектура компьютерных систем", "type": "пр.", "room": "А-308", "teacher": "ст.преп. Самуратов А.Т."},
            {"number": 3, "time": "10:15-11:05", "subject": "Иностранный язык (профессиональный)", "type": "пр.", "room": "Б-105", "teacher": "доц. Смагулова Г.К."},
        ],
        "Вторник": [
            {"number": 1, "time": "10:15-11:05", "subject": "Объектно-ориентированное программирование (Java)", "type": "пр./сем.", "room": "А-406", "teacher": "Айтбаева К. Ж."},
            {"number": 2, "time": "11:15-12:05", "subject": "Объектно-ориентированное программирование (Java)", "type": "пр./сем.", "room": "А-406", "teacher": "Айтбаева К. Ж."},
            {"number": 3, "time": "12:35-13:25", "subject": "Системы управления базами данных", "type": "пр./сем.", "room": "А-404", "teacher": "Айтбаева К. Ж."},
            {"number": 4, "time": "13:35-14:25", "subject": "Системы управления базами данных", "type": "лаб.", "room": "А-404", "teacher": "Айтбаева К. Ж."},
        ],
        "Среда": [
            {"number": 1, "time": "08:15-09:05", "subject": "Алгоритмы и структуры данных", "type": "лек.", "room": "А-9", "teacher": "доц. Ахметов Т.С."},
            {"number": 2, "time": "09:15-10:05", "subject": "Алгоритмы и структуры данных", "type": "пр.", "room": "А-315", "teacher": "преп. Касимова А.А."},
            {"number": 3, "time": "10:15-11:05", "subject": "Web-разработка и фреймворки", "type": "лек.", "room": "А-7", "teacher": "преп. Муратов Е.Е."},
        ],
        "Четверг": [
            {"number": 1, "time": "09:15-10:05", "subject": "Компьютерные сети", "type": "лек.", "room": "А-7", "teacher": "ст.преп. Самуратов А.Т."},
            {"number": 2, "time": "10:15-11:05", "subject": "Компьютерные сети", "type": "лаб.", "room": "Б-204", "teacher": "Сейткалиев М.Б."},
            {"number": 3, "time": "11:15-12:05", "subject": "Операционные системы", "type": "пр.", "room": "А-410", "teacher": "преп. Оспанов Д.К."},
        ],
        "Пятница": [
            {"number": 1, "time": "10:15-11:05", "subject": "Веб-технологии", "type": "лек.", "room": "А-7", "teacher": "преп. Муратов Е.Е."},
            {"number": 2, "time": "11:15-12:05", "subject": "Веб-технологии", "type": "лаб.", "room": "А-318", "teacher": "преп. Муратов Е.Е."},
        ],
    }

    now_kz = get_kz_now()
    weekday_idx = now_kz.weekday()
    day_name = WEEKDAYS[weekday_idx] if weekday_idx < len(WEEKDAYS) else None
    today_lessons = demo_schedule.get(day_name, []) if day_name else []

    live_status = get_current_lesson_status(today_lessons=today_lessons)
    user_num = live_status.get("user_lesson_number") or live_status.get("slot", {}).get("number", 0)
    bell_num = live_status.get("bell_slot_number") or live_status.get("slot", {}).get("number", 0)

    live_widget = {
        "status": live_status.get("status", "no_lessons_today"),
        "lesson_number": user_num,
        "bell_slot_number": bell_num,
        "start": live_status.get("slot", {}).get("start", ""),
        "end": live_status.get("slot", {}).get("end", ""),
        "subject": live_status.get("lesson", {}).get("subject", ""),
        "type": live_status.get("lesson", {}).get("type", ""),
        "room": live_status.get("lesson", {}).get("room", ""),
        "teacher": live_status.get("lesson", {}).get("teacher", ""),
        "remaining_minutes": live_status.get("remaining_minutes", 0),
        "break_duration": live_status.get("break_duration", 10),
        "next_subject": live_status.get("next_lesson", {}).get("subject", "") if live_status.get("next_lesson") else "",
        "next_room": live_status.get("next_lesson", {}).get("room", "") if live_status.get("next_lesson") else "",
        "next_lesson_number": live_status.get("next_user_lesson_number") or 0,
    }

    demo_grades = {
        "current_week": 9,
        "courses": [
            {
                "title": "Объектно-ориентированное программирование (Java)",
                "teachers": [{"type": "Практика", "fio": "Айтбаева К. Ж."}],
                "part1": {
                    "tu": "88.5", "rk": "90", "rating": "89.2", "traffic": "🟢",
                    "activities": [
                        {"type": "Практика", "avg": "88.5", "weeks": [{"week": 1, "val": "85"}, {"week": 2, "val": "90"}, {"week": 3, "val": "88"}, {"week": 5, "val": "91"}]}
                    ]
                },
                "part2": {
                    "tu": "92.0", "rk": "—", "rating": "—", "traffic": "🟢",
                    "activities": [
                        {"type": "Практика", "avg": "92.0", "weeks": [{"week": 9, "val": "92"}]}
                    ]
                }
            },
            {
                "title": "Компьютерные сети",
                "teachers": [{"type": "Лекция", "fio": "Самуратов А. Т."}, {"type": "Лабораторные", "fio": "Сейткалиев М. Б."}],
                "part1": {
                    "tu": "84.5", "rk": "85", "rating": "85.0", "traffic": "🟢",
                    "activities": [
                        {"type": "Лекции", "avg": "88.0", "weeks": [{"week": 1, "val": "90"}, {"week": 2, "val": "85"}, {"week": 3, "val": "90"}]},
                        {"type": "Лабораторные", "avg": "81.0", "weeks": [{"week": 1, "val": "80"}, {"week": 2, "val": "82"}]}
                    ]
                },
                "part2": {
                    "tu": "90.0", "rk": "—", "rating": "—", "traffic": "🟢",
                    "activities": [
                        {"type": "Лекции", "avg": "95.0", "weeks": [{"week": 9, "val": "95"}]},
                        {"type": "Лабораторные", "avg": "85.0", "weeks": [{"week": 9, "val": "85"}]}
                    ]
                }
            },
            {
                "title": "Системы управления базами данных",
                "teachers": [{"type": "Лабораторные", "fio": "Айтбаева К. Ж."}],
                "part1": {
                    "tu": "74.0", "rk": "72", "rating": "73.0", "traffic": "🟢",
                    "activities": [
                        {"type": "Лабораторные", "avg": "74.0", "weeks": [{"week": 1, "val": "75"}, {"week": 2, "val": "70"}, {"week": 4, "val": "77"}]}
                    ]
                },
                "part2": {
                    "tu": "68.0", "rk": "—", "rating": "—", "traffic": "🟠",
                    "activities": [
                        {"type": "Лабораторные", "avg": "68.0", "weeks": [{"week": 9, "val": "68"}]}
                    ]
                }
            }
        ]
    }

    demo_checks = [
        {"name": "Допуск к экзаменам", "value": "Допущен", "indicator": "positive"},
        {"name": "Текущая успеваемость", "value": "В норме (выше 50)", "indicator": "positive"},
        {"name": "Задолженности", "value": "Отсутствуют", "indicator": "positive"},
        {"name": "Флюорография", "value": "до 25.12.2026", "indicator": "positive"},
    ]

    key_dates = parse_key_dates("")

    return {
        "student": {
            "name": "Демо Студент",
            "login": "demo_student",
            "status_overall": "В норме",
            "current_week": 9,
            "is_demo": True,
            "is_offline": False,
            "is_admin": True,
        },
        "settings": {
            "notifications_enabled": True,
            "notify_mook": False,
        },
        "live_widget": live_widget,
        "schedule": demo_schedule,
        "grades": demo_grades,
        "status_checks": demo_checks,
        "key_dates": key_dates,
    }
