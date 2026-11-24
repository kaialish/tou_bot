"""
Маршруты панели администратора WebApp.
"""
from aiohttp import web

from src.config import ADMIN_IDS, get_kz_now
from src.database import (
    get_users_stats,
    is_maintenance_active,
    set_maintenance_status,
)


async def handle_admin_stats(request: web.Request) -> web.Response:
    """Возвращает системную и пользовательскую статистику для админ-панели Mini App."""
    user_id_param = request.query.get("user_id", "")
    is_demo = request.query.get("demo", "") == "1" or user_id_param == "demo"
    user_id = int(user_id_param) if user_id_param.isdigit() else None

    if not is_demo and (not user_id or user_id not in ADMIN_IDS):
        return web.json_response({"status": "error", "message": "Доступ запрещен"}, status=403)

    count, logins = await get_users_stats()
    maint = await is_maintenance_active()
    now_kz = get_kz_now().strftime("%d.%m.%Y в %H:%M:%S")

    return web.json_response({
        "status": "ok",
        "total_users": count,
        "logins": logins,
        "is_maintenance": maint,
        "server_time": now_kz,
        "admin_id": user_id or "demo"
    })


async def handle_admin_toggle_maintenance(request: web.Request) -> web.Response:
    """Переключает статус технического обслуживания через админ-панель Mini App."""
    user_id_param = request.query.get("user_id", "")
    is_demo = request.query.get("demo", "") == "1" or user_id_param == "demo"
    user_id = int(user_id_param) if user_id_param.isdigit() else None

    if not is_demo and (not user_id or user_id not in ADMIN_IDS):
        return web.json_response({"status": "error", "message": "Доступ запрещен"}, status=403)

    cur = await is_maintenance_active()
    new_status = not cur
    await set_maintenance_status(new_status)

    return web.json_response({
        "status": "ok",
        "is_maintenance": new_status,
        "message": "Режим техобслуживания активирован" if new_status else "Режим техобслуживания отключен"
    })
