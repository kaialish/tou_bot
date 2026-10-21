import re
from datetime import datetime, date, timedelta
from bs4 import BeautifulSoup
from src.config import get_kz_now

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


def parse_schedule_items(html_content: str, day: str = "today", target_date: date | datetime | None = None) -> list[dict]:
    all_items = _parse_schedule_table(html_content)

    if day == "week":
        return all_items

    if target_date is not None:
        target_dt = target_date
    else:
        now = get_kz_now()
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


_NUM_EMOJIS = {
    1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣",
    6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"
}


def format_schedule_text(items: list[dict], title: str, day_mode: str = "today") -> str:
    """
    Форматирует расписание в красивый, компактный и читаемый текст для Telegram.
    Работает мгновенно без нагрузки на процессор и рендеринга картинок.
    """
    if not items:
        return f"📅 <b>{title}</b>\n\n🎉 <i>Занятий нет! Можно отдыхать.</i>"

    if day_mode == "week":
        days_order = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
        grouped: dict[str, list[dict]] = {d: [] for d in days_order}
        for it in items:
            day_name = it.get("day", "").strip()
            if day_name in grouped:
                grouped[day_name].append(it)
            else:
                grouped.setdefault(day_name, []).append(it)

        lines = [f"📅 <b>{title}</b>\n"]
        has_any = False
        for day_name, day_items in grouped.items():
            if not day_items:
                continue
            has_any = True
            lines.append(f"🗓️ <b>{day_name}</b>")
            for idx, item in enumerate(day_items, 1):
                num_icon = _NUM_EMOJIS.get(idx, f"[{idx}]")
                t_type = f" | <i>{item['type']}</i>" if item.get('type') else ""
                time_str = item.get('time', '')
                subj = item.get('subject', 'Без названия')
                room = item.get('room', '')
                teacher = item.get('teacher', '')

                details = []
                if room:
                    details.append(f"📍 Ауд. {room}")
                if teacher:
                    details.append(f"👤 {teacher}")
                meta_str = f"   {' • '.join(details)}" if details else ""
                meta_line = f"\n{meta_str}" if meta_str else ""

                lines.append(f"{num_icon} <b>{time_str}</b>{t_type}\n   📚 <b>{subj}</b>{meta_line}")
            lines.append("")

        if not has_any:
            return f"📅 <b>{title}</b>\n\n🎉 <i>На этой неделе занятий нет!</i>"

        return "\n".join(lines).strip()

    # Для одного дня (Сегодня / Завтра)
    day_name = items[0].get("day") if items else ""
    header = f"📅 <b>{title}</b>"
    if day_name and day_name.lower() not in title.lower():
        header += f" (<b>{day_name}</b>)"

    lines = [header, ""]
    for idx, item in enumerate(items, 1):
        num_icon = _NUM_EMOJIS.get(idx, f"[{idx}]")
        t_type = f" | <i>{item['type']}</i>" if item.get('type') else ""
        time_str = item.get('time', '')
        subj = item.get('subject', 'Без названия')
        room = item.get('room', '')
        teacher = item.get('teacher', '')

        details = []
        if room:
            details.append(f"📍 Ауд. {room}")
        if teacher:
            details.append(f"👤 {teacher}")
        meta_str = f"   {' • '.join(details)}" if details else ""
        meta_line = f"\n{meta_str}" if meta_str else ""

        lines.append(f"{num_icon} <b>{time_str}</b>{t_type}\n   📚 <b>{subj}</b>{meta_line}\n")

    return "\n".join(lines).strip()


# ─────────────────────────────────────────────────────────────────────────────
# Академический статус
# ─────────────────────────────────────────────────────────────────────────────

