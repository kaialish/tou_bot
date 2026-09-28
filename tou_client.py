import httpx
from config import get_headers, LOGIN_URL, SCHEDULE_URL


async def get_schedule_html(login: str, password: str) -> tuple[bool, str]:
    """
    Авторизуется на портале ToU и возвращает HTML страницы расписания (mod=rasp).
    Возвращает (True, html) при успехе или (False, сообщение_об_ошибке).
    """
    headers = get_headers("random")
    payload = {"role": "student", "user": login, "password": password}

    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=15.0) as client:
        try:
            # 1. Отправляем форму авторизации
            login_res = await client.post(LOGIN_URL, data=payload)
            if login_res.status_code != 200:
                return False, f"Сервер ответил с ошибкой: {login_res.status_code}"

            # 2. Переходим на страницу расписания
            res = await client.get(SCHEDULE_URL)

            if "schedule-table" in res.text or "Выход" in res.text:
                return True, res.text
            else:
                return False, "Не удалось открыть расписание. Проверьте логин и пароль."

        except httpx.TimeoutException:
            return False, "Превышено время ожидания ответа от портала ToU."
        except Exception as e:
            return False, f"Ошибка сети: {e}"