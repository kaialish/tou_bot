from bs4 import BeautifulSoup
import re

def parse_zhurnal(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    courses = []
    
    sections = soup.select("section.student-zhurnal__course")
    for sec in sections:
        head = sec.select_one(".student-zhurnal__course-head")
        if not head:
            continue
        h2 = head.find("h2")
        title = h2.get_text(strip=True) if h2 else "Без названия"
        
        # Преподаватели
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
                "empty_note": empty_el.get_text(strip=True),
                "has_data": False
            })
            continue
            
        table = sec.find("table")
        if not table:
            continue
            
        rows = table.find_all("tr")
        if len(rows) < 4:
            continue
            
        data_row = rows[-1]
        data_tds = data_row.find_all("td")
        
        # Попробуем собрать структуру
        # Давайте распечатаем заголовки и ячейки
        courses.append({
            "title": title,
            "teachers": teachers,
            "tds_count": len(data_tds),
            "tds_text": [td.get_text(strip=True) for td in data_tds],
            "has_data": True
        })
        
    return courses

if __name__ == "__main__":
    import json
    with open("debug_zhurnal_sample.html", "w", encoding="utf-8") as f:
        # We can test with the provided HTML
        pass
