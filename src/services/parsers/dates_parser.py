from datetime import date
from src.config import get_kz_now

DEFAULT_KEY_DATES = [
    {
        "title": "Учебный период",
        "start_date": date(2026, 9, 1),
        "end_date": date(2026, 12, 12),
        "period_text": "01.09.2026 - 12.12.2026",
        "season": "осенний период"
    },
    {
        "title": "РК №1",
        "start_date": date(2026, 10, 12),
        "end_date": date(2026, 10, 24),
        "period_text": "12.10.2026 - 24.10.2026",
        "season": "осенний период"
    },
    {
        "title": "РК №2",
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
        "title": "РК №1",
        "start_date": date(2027, 3, 1),
        "end_date": date(2027, 3, 13),
        "period_text": "01.03.2027 - 13.03.2027",
        "season": "весенний период"
    }
]


def get_calculated_key_dates(target_date: date | None = None) -> list[dict]:
    """Возвращает ключевые даты с авто-расчетом оставшегося времени."""
    today = target_date or get_kz_now().date()
    current_year = today.year
    base_year = current_year if today.month >= 8 else current_year - 1

    dates_config = [
        {"title": "Учебный период (осенний)", "start": date(base_year, 9, 1), "end": date(base_year, 12, 12)},
        {"title": "РК №1", "start": date(base_year, 10, 12), "end": date(base_year, 10, 24)},
        {"title": "РК №2", "start": date(base_year, 11, 30), "end": date(base_year, 12, 12)},
        {"title": "1-я зимняя сессия", "start": date(base_year, 12, 14), "end": date(base_year + 1, 1, 2)},
        {"title": "Зимние каникулы", "start": date(base_year + 1, 1, 4), "end": date(base_year + 1, 1, 16)},
    ]

    items = []
    for item in dates_config:
        title = item["title"]
        start_date = item["start"]
        end_date = item["end"]
        period_text = f"{start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"

        if today < start_date:
            days_left = (start_date - today).days
            status = f"начнётся через {days_left} {get_days_declension(days_left)}"
            marker = "🔹"
        elif start_date <= today <= end_date:
            days_left = (end_date - today).days
            status = f"осталось {days_left} {get_days_declension(days_left)}"
            marker = "🔵"
        else:
            status = "завершено"
            marker = "✅"

        items.append({
            "title": title,
            "period": period_text,
            "period_text": period_text,
            "status": status,
            "marker": marker,
            "days_left": days_left if (today <= end_date) else 0,
        })
    return items


def parse_key_dates(html_content: str) -> list[dict]:
    """Возвращает список ключевых дат."""
    return get_calculated_key_dates()


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
