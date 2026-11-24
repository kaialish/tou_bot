"""
Маршруты настроек пользователя: уведомления, MOOK, удаление аккаунта и политика конфиденциальности.
"""
from aiohttp import web

from src.database import (
    is_user_subscribed,
    subscribe_to_notifications,
    unsubscribe_from_notifications,
    toggle_user_mook_setting,
    delete_user_account,
)
from src.utils.texts import PRIVACY_POLICY_TEXT


async def handle_settings_toggle_notifications(request: web.Request) -> web.Response:
    """Включение/выключение уведомлений о парах из Mini App."""
    try:
        data = await request.json()
    except Exception:
        data = {}
    user_id_raw = data.get("user_id") or request.query.get("user_id")
    user_id = int(user_id_raw) if str(user_id_raw).isdigit() else None
    if not user_id:
        return web.json_response({"success": False, "error": "user_id required"}, status=400)

    current_sub = await is_user_subscribed(user_id)
    if current_sub:
        await unsubscribe_from_notifications(user_id)
        new_val = False
    else:
        await subscribe_to_notifications(user_id)
        new_val = True

    return web.json_response({"success": True, "notifications_enabled": new_val})


async def handle_settings_toggle_mook(request: web.Request) -> web.Response:
    """Включение/выключение уведомлений о парах MOOK (дистант) из Mini App."""
    try:
        data = await request.json()
    except Exception:
        data = {}
    user_id_raw = data.get("user_id") or request.query.get("user_id")
    user_id = int(user_id_raw) if str(user_id_raw).isdigit() else None
    if not user_id:
        return web.json_response({"success": False, "error": "user_id required"}, status=400)

    new_val = await toggle_user_mook_setting(user_id)
    return web.json_response({"success": True, "notify_mook": new_val})


async def handle_settings_delete_account(request: web.Request) -> web.Response:
    """Удаление аккаунта и кэша студента по запросу из Mini App."""
    try:
        data = await request.json()
    except Exception:
        data = {}
    user_id_raw = data.get("user_id") or request.query.get("user_id")
    user_id = int(user_id_raw) if str(user_id_raw).isdigit() else None
    if not user_id:
        return web.json_response({"success": False, "error": "user_id required"}, status=400)

    deleted = await delete_user_account(user_id)
    return web.json_response({"success": deleted})


async def handle_privacy_policy(request: web.Request) -> web.Response:
    """Возвращает текст политики конфиденциальности для модального окна Mini App."""
    return web.json_response({"policy": PRIVACY_POLICY_TEXT})
