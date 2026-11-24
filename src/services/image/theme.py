from datetime import datetime, timedelta

WEEKDAYS_RU = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

WEEKDAY_MAP = {
    "понедельник": 0, "вторник": 1, "среда": 2,
    "четверг": 3, "пятница": 4, "суббота": 5, "воскресенье": 6,
}

# Палитра фонов по дням недели: (фон, цвет водяного знака)
DAY_PALETTES: dict[str, tuple[tuple, tuple]] = {
    "понедельник": ((2,  34, 40), (30, 64, 70)),   # Тёмный изумруд
    "вторник":     ((4,  25, 52), (28, 50, 82)),   # Тёмный синий
    "среда":       ((38, 18, 48), (68, 40, 78)),   # Тёмный фиолетовый
    "четверг":     ((20, 40, 18), (42, 72, 38)),   # Тёмный зелёный
    "пятница":     ((48, 22, 18), (78, 46, 40)),   # Тёмный красный / бордо
    "суббота":     ((50, 36,  6), (82, 62, 22)),   # Тёмный янтарный
    "воскресенье": ((35, 35, 35), (62, 62, 62)),   # Тёмный серый
}
BG_DEFAULT = (2, 34, 40)
WM_DEFAULT = (30, 64, 70)

# Общие цвета текста
TEXT_WHITE    = (255, 255, 255)
TEXT_MUTED    = (210, 230, 230)
DIVIDER_COLOR = (245, 250, 250)

# Константы разметки карточки
WIDTH             = 724
HEADER_START_Y    = 116
CONTENT_X1        = 178
CONTENT_X2        = 630
CONTENT_MAX_WIDTH = CONTENT_X2 - CONTENT_X1

ROW_HEIGHT_LARGE = 148   # 5+ пар
ROW_HEIGHT_SMALL = 168   # 1-4 пары

TYPE_EXPANSIONS = {
    "лек.":      "Лекция",
    "пр.":       "Практика",
    "лаб.":      "Лабораторная",
    "сем.":      "Семинар",
    "пр./сем.":  "Практика",
    "лаб./сем.": "Лабораторная",
}


def get_weekday_date(day_name: str, base_dt: datetime | None = None) -> datetime | None:
    """Вычисляет дату для дня недели в текущей учебной неделе."""
    if base_dt is None:
        base_dt = datetime.now()
    clean = day_name.strip().lower()
    idx = WEEKDAY_MAP.get(clean)
    if idx is None:
        return None
    if base_dt.weekday() == 6:
        monday = base_dt + timedelta(days=1)
    else:
        monday = base_dt - timedelta(days=base_dt.weekday())
    return monday + timedelta(days=idx)


def expand_lesson_type(raw_type: str) -> str:
    """Преобразует сокращённый тип занятия в полное читаемое название."""
    if not raw_type:
        return ""
    clean = raw_type.strip().lower()
    for k, v in TYPE_EXPANSIONS.items():
        if k in clean:
            return v
    if "лек" in clean:
        return "Лекция"
    if "прак" in clean or "пр" in clean:
        return "Практика"
    if "лаб" in clean:
        return "Лабораторная"
    if "сем" in clean:
        return "Семинар"
    return raw_type.capitalize()
