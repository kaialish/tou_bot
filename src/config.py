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
