# -*- coding: utf-8 -*-
import re

def shorten_fio(fio: str) -> str:
    """
    Сокращает ФИО строго до инициалов:
    'Потапенко Александра Олеговна' -> 'Потапенко А. О.'
    'Шабамбаева Анара Габдулбариевна' -> 'Шабамбаева А. Г.'
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

def get_traffic_light(score_str: str) -> str:
    """
    Светофор успеваемости:
    🟢 — 70-100 баллов
    🟠 — 50-69 баллов
    🔴 — 0-49 баллов
    """
    if not score_str:
        return "🔴"
    # Очищаем от нецифровых символов (кроме точки и запятой)
    val_clean = score_str.replace(",", ".").strip()
    match = re.search(r'[-+]?\d*\.?\d+', val_clean)
    if not match:
        return "🔴"
    try:
        score = float(match.group())
        if score >= 70.0:
            return "🟢"
        elif score >= 50.0:
            return "🟠"
        else:
            return "🔴"
    except Exception:
        return "🔴"

def format_score(val: str) -> str:
    """Округление: Дробные баллы сокращает до 1-2 знаков."""
    if not val:
        return "0"
    val_clean = val.replace(",", ".").strip()
    match = re.search(r'[-+]?\d*\.?\d+', val_clean)
    if not match:
        return val.strip()
    try:
        num = float(match.group())
        if num.is_integer():
            return str(int(num))
        # округляем до 2 знаков, если последний 0 - убираем (например 60.50 -> 60.5)
        formatted = f"{num:.2f}".rstrip("0").rstrip(".")
        return formatted
    except Exception:
        return val.strip()

def filter_grades_trailing_zeros(grades: list[dict]) -> list[dict]:
    """
    Недели: Фильтрует массив. УДАЛЯЕТ все пустые/нулевые недели, если после них нет оценок.
    Например:
    [80, 80, 80, 80, 80, 80, 0, 0] -> оставляет недели 1..6 с 80.
    [90, 90, 0, 0, 0, 0, 0, 0] -> оставляет недели 1..2.
    [0, 70, 80, 0] -> если внутри есть 0, но дальше 70, оставляет до последней непустой.
    """
    # Найдем последний индекс, где оценка не пустая и не равна '0'
    last_valid_idx = -1
    for i, g in enumerate(grades):
        val = str(g.get("grade", "")).strip()
        if val != "" and val != "0":
            last_valid_idx = i

    if last_valid_idx == -1:
        return []
    
    return grades[:last_valid_idx + 1]

if __name__ == "__main__":
    print(shorten_fio("Потапенко Александра Олеговна"))
    print(shorten_fio("Сүйіндік Нұртас Мерхатұлы"))
    print(get_traffic_light("74.63"))
    print(get_traffic_light("60"))
    print(get_traffic_light("45.32"))
    print(format_score("45.3200"))
    print(format_score("60.00"))
    test_grades = [{'week': str(i+1), 'grade': g} for i, g in enumerate(['80', '80', '80', '80', '80', '80', '0', '0'])]
    filtered = filter_grades_trailing_zeros(test_grades)
    print("Filtered:", [f"{g['week']}н: {g['grade']}" for g in filtered])
