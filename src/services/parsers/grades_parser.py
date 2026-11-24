import re
from bs4 import BeautifulSoup

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


# Реэкспорт функций форматирования и расчёта для обратной совместимости
from src.services.parsers.grades_formatter import (  # noqa: E402, F401
    _calc_course_real_tu,
    _extract_courses_and_week,
    _filter_grades_by_current_week,
    _format_score,
    _get_part_week_range,
    _get_traffic_light,
    _shorten_fio,
    format_zhurnal_brief,
    format_zhurnal_full_chunks,
    get_zhurnal_part,
)
