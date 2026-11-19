"""
Легковесный асинхронный веб-сервер и API для ToU Telegram Mini App.
Построен на aiohttp (уже входит в зависимости проекта).
Позволяет отдавать статику Mini App и JSON API для расписания и оценок.
"""
import os
import sys
import json
import re
from pathlib import Path

# Гарантируем, что корень проекта всегда в sys.path при прямом запуске скрипта
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from aiohttp import web
from src.config import PROJECT_ROOT, get_kz_now
from src.database import (
    init_db,
    get_user_credentials,
    get_cached_schedule,
    save_cached_schedule,
    get_cached_zhurnal,
    save_cached_zhurnal,
    get_cached_academic_status,
    save_cached_academic_status,
)
from src.services.parser import (
    parse_schedule_items,
    parse_academic_status,
    parse_zhurnal,
    parse_key_dates,
    extract_current_week,
    _calc_course_real_tu,
    _format_score,
    _get_traffic_light,
    _get_part_week_range,
    _filter_grades_by_current_week,
)
from src.services.tou_client import get_schedule_html, get_zhurnal_html, get_dashboard_html
from src.utils.lesson_widget import get_current_lesson_status

WEBAPP_DIR = PROJECT_ROOT / "webapp"

WEEKDAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]


def _format_schedule_for_api(schedule_html: str) -> dict[str, list[dict]]:
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


def _format_grades_for_api(zhurnal_dict: dict) -> dict:
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

        # Разделение активностей по рейтингам:
        # Для 1 рейтинга — только недели 1-8 и средний балл Р1
        part1_activities = []
        # Для 2 рейтинга — только недели 9-15 и средний балл Р2
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
            # Фолбэк для обратной совместимости
            "activities": part1_activities if current_week < 9 else part2_activities,
        })

    return {
        "current_week": current_week,
        "courses": formatted_courses,
    }


def _build_demo_payload() -> dict:
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

    # Рассчитываем динамический live_widget для сегодняшнего дня
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
        },
        "live_widget": live_widget,
        "schedule": demo_schedule,
        "grades": demo_grades,
        "status_checks": demo_checks,
        "key_dates": key_dates,
    }