def _evaluate_academic_indicator(name: str, value: str) -> str:
    """Определяет индикатор статуса: positive (🟢), negative (🔴), neutral (⚪)."""
    val_clean = value.lower().strip()
    name_clean = name.lower().strip()

    if not val_clean or val_clean in ["нет данных", "--", "неизвестно", "не указан", "отсутствует"]:
        return "neutral"

    if "успеваемость" in name_clean:
        if any(w in val_clean for w in ["ниже 50", "< 50", "задолж", "не аттест", "не допуск"]):
            return "negative"
        if any(w in val_clean for w in ["в норме", "выше 50", "аттестован", "сдано"]):
            return "positive"

    if "задолженност" in name_clean:
        if val_clean in ["нет", "отсутствуют", "0", "нет задолженностей"]:
            return "positive"
        return "negative"

    if "допуск" in name_clean:
        if any(w in val_clean for w in ["не допущен", "нет допуска", "не сдан"]):
            return "negative"
        if any(w in val_clean for w in ["допущен", "есть допуск", "в норме"]):
            return "positive"

    if "флюорограф" in name_clean:
        if "действительна" in val_clean:
            return "positive"
        if any(w in val_clean for w in ["просроч", "недействительна", "требуется", "сдать", "нет"]):
            return "negative"

    if "email" in name_clean or "почта" in name_clean:
        if "@" in val_clean:
            return "positive"
        return "neutral"

    # Общие правила
    if any(w in val_clean for w in ["ниже", "просроч", "долг", "не сдан", "ошибка", "вниман"]):
        return "negative"
    if any(w in val_clean for w in ["действительн", "в норме", "допущен", "нет"]):
        return "positive"

    return "neutral"


def parse_academic_status(html: str) -> dict:
    """
    Парсит карточку 'Академический статус' из дашборда ToU.
    Возвращает словарь с бейджем, подзаголовком и списком параметров.
    """
    soup = BeautifulSoup(html, "html.parser")

    target_fields = [
        ("Допуск к экзаменам", ["допуск к экзаменам", "допуск к экзаменам:"]),
        ("Текущая успеваемость", ["текущая успеваемость", "текущая успеваемость:"]),
        ("Академические задолженности", ["академические задолженности", "задолженности:"]),
        ("Флюорография", ["флюорография", "флюорография:"]),
    ]

    status_badge = ""
    subtitle = ""
    items = []

    # 1. Точный поиск карточки по официальным классам ToU (student-card)
    target_card = None
    for card in soup.select("section.student-card, div.student-card"):
        h2 = card.find("h2")
        if h2 and "академический статус" in h2.get_text().lower():
            target_card = card
            break
        if "академический статус" in card.get_text().lower():
            target_card = card
            break

    # Если карточка с классом student-card найдена, парсим по точной верстке
    if target_card:
        # Бейдж статуса
        chip = target_card.select_one(".student-chip")
        if chip:
            status_badge = chip.get_text(strip=True)

        # Элементы проверок (.student-check)
        checks = target_card.select(".student-check")
        if checks:
            for check in checks:
                lbl_el = check.select_one(".student-check__label")
                val_el = check.select_one(".student-check__value")
                dot_el = check.select_one(".student-check__dot")

                if not lbl_el:
                    continue

                name = lbl_el.get_text(strip=True)
                # Пропускаем email по запросу
                if name.lower() in ["email", "e-mail", "эл. почта", "почта"]:
                    continue

                val = val_el.get_text(strip=True) if val_el else "Нет данных"

                # Удаляем шевроны если попали
                val = re.sub(r'chevron_right|keyboard_arrow_right|[>›»&gt;]', '', val).strip()

                # Определяем индикатор по классам ToU (--bad, --good, --muted)
                dot_classes = " ".join(dot_el.get("class", [])) if dot_el else ""
                val_classes = " ".join(val_el.get("class", [])) if val_el else ""
                combined_classes = f"{dot_classes} {val_classes}".lower()

                if "--bad" in combined_classes or "--danger" in combined_classes:
                    indicator = "negative"
                elif "--good" in combined_classes or "--success" in combined_classes:
                    indicator = "positive"
                elif "--muted" in combined_classes:
                    indicator = "neutral"
                else:
                    indicator = _evaluate_academic_indicator(name, val)

                items.append({
                    "name": name,
                    "value": val if val else "Нет данных",
                    "indicator": indicator,
                })

    # 2. Универсальный фолбэк, если верстка изменилась или student-card не найден
    if not items:
        # Поиск контейнера
        title_el = None
        for el in soup.find_all(string=re.compile(r"академический\s+статус", re.IGNORECASE)):
            title_el = el.parent
            break

        widget_container = None
        if title_el:
            curr = title_el
            while curr and getattr(curr, "name", None) not in ["body", "html", "[document]", None]:
                curr_text = curr.get_text().lower()
                if any(k in curr_text for k in ["успеваемость", "допуск", "задолженност", "флюорограф"]):
                    widget_container = curr
                    break
                curr = curr.parent

        search_root = widget_container if widget_container else soup

        if not status_badge and widget_container:
            for elem in widget_container.find_all(["span", "div", "p", "a"]):
                text = elem.get_text(strip=True)
                if not text:
                    continue
                text_lower = text.lower()
                if "академический статус" in text_lower or subtitle.lower() in text_lower:
                    continue
                if any(w in text_lower for w in ["требует внимания", "в норме", "внимание", "отлично", "всё в порядке"]):
                    status_badge = text
                    break
                cls_str = " ".join(elem.get("class", []))
                if any(c in cls_str for c in ["badge", "chip", "status", "tag", "pill"]):
                    if len(text) < 40 and text not in [f[0] for f in target_fields]:
                        status_badge = text
                        break

        for display_name, aliases in target_fields:
            found_val = ""
            for alias in aliases:
                for el in search_root.find_all(string=re.compile(re.escape(alias), re.IGNORECASE)):
                    parent = el.parent
                    row = (
                        parent.find_parent(["li", "tr"])
                        or parent.find_parent(class_=re.compile(r"item|row|list|collection", re.I))
                        or parent.find_parent("div")
                        or parent
                    )
                    row_text = row.get_text(" ", strip=True)

                    remaining = re.sub(re.escape(alias), "", row_text, flags=re.IGNORECASE).strip()
                    remaining = re.sub(r'chevron_right|keyboard_arrow_right|[>›»&gt;]', '', remaining).strip()
                    remaining = re.sub(r'^[:\-–\s]+', '', remaining).strip()

                    if remaining:
                        found_val = remaining
                        break
                if found_val:
                    break

            if not found_val:
                for alias in aliases:
                    match = re.search(rf'{re.escape(alias)}\s*[:\-–]?\s*([^\n<]+)', html, re.IGNORECASE)
                    if match:
                        candidate = match.group(1).strip()
                        candidate = re.sub(r'chevron_right|keyboard_arrow_right|[>›»&gt;]', '', candidate).strip()
                        if candidate and len(candidate) < 100:
                            found_val = candidate
                            break

            val = found_val if found_val else "Нет данных"
            indicator = _evaluate_academic_indicator(display_name, val)
            items.append({
                "name": display_name,
                "value": val,
                "indicator": indicator,
            })

    # Если бейдж не удалось найти в разметке, вычисляем его
    if not status_badge:
        has_negative = any(item["indicator"] == "negative" for item in items)
        status_badge = "Требует внимания" if has_negative else "В норме"

    return {
        "status_badge": status_badge,
        "subtitle": subtitle,
        "items": items,
    }


