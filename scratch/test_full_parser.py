# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup
import re

def parse_zhurnal_table(table):
    """
    Разбирает таблицу успеваемости дисциплины ToU.
    Возвращает словарь с:
      - groups: список групп занятий (например, 'Лекции', 'Практические/Семинарские')
        внутри каждой группы:
          - rating_1_grades: список оценок за 1-8 недели (неделя, оценка)
          - rating_1_avg: среднее за 1 рейтинг
          - rating_2_grades: список оценок за 9-15 недели (неделя, оценка)
          - rating_2_avg: среднее за 2 рейтинг
      - summary:
          - tu1: текущая успеваемость 1 (ТУ1)
          - rk1: рубежный контроль 1 (РК1)
          - r1: итоговый 1 рейтинг (Р1)
          - tu2: текущая успеваемость 2 (ТУ2)
          - rk2: рубежный контроль 2 (РК2)
          - r2: итоговый 2 рейтинг (Р2)
          - rd: рейтинг допуска
          - exam: экзамен / зачет
          - final: итоговая оценка
    """
    rows = table.find_all("tr")
    if len(rows) < 4:
        return None

    # Посмотрим row 1 (типы занятий и сводные блоки)
    row1_cells = rows[1].find_all(["td", "th"])
    # row 2 (номера недель 1..8, Сред. знач., ТУ1, РК1 и т.д.)
    row2_cells = rows[2].find_all(["td", "th"])
    # row 3 (значения)
    row3_cells = rows[3].find_all(["td", "th"])
    
    # row3_cells[0] - "Входной контроль"
    # row3_cells[-1] - "Итоговая оценка"
    # row3_cells[-2] - "Курсовая работа (из журнала)"
    # row3_cells[-3] - "Курсовая работа (из ведомости)"
    # row3_cells[-4] - "Экзамен/Зачет"
    # row3_cells[-5] - "Рейтинг допуска"
    
    # Сопоставим row1_cells с их colspan и row2_cells
    col_idx = 0
    groups_info = []
    
    # Для каждого блока в row1
    row2_idx = 0
    row3_idx = 1 # т.к. 0 - Входной контроль
    
    sections_by_type = {} # "Лекции": {"r1_grades": [], "r1_avg": "", "r2_grades": [], "r2_avg": ""}
    
    # Разбор row1_cells
    # Пример row1_cells:
    # 0: Лекции (colspan=9) -> 1..8 недели + Сред. знач.
    # 1: Практические (colspan=9) -> 1..8 недели + Сред. знач.
    # 2: Текущие (colspan=2) -> ТУ1, РК1
    # 3: Из ведомости (colspan=2) -> ТУ1, РК1
    # 4: Р1 (rowspan=2) -> значение Р1
    # 5: Лекции (colspan=8) -> 9..15 недели + Сред. знач.
    # 6: Практические (colspan=8) -> 9..15 недели + Сред. знач.
    # 7: Текущие (colspan=2) -> ТУ2, РК2
    # 8: Из ведомости (colspan=2) -> ТУ2, РК2
    # 9: Р2 (rowspan=2) -> значение Р2
    
    summary = {
        "tu1": "",
        "rk1": "",
        "r1": "",
        "tu2": "",
        "rk2": "",
        "r2": "",
        "rd": row3_cells[-5].get_text(strip=True) if len(row3_cells) >= 5 else "",
        "exam": row3_cells[-4].get_text(strip=True) if len(row3_cells) >= 4 else "",
        "final": row3_cells[-1].get_text(strip=True) if len(row3_cells) >= 1 else ""
    }
    
    # Определим текущий этап по порядку
    current_rating = 1
    
    for r1_cell in row1_cells:
        name = r1_cell.get_text(strip=True)
        colspan = int(r1_cell.get("colspan", 1))
        rowspan = int(r1_cell.get("rowspan", 1))
        
        if "Р1" in name or name == "Р1":
            # Р1 это ячейка с rowspan=2, в row2 для неё нет ячейки
            val = row3_cells[row3_idx].get_text(strip=True)
            summary["r1"] = val
            row3_idx += 1
            current_rating = 2
            continue
            
        if "Р2" in name or name == "Р2":
            val = row3_cells[row3_idx].get_text(strip=True)
            summary["r2"] = val
            row3_idx += 1
            continue
            
        # Если это Текущие / Из ведомости
        if "Текущие" in name:
            # colspan=2 -> ТУ, РК
            tu_val = row3_cells[row3_idx].get_text(strip=True)
            rk_val = row3_cells[row3_idx+1].get_text(strip=True)
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
            # Из ведомости нам не обязательно дублировать, но сдвигаем индексы
            row2_idx += colspan
            row3_idx += colspan
            continue
            
        # Иначе это конкретный тип занятий: Лекции, Практические, Лабораторные и т.д.
        activity_type = name
        if activity_type not in sections_by_type:
            sections_by_type[activity_type] = {
                "type": activity_type,
                "r1_grades": [],
                "r1_avg": "",
                "r2_grades": [],
                "r2_avg": ""
            }
            
        # Собираем недели из row2 и значения из row3
        for i in range(colspan):
            col_header = row2_cells[row2_idx].get_text(strip=True)
            val = row3_cells[row3_idx].get_text(strip=True)
            
            if "сред" in col_header.lower():
                if current_rating == 1:
                    sections_by_type[activity_type]["r1_avg"] = val
                else:
                    sections_by_type[activity_type]["r2_avg"] = val
            else:
                # Номер недели
                grade_item = {"week": col_header, "grade": val}
                if current_rating == 1:
                    sections_by_type[activity_type]["r1_grades"].append(grade_item)
                else:
                    sections_by_type[activity_type]["r2_grades"].append(grade_item)
                    
            row2_idx += 1
            row3_idx += 1
            
    return {
        "activities": list(sections_by_type.values()),
        "summary": summary
    }

def parse_zhurnal_page(html: str) -> list[dict]:
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
                "note": empty_el.get_text(strip=True)
            })
            continue
            
        table = sec.find("table")
        if not table:
            continue
            
        parsed_table = parse_zhurnal_table(table)
        courses.append({
            "title": title,
            "teachers": teachers,
            "has_data": True,
            "data": parsed_table
        })
        
    return courses
