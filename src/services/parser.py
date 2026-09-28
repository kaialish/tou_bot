from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re

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

    return [item for item in all_items if item["day"] == target_day_name]