def format_academic_status_message(status_data: dict, updated_at: str = "") -> str:
    """Форматирует данные академического статуса в красивый Telegram HTML-текст."""
    badge = status_data.get("status_badge", "").strip()
    badge_lower = badge.lower() if badge else ""

    if any(w in badge_lower for w in ["вниман", "долг", "риск", "просроч", "ниже", "плохо"]):
        badge_header = f"🔴 <code>{badge}</code>"
    elif any(w in badge_lower for w in ["норм", "порядок", "отличн", "хорошо"]):
        badge_header = f"🟢 <code>{badge}</code>"
    elif badge:
        badge_header = f"ℹ️ <code>{badge}</code>"
    else:
        badge_header = ""

    header_line = "📌 <b>Академический статус</b>"
    if badge_header:
        header_line += f" • {badge_header}"

    lines = [
        header_line,
        "─────────────────────────",
    ]

    items = status_data.get("items", [])
    if not items:
        lines.append("<i>Данные статуса пока не загружены.</i>")
    else:
        for item in items:
            name = item.get("name", "")
            val = item.get("value", "Нет данных")
            ind = item.get("indicator", "neutral")

            if ind == "positive":
                dot = "🟢"
            elif ind == "negative":
                dot = "🔴"
            else:
                dot = "⚪"

            if "@" in val:
                val_text = f"<code>{val}</code>"
            elif ind == "negative":
                val_text = f"<b>{val}</b>"
            else:
                val_text = val

            lines.append(f"{dot} <b>{name}:</b> {val_text}")

    lines.append("─────────────────────────")
    if updated_at:
        lines.append(f"🕒 <i>Данные обновлены: {updated_at}</i>")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Журнал успеваемости (mod=zhurnal)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_zhurnal_table(table) -> dict | None:
    """Разбирает таблицу оценок для одного предмета."""
    rows = table.find_all("tr")
    if len(rows) < 4:
        return None

    row1_cells = rows[1].find_all(["td", "th"])
    row2_cells = rows[2].find_all(["td", "th"])
    row3_cells = rows[3].find_all(["td", "th"])

    summary = {
        "tu1": "",
        "rk1": "",
        "r1": "",
        "tu2": "",
        "rk2": "",
        "r2": "",
        "rd": row3_cells[-5].get_text(strip=True) if len(row3_cells) >= 5 else "",
        "exam": row3_cells[-4].get_text(strip=True) if len(row3_cells) >= 4 else "",
        "final": row3_cells[-1].get_text(strip=True) if len(row3_cells) >= 1 else "",
    }

    sections_by_type = {}
    row2_idx = 0
    row3_idx = 1
    current_rating = 1

    for r1_cell in row1_cells:
        name = r1_cell.get_text(strip=True)
        colspan = int(r1_cell.get("colspan", 1))

        if "Р1" in name or name == "Р1":
            if row3_idx < len(row3_cells):
                summary["r1"] = row3_cells[row3_idx].get_text(strip=True)
                row3_idx += 1
            current_rating = 2
            continue

        if "Р2" in name or name == "Р2":
            if row3_idx < len(row3_cells):
                summary["r2"] = row3_cells[row3_idx].get_text(strip=True)
                row3_idx += 1
            continue

        if "Текущие" in name:
            if row3_idx + 1 < len(row3_cells):
                tu_val = row3_cells[row3_idx].get_text(strip=True)
                rk_val = row3_cells[row3_idx + 1].get_text(strip=True)
                if current_rating == 1:
                    summary["tu1"] = tu_val
                    summary["rk1"] = rk_val
                else:
                    summary["tu2"] = tu_val
                    summary["rk2"] = rk_val
            row2_idx += colspan
            row3_idx += colspan
            continue

        if "ведомост" in name.lower():
            row2_idx += colspan
            row3_idx += colspan
            continue

        activity_type = name
        if activity_type not in sections_by_type:
            sections_by_type[activity_type] = {
                "type": activity_type,
                "r1_grades": [],
                "r1_avg": "",
                "r2_grades": [],
                "r2_avg": "",
            }

        for _ in range(colspan):
            if row2_idx < len(row2_cells) and row3_idx < len(row3_cells):
                col_header = row2_cells[row2_idx].get_text(strip=True)
                val = row3_cells[row3_idx].get_text(strip=True)

                if "сред" in col_header.lower():
                    if current_rating == 1:
                        sections_by_type[activity_type]["r1_avg"] = val
                    else:
                        sections_by_type[activity_type]["r2_avg"] = val
                else:
                    grade_item = {"week": col_header, "grade": val}
                    if current_rating == 1:
                        sections_by_type[activity_type]["r1_grades"].append(grade_item)
                    else:
                        sections_by_type[activity_type]["r2_grades"].append(grade_item)

            row2_idx += 1
            row3_idx += 1

    return {
        "activities": list(sections_by_type.values()),
        "summary": summary,
    }


