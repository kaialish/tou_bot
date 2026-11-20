# -*- coding: utf-8 -*-
import re
from bs4 import BeautifulSoup

def extract_current_week(html: str) -> int:
    """
    Ищет номер текущей недели в HTML-коде (блок Неделя: <b>X</b>).
    Если не найден, возвращает 15 (по умолчанию).
    """
    soup = BeautifulSoup(html, "html.parser")
    # Ищем в тексте элементов
    for el in soup.find_all(string=re.compile(r'неделя\s*:\s*', re.IGNORECASE)):
        parent = el.parent
        # Ищем <b> рядом
        b_tag = parent.find("b") if parent else None
        if b_tag and b_tag.get_text(strip=True).isdigit():
            return int(b_tag.get_text(strip=True))
        
        # Или в строке: "Неделя: <b>7</b>"
        match = re.search(r'неделя\s*:\s*(?:<[^>]+>)?\s*(\d+)', str(parent), re.IGNORECASE)
        if match:
            return int(match.group(1))

    # Запасной regex по всему HTML
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

if __name__ == "__main__":
    from scratch.analyze_zhurnal import HTML_SAMPLE
    # В HTML_SAMPLE из запроса пользователя:
    # <div style="line-height: 16px; padding: 4px 10px 0 10px; text-transform: normal; color: red; font-weight: bold;">
    # Неделя: <b>7</b>, Числитель
    # </div>
    with open("scratch/test_week_html.html", "w", encoding="utf-8") as f:
        f.write('<div>Неделя: <b>7</b>, Числитель</div>')
    
    w = extract_current_week('<div>Неделя: <b>7</b>, Числитель</div>')
    print("Found week:", w)
