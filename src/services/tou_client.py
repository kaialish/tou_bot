import httpx
from aiogram import Bot
from src.config import get_headers, LOGIN_URL, SCHEDULE_URL
from src.services.admin_alerts import notify_portal_incident

PORTAL_DOWN_MESSAGE = (
    "⚠️ <b>Портал ToU временно недоступен</b>\n\n"
    "К сожалению, в данный момент официальный портал ToU (tou.edu.kz) временно лёг "
    "или на сервере проводятся технические работы.\n\n"
    "Сервер университета не отвечает на запросы. Пожалуйста, попробуйте повторить попытку позже."
)


async def get_schedule_html(login: str, password: str, bot: Bot | None = None) -> tuple[bool, str]:
    """
    Авторизуется на портале ToU и возвращает HTML страницы расписания (mod=rasp).
    Возвращает (True, html) при успехе или (False, сообщение_об_ошибке).
    При сбоях портала автоматически уведомляет администраторов через bot.
    """
    headers = get_headers("random")
    payload = {"role": "student", "user": login, "password": password}

    # Оптимизированный таймаут: 7s на чтение, 5s на подключение
    timeout = httpx.Timeout(7.0, connect=5.0)

    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=timeout) as client:
            # 1. Отправляем форму авторизации
            login_res = await client.post(LOGIN_URL, data=payload)

            # Проверяем, если сервер университета вернул ошибку 5xx (500, 502, 503, 504)
            if login_res.status_code >= 500:
                if bot:
                    await notify_portal_incident(bot, is_down=True, reason=f"HTTP {login_res.status_code} на авторизации")
                return False, PORTAL_DOWN_MESSAGE

            if login_res.status_code != 200:
                return False, f"⚠️ Сервер ToU ответил с кодом: {login_res.status_code}. Возможно, на сайте ведутся технические работы."

            # 2. Переходим на страницу расписания
            res = await client.get(SCHEDULE_URL)

            if res.status_code >= 500:
                if bot:
                    await notify_portal_incident(bot, is_down=True, reason=f"HTTP {res.status_code} при загрузке расписания")
                return False, PORTAL_DOWN_MESSAGE

            if "schedule-table" in res.text or "Выход" in res.text:
                if bot:
                    await notify_portal_incident(bot, is_down=False)
                return True, res.text
            else:
                return False, "❌ Не удалось войти в систему. Проверьте правильность логина и пароля."

    except (httpx.TimeoutException, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
        if bot:
            await notify_portal_incident(bot, is_down=True, reason=f"Таймаут подключения: {type(e).__name__}")
        return False, PORTAL_DOWN_MESSAGE
    except (httpx.ConnectError, httpx.NetworkError) as e:
        if bot:
            await notify_portal_incident(bot, is_down=True, reason=f"Сетевая ошибка: {type(e).__name__}")
        return False, PORTAL_DOWN_MESSAGE
    except Exception as e:
        return False, f"⚠️ Ошибка при обращении к сайту ToU:\n<code>{e}</code>\n\nВозможно, портал временно недоступен."