def extract_current_week(html: str) -> int:
    """
    Находит номер текущей недели в HTML-коде (блок Неделя: <b>X</b>).
    Если не найден, возвращает 15 по умолчанию.
    """
    match = re.search(r'Неделя:\s*<b>(\d+)</b>', html, re.IGNORECASE)
    if match:
        return int(match.group(1))

    match = re.search(r'неделя\s*:\s*<b>(\d+)</b>', html, re.IGNORECASE)
    if match:
        return int(match.group(1))

    match = re.search(r'неделя\s*:\s*(\d+)', html, re.IGNORECASE)
    if match:
        return int(match.group(1))

    return 15


def parse_zhurnal(html: str) -> dict:
    """
    Парсит страницу журнала успеваемости ToU (mod=zhurnal).
    Возвращает словарь:
      - current_week: номер текущей недели X (якорь)
      - courses: список дисциплин с преподавателями, оценками и итоговыми баллами.
    """
    current_week = extract_current_week(html)
    soup = BeautifulSoup(html, "html.parser")
    courses = []

    sections = soup.select("section.student-zhurnal__course")
    for sec in sections:
        head = sec.select_one(".student-zhurnal__course-head")
        if not head:
            continue
        h2 = head.find("h2")
        title = h2.get_text(strip=True) if h2 else "Без названия"

        teachers = []
        for t_span in head.select(".student-zhurnal__teacher"):
            t_types_el = t_span.select_one(".student-zhurnal__teacher-types")
            t_fio_el = t_span.select_one(".student-zhurnal__teacher-fio")
            t_types = t_types_el.get_text(strip=True) if t_types_el else ""
            t_fio = t_fio_el.get_text(strip=True) if t_fio_el else ""
            teachers.append({"type": t_types, "fio": t_fio})

        empty_el = sec.select_one(".student-empty")
        if empty_el:
            courses.append({
                "title": title,
                "teachers": teachers,
                "has_data": False,
                "note": empty_el.get_text(strip=True),
            })
            continue

        table = sec.find("table")
        if not table:
            courses.append({
                "title": title,
                "teachers": teachers,
                "has_data": False,
                "note": "Таблица оценок не найдена",
            })
            continue

        parsed_data = _parse_zhurnal_table(table)
        courses.append({
            "title": title,
            "teachers": teachers,
            "has_data": True if parsed_data else False,
            "data": parsed_data,
        })

    return {
        "current_week": current_week,
        "courses": courses,
    }


