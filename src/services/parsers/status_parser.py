import re
from bs4 import BeautifulSoup

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

                # Для флюорографии оставляем только дату действия
                if "флюорограф" in name.lower() or "флюрограф" in name.lower():
                    date_match = re.search(r'(\d{2}[./-]\d{2}[./-]\d{2,4})', val)
                    if date_match:
                        val = f"до {date_match.group(1).replace('-', '.').replace('/', '.')}"

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
            if "флюорограф" in display_name.lower() or "флюрограф" in display_name.lower():
                date_match = re.search(r'(\d{2}[./-]\d{2}[./-]\d{2,4})', val)
                if date_match:
                    val = f"до {date_match.group(1).replace('-', '.').replace('/', '.')}"

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
