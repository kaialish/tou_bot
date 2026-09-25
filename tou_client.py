import httpx
from config import get_headers, LOGIN_URL, DASHBOARD_URL

async def get_dashboard_html(login: str, password: str) -> tuple[bool, str]:
    headers = get_headers("random")
    payload = {
        'role': 'student',
        'user': login,
        'password': password
    }
    
    # Использование сессии сохраняет куки между запросами
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        try:
            # 1. POST запрос на вход
            res_post = await client.post(LOGIN_URL, data=payload)
            
            # 2. GET запрос к дашборду
            res_dash = await client.get(DASHBOARD_URL)
            
            # Сохраняем дашборд для отладки
            with open("debug.html", "w", encoding="utf-8") as f:
                f.write(res_dash.text)
                
            if "student-card--schedule" in res_dash.text or "student-schedule-panel" in res_dash.text or "Выход" in res_dash.text:
                return True, res_dash.text
            else:
                return False, "Не удалось открыть дашборд. Проверьте логин и пароль."
                
        except Exception as e:
            return False, f"Ошибка сети: {e}"