def _shorten_fio(fio: str) -> str:
    """
    Сокращает ФИО строго до инициалов:
    'Потапенко Александра Олеговна' -> 'Потапенко А. О.'
    'Сүйіндік Нұртас Мерхатұлы' -> 'Сүйіндік Н. М.'
    """
    parts = fio.strip().split()
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    last_name = parts[0]
    initials = [f"{p[0].upper()}." for p in parts[1:] if p]
    return f"{last_name} {' '.join(initials)}"


def _get_traffic_light(score: float | None, current_week: int = 1, has_any_grade: bool = True) -> str:
    """
    Светофор успеваемости по пересчитанному реальному баллу:
    🟢 — 70-100 баллов
    🟠 — 50-69 баллов
    🔴 — 0-49 баллов (Завалы с учетом долгов по текущую неделю)
    ⚪ — Если неделя 1-я и оценок физически еще нет ни у кого.
    """
    if score is None or not has_any_grade:
        return "⚪" if current_week <= 1 else "🔴"
    try:
        if score >= 70.0:
            return "🟢"
        elif score >= 50.0:
            return "🟠"
        else:
            return "🔴"
    except Exception:
        return "⚪"


def _format_score(val: str | float | int | None, default: str = "0") -> str:
    """Округление: Дробные баллы округляет до одного знака после запятой."""
    if val is None or str(val).strip() == "":
        return default
    val_clean = str(val).replace(",", ".").strip()
    match = re.search(r'[-+]?\d*\.?\d+', val_clean)
    if not match:
        return str(val).strip()
    try:
        num = float(match.group())
        if num.is_integer():
            return str(int(num))
        formatted = f"{num:.1f}".rstrip("0").rstrip(".")
        return formatted
    except Exception:
        return str(val).strip()


def _filter_grades_by_current_week(grades: list[dict], current_week: int) -> tuple[list[dict], float | None, bool]:
    """
    1. Обрезает данные строго после недели X.
    2. Все недели от 1 до X обязательно остаются в выводе. Если балл пуст или 0, он остается 0.
    3. Считает средний балл: (Сумма всех оценок с 1 по X неделю) / X.
    4. Возвращает (filtered_grades, average_score, has_any_non_zero_grade).
    """
    cutoff = max(1, current_week)
    result = []
    total = 0.0
    has_any_grade = False

    for w in range(1, cutoff + 1):
        # Ищем оценку за неделю w в массиве
        found_val = "0"
        for g in grades:
            week_str = str(g.get("week", "")).strip()
            if week_str == str(w):
                raw = str(g.get("grade", "")).strip()
                if raw != "":
                    found_val = raw
                break

        val_clean = found_val.replace(",", ".").strip()
        match = re.search(r'[-+]?\d*\.?\d+', val_clean)
        num = float(match.group()) if match else 0.0

        if num > 0:
            has_any_grade = True

        total += num
        result.append({"week": str(w), "grade": found_val})

    avg = total / cutoff
    return result, avg, has_any_grade


