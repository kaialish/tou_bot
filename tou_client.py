import httpx
from config import get_headers, LOGIN_URL, SCHEDULE_URL

async def get_schedule_html(login: str, password: str) -> tuple[bool, str]:
    """
    Авторизуется на портале ToU и возвращает HTML страницы расписания (mod=rasp).
    Возвращает (True, html) при успехе или (False, сообщение_об_ошибке).
    """
    headers = get_headers("random")
    payload = {"role": "student", "user": login, "password": password}

    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        try:
            await client.post(LOGIN_URL, data=payload)
            res = await client.get(SCHEDULE_URL)

            # Сохраняем для отладки
            with open("debug_schedule.html", "w", encoding="utf-8") as f:
                f.write(res.text)

            if "schedule-table" in res.text or "Выход" in res.text:
                return True, res.text
            else:
                return False, "Не удалось открыть расписание. Проверьте логин и пароль."

        except Exception as e:
            return False, f"Ошибка сети: {e}"