async def handle_student_data(request: web.Request) -> web.Response:
    """Возвращает агрегированный JSON с расписанием, статусом и успеваемостью."""
    user_id_param = request.query.get("user_id", "")
    is_demo = request.query.get("demo", "") == "1" or user_id_param == "demo"
    
    # Пытаемся преобразовать в int Telegram ID
    user_id = int(user_id_param) if user_id_param.isdigit() else None

    # Если запрошен явный демо-режим или user_id отсутствует
    if is_demo or not user_id:
        return web.json_response(_build_demo_payload())

    # Если передан валидный ID студента в базе данных
    if user_id:
        cached_schedule_res = await get_cached_schedule(user_id)
        cached_zhurnal_res = await get_cached_zhurnal(user_id)
        cached_status_res = await get_cached_academic_status(user_id)
        creds = await get_user_credentials(user_id)

        # Если у пользователя нет сохраненных данных в БД, отдаем демо-версию
        if not cached_schedule_res and not creds:
            return web.json_response(_build_demo_payload())

        login = creds[0] if creds else f"ID: {user_id}"

        # 1. Расписание
        schedule_html = cached_schedule_res[0] if cached_schedule_res else ""
        schedule_grouped = _format_schedule_for_api(schedule_html) if schedule_html else {}

        # 2. Виджет текущей пары
        now_lessons = parse_schedule_items(schedule_html, day="today") if schedule_html else []
        live_status = get_current_lesson_status(today_lessons=now_lessons)

        user_lesson_num = live_status.get("user_lesson_number") or live_status.get("slot", {}).get("number", 0)
        bell_slot_num = live_status.get("bell_slot_number") or live_status.get("slot", {}).get("number", 0)

        live_widget = {
            "status": live_status.get("status", "no_lessons_today"),
            "lesson_number": user_lesson_num,  # Порядковый номер пары в персональном расписании студента на сегодня
            "bell_slot_number": bell_slot_num,  # Номер слота по звонкам университета
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

        # 3. Успеваемость (Журнал)
        zhurnal_raw = cached_zhurnal_res[0] if cached_zhurnal_res else "{}"
        try:
            zhurnal_dict = json.loads(zhurnal_raw)
        except Exception:
            zhurnal_dict = {}
        grades_data = _format_grades_for_api(zhurnal_dict)

        # 4. Академический статус
        status_raw = cached_status_res[0] if cached_status_res else "{}"
        try:
            status_dict = json.loads(status_raw)
        except Exception:
            status_dict = {}

        status_checks = []
        for item in status_dict.get("items", []):
            name = item.get("name", "")
            val = item.get("value", "")
            # Оставляем только дату действия для флюорографии
            if "флюорограф" in name.lower() or "флюрограф" in name.lower():
                date_match = re.search(r'(\d{2}[./-]\d{2}[./-]\d{2,4})', val)
                if date_match:
                    val = f"до {date_match.group(1).replace('-', '.').replace('/', '.')}"

            status_checks.append({
                "name": name,
                "value": val,
                "indicator": item.get("indicator", "neutral")
            })

        # 5. Ключевые даты с рассчитанными днями
        key_dates = parse_key_dates("")

        payload = {
            "student": {
                "name": login,
                "login": login,
                "status_overall": status_dict.get("status_badge", "В норме"),
                "current_week": grades_data.get("current_week", 9),
                "is_demo": False,
                "is_offline": False,
            },
            "live_widget": live_widget,
            "schedule": schedule_grouped,
            "grades": grades_data,
            "status_checks": status_checks,
            "key_dates": key_dates,
        }
        return web.json_response(payload)

    # Резервный фолбэк
    return web.json_response(_build_demo_payload())


async def handle_refresh(request: web.Request) -> web.Response:
    """Принудительно обновляет данные с портала ToU и сохраняет в БД."""
    user_id_param = request.query.get("user_id", "")
    is_demo = request.query.get("demo", "") == "1" or user_id_param == "demo"

    if is_demo or not user_id_param or not user_id_param.isdigit():
        return web.json_response(_build_demo_payload())

    user_id = int(user_id_param)

    creds = await get_user_credentials(user_id)
    if not creds:
        return web.json_response({"status": "error", "message": "Студент не авторизован в боте"})

    login, password = creds
    now_str = get_kz_now().strftime("%d.%m.%Y в %H:%M")

    # Обновляем расписание
    ok_s, s_html = await get_schedule_html(login, password)
    if ok_s:
        await save_cached_schedule(user_id, s_html, now_str)

    # Обновляем журнал
    ok_z, z_html = await get_zhurnal_html(login, password)
    if ok_z:
        zhurnal_data = parse_zhurnal(z_html)
        await save_cached_zhurnal(user_id, json.dumps(zhurnal_data, ensure_ascii=False), now_str)

    # Обновляем статус
    ok_d, d_html = await get_dashboard_html(login, password)
    if ok_d:
        status_data = parse_academic_status(d_html)
        await save_cached_academic_status(user_id, json.dumps(status_data, ensure_ascii=False), now_str)

    # Возвращаем обновленный дамп
    return await handle_student_data(request)


async def handle_index(request: web.Request) -> web.FileResponse:
    """Отдает главную страницу webapp/index.html."""
    return web.FileResponse(WEBAPP_DIR / "index.html")


def create_app() -> web.Application:
    """Создает и настраивает экземпляр aiohttp приложения."""
    app = web.Application()

    # Маршруты API
    app.router.add_get("/", handle_index)
    app.router.add_get("/api/student-data", handle_student_data)
    app.router.add_get("/api/refresh", handle_refresh)

    # Раздача статики (index.html, app.js, mock_data.js)
    app.router.add_static("/static/", path=str(WEBAPP_DIR), name="static")

    return app


async def start_server(host: str = "0.0.0.0", port: int = 8080):
    """Асинхронный запуск сервера."""
    await init_db()
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    print(f"\n🚀 ToU Mini App сервер успешно запущен!")
    print(f"👉 Откройте в браузере: http://localhost:{port}")
    print(f"📱 Для Telegram пробросьте порт через Cloudflare Tunnel / ngrok\n")
    return runner


if __name__ == "__main__":
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def _main():
        await start_server(host="127.0.0.1", port=8080)
        # Держим процесс активным
        while True:
            await asyncio.sleep(3600)

    try:
        loop.run_until_complete(_main())
    except KeyboardInterrupt:
        print("\nСервер остановлен.")