def _calc_course_real_tu(activities: list[dict], current_week: int, fallback_tu1: str = "") -> tuple[float | None, bool]:
    """
    Считает реальный средний балл текущей успеваемости дисциплины
    по формуле: среднее арифметическое средних баллов активностей с 1 по X неделю.
    Возвращает (avg_score, has_any_grade).
    """
    act_avgs = []
    has_any = False
    for act in activities:
        r1_grades = act.get("r1_grades", [])
        _, avg, has_grade = _filter_grades_by_current_week(r1_grades, current_week)
        if avg is not None:
            act_avgs.append(avg)
        if has_grade:
            has_any = True

    if act_avgs:
        return sum(act_avgs) / len(act_avgs), has_any

    # Если активности пустые
    if fallback_tu1:
        val_clean = fallback_tu1.replace(",", ".").strip()
        match = re.search(r'[-+]?\d*\.?\d+', val_clean)
        if match:
            val = float(match.group())
            return val, val > 0

    return None, False


def _extract_courses_and_week(zhurnal_data: list[dict] | dict) -> tuple[list[dict], int]:
    """Вспомогательная функция для поддержки и старого списка, и нового словаря."""
    if isinstance(zhurnal_data, dict):
        return zhurnal_data.get("courses", []), zhurnal_data.get("current_week", 15)
    return zhurnal_data, 15


def format_zhurnal_brief(zhurnal_data: list[dict] | dict, updated_at: str = "") -> str:
    """
    Форматирует краткий вид успеваемости по строгому шаблону:
    📚 [Название предмета]
       💡 ТУ1: [Реальный балл] • РК1: [Балл] • Р1: [Балл] [Эмодзи]
    (Если нет силлабуса: ⚠️ Силлабус не сформирован.)
    """
    courses, current_week = _extract_courses_and_week(zhurnal_data)

    if not courses:
        return "📊 <b>Успеваемость</b>\n\n<i>Данные об успеваемости не найдены.</i>"

    lines = [
        f"📊 <b>Успеваемость · Краткий вид</b> (Неделя: {current_week})",
        "─────────────────────────",
    ]

    for c in courses:
        title = c.get("title", "Без названия")
        has_data = c.get("has_data", False)
        note = c.get("note", "")

        lines.append(f"📚 <b>{title}</b>")

        if not has_data:
            if "силлабус" in note.lower():
                lines.append("   ⚠️ Силлабус не сформирован.\n")
            else:
                lines.append(f"   ⚠️ {note if note else 'Данные недоступны'}\n")
            continue

        data = c.get("data") or {}
        activities = data.get("activities", [])
        summary = data.get("summary") or {}

        # Пересчитанный честный балл ТУ1 за недели 1..X
        real_tu, has_any_grade = _calc_course_real_tu(activities, current_week, fallback_tu1=summary.get("tu1", ""))
        display_tu = _format_score(real_tu) if real_tu is not None else _format_score(summary.get("tu1", ""))
        rk1 = _format_score(summary.get("rk1", ""))
        r1 = _format_score(summary.get("r1", ""))

        # Светофор на основе реального балла
        traffic = _get_traffic_light(real_tu, current_week=current_week, has_any_grade=has_any_grade)

        lines.append(f"   💡 ТУ1: <b>{display_tu}</b> • РК1: <b>{rk1}</b> • Р1: <b>{r1}</b> {traffic}\n")

    lines.append("─────────────────────────")
    if updated_at:
        lines.append(f"🕒 <i>Данные обновлены: {updated_at}</i>")

    return "\n".join(lines).strip()


