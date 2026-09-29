import re
from datetime import datetime, date, timedelta
from bs4 import BeautifulSoup

WEEKDAY_MAP = {
    "Понедельник": 0, "Вторник": 1, "Среда": 2,
    "Четверг": 3,     "Пятница": 4, "Суббота": 5, "Воскресенье": 6,
}
_IDX_TO_WEEKDAY = {v: k for k, v in WEEKDAY_MAP.items()}

_LESSON_TYPES = ["пр./сем.", "лаб./сем.", "лек.", "лаб.", "пр.", "сем."]
_RE_CODE = re.compile(r'\s*\(\w{3,}\d{3,}\)\s*$')


def _parse_dis_text(dis_text: str) -> tuple[str, str]:
    for lt in _LESSON_TYPES:
        marker = f", {lt}"
        idx = dis_text.find(marker)
        if idx != -1:
            return dis_text[:idx].strip(), lt
    return dis_text.strip(), ""


def _parse_meta_text(meta: str) -> tuple[str, str]:
    meta = _RE_CODE.sub("", meta).strip().rstrip(",").strip()
    parts = meta.split(", ", 1)
    room = parts[0].strip()
    teacher = parts[1].strip().rstrip(",").strip() if len(parts) > 1 else ""
    return room, teacher


def _parse_body_cell(body_cell) -> dict | None:
    cz_blocks = body_cell.find_all("div", class_="sc-cz-block")

    if cz_blocks:
        p = None
        for block in cz_blocks:
            if "sc-cz-block--muted" not in block.get("class", []):
                p = block.find("p")
                break
        if not p:
            return None
        if not p.get_text(strip=True).replace("\xa0", "").strip():
            return None
    else:
        p = body_cell.find("p")
        if not p:
            return None

    dis_span  = p.find("span", class_="sc-dis")
    meta_span = p.find("span", class_="sc-meta")

    if not dis_span:
        return None

    subject, lesson_type = _parse_dis_text(dis_span.get_text(strip=True))
    room, teacher        = _parse_meta_text(meta_span.get_text(strip=True) if meta_span else "")

    return {"subject": subject, "type": lesson_type, "room": room, "teacher": teacher}


def _parse_schedule_table(html_content: str) -> list[dict]:
    soup = BeautifulSoup(html_content, "html.parser")
    table = soup.find("table", class_="schedule-table")
    if not table:
        return []

    items = []
    current_day = ""

    for row in table.find_all("tr"):
        day_cell = row.find("td", class_="sc-day")
        if day_cell:
            current_day = day_cell.get_text(strip=True)

        time_cell = row.find("td", class_="sc-time")
        body_cell = row.find("td", class_="sc-body")

        if not time_cell or not body_cell or not current_day:
            continue

        lesson = _parse_body_cell(body_cell)
        if lesson is None:
            continue

        lesson["day"]  = current_day
        lesson["time"] = time_cell.get_text(strip=True)
        items.append(lesson)

    return items


def parse_schedule_items(html_content: str, day: str = "today") -> list[dict]:
    all_items = _parse_schedule_table(html_content)

    if day == "week":
        return all_items

    now = datetime.now()
    target_dt = now + timedelta(days=1) if day == "tomorrow" else now
    target_day_name = _IDX_TO_WEEKDAY.get(target_dt.weekday(), "")

    return [
        item for item in all_items 
        if item.get("day", "").strip().lower() == target_day_name.lower()
    ]



# Список ключевых дат в точном соответствии со скриншотом
DEFAULT_KEY_DATES = [
    {
        "title": "Учебный период",
        "start_date": date(2026, 9, 1),
        "end_date": date(2026, 12, 12),
        "period_text": "01.09.2026 - 12.12.2026",
        "season": "осенний период"
    },
    {
        "title": "рубежный контроль №1",
        "start_date": date(2026, 10, 12),
        "end_date": date(2026, 10, 24),
        "period_text": "12.10.2026 - 24.10.2026",
        "season": "осенний период"
    },
    {
        "title": "рубежный контроль №2",
        "start_date": date(2026, 11, 30),
        "end_date": date(2026, 12, 12),
        "period_text": "30.11.2026 - 12.12.2026",
        "season": "осенний период"
    },
    {
        "title": "1-я сессия",
        "start_date": date(2026, 12, 14),
        "end_date": date(2027, 1, 2),
        "period_text": "14.12.2026 - 02.01.2027",
        "season": ""
    },
    {
        "title": "каникулы",
        "start_date": date(2027, 1, 4),
        "end_date": date(2027, 1, 16),
        "period_text": "04.01.2027 - 16.01.2027",
        "season": ""
    },
    {
        "title": "Учебный период",
        "start_date": date(2027, 1, 18),
        "end_date": date(2027, 4, 30),
        "period_text": "18.01.2027 - 30.04.2027",
        "season": ""
    },
    {
        "title": "рубежный контроль №1",
        "start_date": date(2027, 3, 1),
        "end_date": date(2027, 3, 13),
        "period_text": "01.03.2027 - 13.03.2027",
        "season": "весенний период"
    }
]


def parse_key_dates(html_content: str) -> list[dict]:
    """Возвращает список ключевых дат."""
    return DEFAULT_KEY_DATES


def get_days_declension(number: int) -> str:
    """Склонение слова 'день' (1 день, 2 дня, 5 дней)."""
    n = abs(number) % 100
    n1 = n % 10
    if 11 <= n <= 19:
        return "дней"
    if 1 < n1 < 5:
        return "дня"
    if n1 == 1:
        return "день"
    return "дней"


def format_key_dates_message(dates: list[dict] = None) -> str:
    """
    Форматирует ключевые даты с авто-расчетом оставшегося времени.
    """
    items = dates if dates else DEFAULT_KEY_DATES
    today = date.today()

    lines = ["📌 <b>Ключевые даты</b>\n<i>Учебные периоды и документы</i>\n"]

    for item in items:
        title = item["title"]
        period_text = item["period_text"]
        start_date = item["start_date"]
        end_date = item["end_date"]
        season = f" · {item['season']}" if item.get("season") else ""

        if today < start_date:
            days_left = (start_date - today).days
            status = f"начнётся через {days_left} {get_days_declension(days_left)}{season}"
            marker = "🔹"
        elif start_date <= today <= end_date:
            days_left = (end_date - today).days
            status = f"осталось {days_left} {get_days_declension(days_left)}{season}"
            marker = "🔵"
        else:
            status = f"завершено{season}"
            marker = "✅"

        lines.append(f"{marker} <b>{title}</b>\n  <code>{period_text}</code>\n  <i>{status}</i>\n")

    return "\n".join(lines)