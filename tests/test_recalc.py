# -*- coding: utf-8 -*-
import re

def filter_grades_and_calc_avg(grades: list[dict]) -> tuple[list[dict], float | None]:
    """
    1. Находит последнюю реальную оценку (не пустую и не '0').
    2. Оставляет все недели от начала до этой оценки (включая внутренние нули-долги).
    3. Вычисляет реальный средний балл: сумма / количество оставшихся недель.
    """
    last_valid_idx = -1
    for i, g in enumerate(grades):
        val = str(g.get("grade", "")).strip()
        if val != "" and val != "0":
            last_valid_idx = i

    if last_valid_idx == -1:
        return [], None

    filtered = grades[:last_valid_idx + 1]

    # Считаем сумму и среднее
    total = 0.0
    for g in filtered:
        val = str(g.get("grade", "")).strip().replace(",", ".")
        match = re.search(r'[-+]?\d*\.?\d+', val)
        if match:
            total += float(match.group())

    avg = total / len(filtered)
    return filtered, avg

def get_traffic_light_from_score(score: float | None) -> str:
    """
    🟢 — 70-100 баллов (Всё отлично)
    🟠 — 50-69 баллов (На грани)
    🔴 — 0-49 баллов (Реальные завалы по прошедшим неделям)
    ⚪ — Оценок еще нет вообще (Семестр только начался).
    """
    if score is None:
        return "⚪"
    if score >= 70.0:
        return "🟢"
    elif score >= 50.0:
        return "🟠"
    else:
        return "🔴"

def calculate_course_real_tu(activities: list[dict]) -> float | None:
    """
    Считает реальный средний балл текущей успеваемости по дисциплине
    на основе реальных средних по типам занятий.
    """
    act_avgs = []
    for act in activities:
        r1_grades = act.get("r1_grades", [])
        _, avg = filter_grades_and_calc_avg(r1_grades)
        if avg is not None:
            act_avgs.append(avg)

    if not act_avgs:
        return None
    return sum(act_avgs) / len(act_avgs)

if __name__ == "__main__":
    # Тест 1: Лекции Истории: 80, 80, 80, 80, 80, 80, 0, 0 (6 недель по 80)
    g1 = [{'week': str(i+1), 'grade': x} for i, x in enumerate(['80', '80', '80', '80', '80', '80', '0', '0'])]
    f1, avg1 = filter_grades_and_calc_avg(g1)
    print("Test 1 (История лекции): len:", len(f1), "avg:", avg1) # 6, 80.0

    # Тест 2: Практика Истории: 70, 60, 50, 65, 0, 0, 0, 0 (4 недели)
    g2 = [{'week': str(i+1), 'grade': x} for i, x in enumerate(['70', '60', '50', '65', '0', '0', '0', '0'])]
    f2, avg2 = filter_grades_and_calc_avg(g2)
    print("Test 2 (История практика): len:", len(f2), "avg:", avg2) # 4, (70+60+50+65)/4 = 61.25

    # Общий ТУ: (80 + 61.25)/2 = 70.625 -> светофор 🟢 (а официальный был 45.32 🔴!)
    tu = (avg1 + avg2) / 2
    print("Real TU:", tu, "Traffic:", get_traffic_light_from_score(tu))

    # Тест 3: Предмет без оценок (все 0 или пусто)
    g3 = [{'week': str(i+1), 'grade': x} for i, x in enumerate(['', '', '0', '0'])]
    f3, avg3 = filter_grades_and_calc_avg(g3)
    print("Test 3 (без оценок): len:", len(f3), "avg:", avg3, "Traffic:", get_traffic_light_from_score(avg3))