def format_zhurnal_full_chunks(zhurnal_data: list[dict] | dict, updated_at: str = "") -> list[str]:
    """
    Форматирует полный вид детализации предметов по строгому шаблону:
    📘 Дисциплина: [Название]
    👤 Лектор: [Фамилия И. О.]
    👤 Практик: [Фамилия И. О.]
    ─────────────────────────
    🎯 Итог: ТУ1: [Балл] • РК1: [Балл] • Р1: [Балл] [Эмодзи]

    🔹 Лекции [твой ср. балл: X]
    [Только реальные недели, пример: 1н: 90 | 2н: 80]

    🔹 Практика [твой ср. балл: X]
    [Только реальные недели, пример: 1н: 75 | 2н: 80 | 3н: 80]
    """
    courses, current_week = _extract_courses_and_week(zhurnal_data)

    if not courses:
        return ["📊 <b>Полный журнал успеваемости</b>\n\n<i>Данные об успеваемости не найдены.</i>"]

    messages = []
    current_lines = [
        f"📊 <b>Полный журнал успеваемости</b> (Неделя: {current_week})",
        "",
    ]

    for c in courses:
        c_lines = []
        title = c.get("title", "Без названия")
        teachers = c.get("teachers", [])
        has_data = c.get("has_data", False)
        note = c.get("note", "")

        c_lines.append(f"📘 <b>Дисциплина:</b> {title}")

        # Разделение преподавателей на Лектор / Практик
        lectors = []
        practitioners = []
        others = []

        for t in teachers:
            fio_short = _shorten_fio(t.get("fio", ""))
            t_type = t.get("type", "").lower()
            if not fio_short:
                continue
            if "лекц" in t_type:
                lectors.append(fio_short)
            elif any(w in t_type for w in ["практ", "семин", "лаб"]):
                practitioners.append(fio_short)
            else:
                others.append(fio_short)

        if lectors:
            c_lines.append(f"👤 <b>Лектор:</b> {', '.join(lectors)}")
        if practitioners:
            c_lines.append(f"👤 <b>Практик:</b> {', '.join(practitioners)}")
        for o in others:
            c_lines.append(f"👤 <b>Преподаватель:</b> {o}")

        if not has_data:
            c_lines.append("─────────────────────────")
            if "силлабус" in note.lower():
                c_lines.append("⚠️ Силлабус не сформирован.\n")
            else:
                c_lines.append(f"⚠️ {note if note else 'Данные недоступны'}\n")
        else:
            data = c.get("data") or {}
            activities = data.get("activities", [])
            summary = data.get("summary", {})

            # Реальный балл и светофор
            real_tu, has_any_grade = _calc_course_real_tu(activities, current_week, fallback_tu1=summary.get("tu1", ""))
            display_tu = _format_score(real_tu) if real_tu is not None else _format_score(summary.get("tu1", ""))
            rk1 = _format_score(summary.get("rk1", ""))
            r1 = _format_score(summary.get("r1", ""))
            traffic = _get_traffic_light(real_tu, current_week=current_week, has_any_grade=has_any_grade)

            c_lines.append("─────────────────────────")
            c_lines.append(f"🎯 <b>Итог:</b> ТУ1: <b>{display_tu}</b> • РК1: <b>{rk1}</b> • Р1: <b>{r1}</b> {traffic}\n")

            for act in activities:
                raw_type = act.get("type", "Занятие").strip()
                if "лекц" in raw_type.lower():
                    act_title = "Лекции"
                elif any(w in raw_type.lower() for w in ["практ", "семин"]):
                    act_title = "Практика"
                elif "лаб" in raw_type.lower():
                    act_title = "Лабораторные"
                else:
                    act_title = raw_type

                r1_grades = act.get("r1_grades", [])
                filtered, real_avg, _ = _filter_grades_by_current_week(r1_grades, current_week)

                if real_avg is not None:
                    avg_text = _format_score(real_avg)
                    c_lines.append(f"🔹 <b>{act_title}</b> [твой ср. балл: {avg_text}]")
                    row_str = " | ".join([f"{g['week']}н: {_format_score(g['grade'])}" for g in filtered])
                    c_lines.append(row_str)
                else:
                    c_lines.append(f"🔹 <b>{act_title}</b>")
                    c_lines.append("<i>Баллы еще не выставлены</i>")
                c_lines.append("")

        c_lines.append("═════════════════════════\n")

        added_text = "\n".join(c_lines)
        current_text = "\n".join(current_lines)
        if len(current_text) + len(added_text) > 3500:
            messages.append(current_text.strip())
            current_lines = [
                "📊 <b>Полный журнал (продолжение)</b>\n",
            ] + c_lines
        else:
            current_lines.extend(c_lines)

    if updated_at:
        current_lines.append(f"🕒 <i>Данные обновлены: {updated_at}</i>")

    messages.append("\n".join(current_lines).strip())
    return messages
