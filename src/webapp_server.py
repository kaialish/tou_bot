"""
Легковесный асинхронный веб-сервер и API для ToU Telegram Mini App.
Построен на aiohttp.
Позволяет отдавать статику Mini App и JSON API для расписания и оценок.
"""
import sys
from pathlib import Path

# Гарантируем, что корень проекта всегда в sys.path при прямом запуске скрипта
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from aiohttp import web
from src.database import init_db
from src.web.routes_student import (
    handle_index,
    handle_student_data,
    handle_refresh,
    handle_user_avatar,
    WEBAPP_DIR,
)
from src.web.routes_admin import (
    handle_admin_stats,
    handle_admin_toggle_maintenance,
)
from src.web.routes_settings import (
    handle_settings_toggle_notifications,
    handle_settings_toggle_mook,
    handle_settings_delete_account,
    handle_privacy_policy,
)


def create_app() -> web.Application:
    """Создает и настраивает экземпляр aiohttp приложения."""
    app = web.Application()

    # Студенческие маршруты
    app.router.add_get("/", handle_index)
    app.router.add_get("/api/student-data", handle_student_data)
    app.router.add_get("/api/refresh", handle_refresh)
    app.router.add_get("/api/user-avatar", handle_user_avatar)

    # Админские маршруты
    app.router.add_get("/api/admin/stats", handle_admin_stats)
    app.router.add_post("/api/admin/toggle-maintenance", handle_admin_toggle_maintenance)
    app.router.add_get("/api/admin/toggle-maintenance", handle_admin_toggle_maintenance)

    # Настройки и приватность
    app.router.add_post("/api/settings/toggle-notifications", handle_settings_toggle_notifications)
    app.router.add_post("/api/settings/toggle-mook", handle_settings_toggle_mook)
    app.router.add_post("/api/settings/delete-account", handle_settings_delete_account)
    app.router.add_get("/api/privacy-policy", handle_privacy_policy)

    # Раздача статики (index.html, style.css, mock_data.js, js/...)
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
        while True:
            await asyncio.sleep(3600)

    try:
        loop.run_until_complete(_main())
    except KeyboardInterrupt:
        print("\nСервер остановлен.")
