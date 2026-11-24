"""
Маршруты студенческих данных: главная страница, расписание, журнал, аватарка и обновление.
"""
import json
import re
import time
from pathlib import Path

import aiohttp
from aiohttp import web

from src.config import PROJECT_ROOT, get_kz_now, ADMIN_IDS, BOT_TOKEN
from src.database import (
    get_user_credentials,
    get_cached_schedule,
    save_cached_schedule,
    get_cached_zhurnal,
    save_cached_zhurnal,
    get_cached_academic_status,
    save_cached_academic_status,
    is_user_subscribed,
    get_user_mook_setting,
)
from src.services.parser import (
    parse_schedule_items,
    parse_academic_status,
    parse_zhurnal,
    parse_key_dates,
)
from src.services.tou_client import get_schedule_html, get_zhurnal_html, get_dashboard_html
from src.utils.lesson_widget import get_current_lesson_status
from src.utils.rate_limit import check_rate_limit, update_rate_limit
from src.web.data_formatter import format_schedule_for_api, format_grades_for_api, build_demo_payload

WEBAPP_DIR = PROJECT_ROOT / "webapp"
_AVATAR_CACHE: dict[int, tuple[bytes, str, float]] = {}


async def handle_index(request: web.Request) -> web.FileResponse:
    """Отдает главную страницу webapp/index.html с заголовками против кэширования для мгновенного обновления."""
    return web.FileResponse(
        WEBAPP_DIR / "index.html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )


async def handle_student_data(request: web.Request) -> web.Response:
    """Возвращает агрегированный JSON с расписанием, статусом и успеваемостью."""
    user_id_param = request.query.get("user_id", "")
    is_demo = request.query.get("demo", "") == "1" or user_id_param == "demo"
    user_id = int(user_id_param) if user_id_param.isdigit() else None

    if is_demo or not user_id:
        return web.json_response(build_demo_payload())

    if user_id:
        cached_schedule_res = await get_cached_schedule(user_id)
        cached_zhurnal_res = await get_cached_zhurnal(user_id)
        cached_status_res = await get_cached_academic_status(user_id)
        creds = await get_user_credentials(user_id)

        if not cached_schedule_res and not creds:
            return web.json_response(build_demo_payload())

        login = creds[0] if creds else f"ID: {user_id}"

        # 1. Расписание
        schedule_html = cached_schedule_res[0] if cached_schedule_res else ""
        schedule_grouped = format_schedule_for_api(schedule_html) if schedule_html else {}

        # 2. Виджет текущей пары
        now_lessons = parse_schedule_items(schedule_html, day="today") if schedule_html else []
        live_status = get_current_lesson_status(today_lessons=now_lessons)

        user_lesson_num = live_status.get("user_lesson_number") or live_status.get("slot", {}).get("number", 0)
        bell_slot_num = live_status.get("bell_slot_number") or live_status.get("slot", {}).get("number", 0)

        live_widget = {
            "status": live_status.get("status", "no_lessons_today"),
            "lesson_number": user_lesson_num,
            "bell_slot_number": bell_slot_num,
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
        grades_data = format_grades_for_api(zhurnal_dict)

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
            if "флюорограф" in name.lower() or "флюрограф" in name.lower():
                date_match = re.search(r'(\d{2}[./-]\d{2}[./-]\d{2,4})', val)
                if date_match:
                    val = f"до {date_match.group(1).replace('-', '.').replace('/', '.')}"

            status_checks.append({
                "name": name,
                "value": val,
                "indicator": item.get("indicator", "neutral")
            })

        key_dates = parse_key_dates("")

        is_admin = bool(user_id and user_id in ADMIN_IDS)
        is_sub = await is_user_subscribed(user_id) if user_id else True
        notify_mook = await get_user_mook_setting(user_id) if user_id else False

        last_updated = ""
        if cached_schedule_res and len(cached_schedule_res) > 1:
            last_updated = cached_schedule_res[1]
        elif cached_zhurnal_res and len(cached_zhurnal_res) > 1:
            last_updated = cached_zhurnal_res[1]

        is_offline = request.query.get("offline") == "1" or bool(request.get("is_offline", False))

        payload = {
            "student": {
                "name": login,
                "login": login,
                "status_overall": status_dict.get("status_badge", "В норме"),
                "current_week": grades_data.get("current_week", 9),
                "is_demo": False,
                "is_offline": is_offline,
                "last_updated": last_updated,
                "is_admin": is_admin,
            },
            "settings": {
                "notifications_enabled": bool(is_sub),
                "notify_mook": bool(notify_mook),
            },
            "live_widget": live_widget,
            "schedule": schedule_grouped,
            "grades": grades_data,
            "status_checks": status_checks,
            "key_dates": key_dates,
        }
        return web.json_response(payload)

    return web.json_response(build_demo_payload())


async def handle_refresh(request: web.Request) -> web.Response:
    """Принудительно обновляет данные с портала ToU и сохраняет в БД с защитой от спам-запросов (Rate Limit)."""
    user_id_param = request.query.get("user_id", "")
    is_demo = request.query.get("demo", "") == "1" or user_id_param == "demo"

    if is_demo or not user_id_param or not user_id_param.isdigit():
        return web.json_response(build_demo_payload())

    user_id = int(user_id_param)

    can_refresh, _ = check_rate_limit(user_id, action="webapp_refresh", cooldown_seconds=60)
    if not can_refresh:
        return await handle_student_data(request)

    creds = await get_user_credentials(user_id)
    if not creds:
        return web.json_response({"status": "error", "message": "Студент не авторизован в боте"})

    update_rate_limit(user_id, action="webapp_refresh")

    login, password = creds
    now_str = get_kz_now().strftime("%d.%m.%Y в %H:%M")

    ok_s, s_html = await get_schedule_html(login, password)
    if ok_s:
        await save_cached_schedule(user_id, s_html, now_str)

    ok_z, z_html = await get_zhurnal_html(login, password)
    if ok_z:
        zhurnal_data = parse_zhurnal(z_html)
        await save_cached_zhurnal(user_id, json.dumps(zhurnal_data, ensure_ascii=False), now_str)

    ok_d, d_html = await get_dashboard_html(login, password)
    if ok_d:
        status_data = parse_academic_status(d_html)
        await save_cached_academic_status(user_id, json.dumps(status_data, ensure_ascii=False), now_str)

    if not (ok_s or ok_z or ok_d):
        request["is_offline"] = True

    return await handle_student_data(request)


async def handle_user_avatar(request: web.Request) -> web.Response:
    """Возвращает текущую аватарку пользователя из Telegram Bot API с кэшированием."""
    user_id_param = request.query.get("user_id", "")
    if not user_id_param.isdigit():
        return web.Response(status=404)

    user_id = int(user_id_param)
    now = time.time()
    if user_id in _AVATAR_CACHE and (now - _AVATAR_CACHE[user_id][2] < 3600):
        data, ctype, _ = _AVATAR_CACHE[user_id]
        return web.Response(body=data, content_type=ctype)

    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUserProfilePhotos?user_id={user_id}&limit=1"
            async with session.get(url, timeout=5) as r:
                if r.status != 200:
                    return web.Response(status=404)
                resp = await r.json()
                photos = resp.get("result", {}).get("photos", [])
                if not photos or not photos[0]:
                    return web.Response(status=404)
                photo_item = photos[0][1] if len(photos[0]) > 1 else photos[0][0]
                file_id = photo_item["file_id"]

            url2 = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
            async with session.get(url2, timeout=5) as r2:
                if r2.status != 200:
                    return web.Response(status=404)
                resp2 = await r2.json()
                file_path = resp2.get("result", {}).get("file_path")
                if not file_path:
                    return web.Response(status=404)

            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            async with session.get(file_url, timeout=5) as r3:
                if r3.status == 200:
                    img_data = await r3.read()
                    ctype = r3.headers.get("Content-Type", "image/jpeg")
                    if "octet-stream" in ctype or not ctype:
                        ctype = "image/jpeg"
                    _AVATAR_CACHE[user_id] = (img_data, ctype, now)
                    return web.Response(body=img_data, content_type=ctype)
    except Exception as e:
        print(f"Ошибка загрузки аватарки для {user_id}: {e}")

    return web.Response(status=404)
