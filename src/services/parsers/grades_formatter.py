import re


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


def _get_part_week_range(current_week: int, part: int) -> range:
    """Недели выбранной части, уже наступившие по данным портала."""
    if part not in (1, 2):
        raise ValueError("part must be 1 or 2")
    start, end = (1, 8) if part == 1 else (9, 15)
    return range(start, min(max(1, current_week), end) + 1)


def _filter_grades_by_current_week(
    grades: list[dict], current_week: int, part: int = 1,
) -> tuple[list[dict], float | None, bool]:
    """Среднее по наступившим неделям части; пропуски равны нулю."""
    weeks = _get_part_week_range(current_week, part)
    if not weeks:
        return [], None, False
    result = []
    total = 0.0
    has_any_grade = False

    for w in weeks:
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

    avg = total / len(weeks)
    return result, avg, has_any_grade


def _calc_course_real_tu(
    activities: list[dict], current_week: int, fallback_tu: str = "", part: int = 1,
) -> tuple[float | None, bool]:
    """Среднее по видам занятий выбранной части, без недель другой части."""
    if not _get_part_week_range(current_week, part):
        return None, False
    act_avgs = []
    has_any = False
    for act in activities:
        grades = act.get(f"r{part}_grades", [])
        if not grades:
            continue
        _, avg, has_grade = _filter_grades_by_current_week(grades, current_week, part)
        if avg is not None:
            act_avgs.append(avg)
        if has_grade:
            has_any = True

    if act_avgs:
        return sum(act_avgs) / len(act_avgs), has_any

    # Если активности пустые
    if fallback_tu:
        val_clean = fallback_tu.replace(",", ".").strip()
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


def get_zhurnal_part(zhurnal_data: list[dict] | dict) -> int:
    """С девятой недели по умолчанию открывается вторая часть."""
    _, current_week = _extract_courses_and_week(zhurnal_data)
    return 2 if current_week >= 9 else 1


def format_zhurnal_brief(
    zhurnal_data: list[dict] | dict, updated_at: str = "", part: int | None = None,
) -> str:
    """
    Форматирует краткий вид успеваемости по строгому шаблону:
    📚 [Название предмета]
       💡 ТУ1: [Реальный балл] • РК1: [Балл] • Р1: [Балл] [Эмодзи]
    (Если нет силлабуса: ⚠️ Силлабус не сформирован.)
    """
    courses, current_week = _extract_courses_and_week(zhurnal_data)
    part = get_zhurnal_part(zhurnal_data) if part is None else part
    elapsed_weeks = len(_get_part_week_range(current_week, part))
    part_label = f"{part}-я часть · недели {'1–8' if part == 1 else '9–15'}"

    if not courses:
        return "📊 <b>Успеваемость</b>\n\n<i>Данные об успеваемости не найдены.</i>"

    lines = [
        f"📊 <b>Успеваемость · Краткий вид</b> · {part_label} (Неделя: {current_week})",
        "─────────────────────────",
    ]

    if not elapsed_weeks:
        lines.append("<i>Эта часть обучения ещё не началась.</i>")

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

        # Средний балл только за выбранную часть.
        real_tu, has_any_grade = _calc_course_real_tu(
            activities, current_week, fallback_tu=summary.get(f"tu{part}", ""), part=part,
        )
        display_tu = _format_score(real_tu) if real_tu is not None else "—"
        rk = _format_score(summary.get(f"rk{part}", ""))
        rating = _format_score(summary.get(f"r{part}", ""))

        # Светофор на основе реального балла
        traffic = _get_traffic_light(real_tu, current_week=elapsed_weeks, has_any_grade=has_any_grade)

        lines.append(f"   💡 ТУ{part}: <b>{display_tu}</b> • РК{part}: <b>{rk}</b> • Р{part}: <b>{rating}</b> {traffic}\n")

    lines.append("─────────────────────────")
    if updated_at:
        lines.append(f"🕒 <i>Данные обновлены: {updated_at}</i>")

    return "\n".join(lines).strip()


def format_zhurnal_full_chunks(
    zhurnal_data: list[dict] | dict, updated_at: str = "", part: int | None = None,
) -> list[str]:
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
    part = get_zhurnal_part(zhurnal_data) if part is None else part
    elapsed_weeks = len(_get_part_week_range(current_week, part))
    part_label = f"{part}-я часть · недели {'1–8' if part == 1 else '9–15'}"

    if not courses:
        return ["📊 <b>Полный журнал успеваемости</b>\n\n<i>Данные об успеваемости не найдены.</i>"]

    messages = []
    current_lines = [
        f"📊 <b>Полный журнал успеваемости</b> · {part_label} (Неделя: {current_week})",
        "",
    ]

    if not elapsed_weeks:
        current_lines.append("<i>Эта часть обучения ещё не началась.</i>")

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
            real_tu, has_any_grade = _calc_course_real_tu(
                activities, current_week, fallback_tu=summary.get(f"tu{part}", ""), part=part,
            )
            display_tu = _format_score(real_tu) if real_tu is not None else "—"
            rk = _format_score(summary.get(f"rk{part}", ""))
            rating = _format_score(summary.get(f"r{part}", ""))
            traffic = _get_traffic_light(real_tu, current_week=elapsed_weeks, has_any_grade=has_any_grade)

            c_lines.append("─────────────────────────")
            c_lines.append(f"🎯 <b>Итог:</b> ТУ{part}: <b>{display_tu}</b> • РК{part}: <b>{rk}</b> • Р{part}: <b>{rating}</b> {traffic}\n")

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

                grades = act.get(f"r{part}_grades", [])
                if not grades:
                    continue
                filtered, real_avg, _ = _filter_grades_by_current_week(grades, current_week, part)

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
                f"📊 <b>Полный журнал (продолжение)</b> · {part_label}\n",
            ] + c_lines
        else:
            current_lines.extend(c_lines)

    if updated_at:
        current_lines.append(f"🕒 <i>Данные обновлены: {updated_at}</i>")

    messages.append("\n".join(current_lines).strip())
    return messages
