import os
from pathlib import Path
from dotenv import load_dotenv

# Определяем корень проекта и загружаем .env
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Читаем список ID администраторов из .env (через запятую, например: 123456789,987654321)
raw_admin_ids = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(i.strip()) for i in raw_admin_ids.split(",") if i.strip().isdigit()]

if not BOT_TOKEN:
    raise ValueError("ОШИБКА: BOT_TOKEN не найден в файле .env!")

# URL-адреса портала Торайгыров Университета
LOGIN_URL = "https://tou.edu.kz/student_cabinet/index.php?lang=rus"
SCHEDULE_URL = "https://tou.edu.kz/student_cabinet/index.php?lang=rus&mod=rasp"
DASHBOARD_URL = "https://tou.edu.kz/student_cabinet/index.php?lang=rus&mod=dashboard"


def get_headers(mode: str = "random") -> dict:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }


# Расписание пар Торайгыровского Университета
# Структура: (номер пары, время начала HH:MM, время окончания HH:MM, длительность перерыва в минутах)
LESSONS_SCHEDULE = [
    {"number": 1, "start": "08:15", "end": "09:05", "break_duration": 10},
    {"number": 2, "start": "09:15", "end": "10:05", "break_duration": 10},
    {"number": 3, "start": "10:15", "end": "11:05", "break_duration": 10},
    {"number": 4, "start": "11:15", "end": "12:05", "break_duration": 30},
    {"number": 5, "start": "12:35", "end": "13:25", "break_duration": 10},
    {"number": 6, "start": "13:35", "end": "14:25", "break_duration": 10},
    {"number": 7, "start": "14:35", "end": "15:25", "break_duration": 5},
    {"number": 8, "start": "15:30", "end": "16:20", "break_duration": 5},
    {"number": 9, "start": "16:25", "end": "17:15", "break_duration": 5},
    {"number": 10, "start": "17:20", "end": "18:10", "break_duration": 5},
    {"number": 11, "start": "18:15", "end": "19:05", "break_duration": 5},
    {"number": 12, "start": "19:10", "end": "20:00", "break_duration": 0},
]
