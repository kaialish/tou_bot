from PIL import Image, ImageDraw, ImageFont
import io
from datetime import datetime

# Названия дней недели на русском (weekday() → индекс 0-6)
WEEKDAYS_RU = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

# Цвета акцента для разных типов занятий
TYPE_COLORS = {
    "лекция":   (99,  179, 237),   # голубой
    "практика": (104, 211, 145),   # зелёный
    "семинар":  (246, 173,  85),   # оранжевый
    "лаб":      (183, 148, 244),   # фиолетовый
}

# Цвета заголовков дней для недельного вида
DAY_HEADER_COLORS = [
    (37,  99, 171),   # Понедельник — синий
    (22, 128,  90),   # Вторник — зелёный
    (146,  64,  14),  # Среда — коричневый
    (91,  33, 182),   # Четверг — фиолетовый
    (190,  18,  60),  # Пятница — тёмно-красный
]

# Константы разметки
WIDTH        = 660
ROW_HEIGHT   = 90
HDR_HEIGHT   = 95     # шапка всего изображения
DAY_HDR_H    = 40     # высота плашки дня недели (только для week)
PADDING      = 18


def _get_accent_color(lesson_type: str) -> tuple:
    """Возвращает цвет акцента по типу занятия."""
    lower = lesson_type.lower()
    for key, color in TYPE_COLORS.items():
        if key in lower:
            return color
    return (148, 163, 184)  # серый по умолчанию


def _load_fonts() -> tuple:
    """Загружает шрифты. Возвращает (font_title, font_date, font_day, font_main, font_sub)."""
    candidates = ["arial.ttf", "ArialMT.ttf", "DejaVuSans.ttf"]
    for name in candidates:
        try:
            return (
                ImageFont.truetype(name, 22),
                ImageFont.truetype(name, 14),
                ImageFont.truetype(name, 15),
                ImageFont.truetype(name, 16),
                ImageFont.truetype(name, 13),
            )
        except IOError:
            continue
    default = ImageFont.load_default()
    return default, default, default, default, default


def _draw_lesson_card(draw, item: dict, x1: int, y: int, x2: int,
                      font_main, font_sub) -> None:
    """Рисует карточку одного занятия."""
    card_y1 = y + 4
    card_y2 = y + ROW_HEIGHT - 6

    draw.rectangle([x1, card_y1, x2, card_y2], fill=(255, 255, 255), outline=(214, 221, 232))

    accent = _get_accent_color(item.get("type", ""))
    draw.rectangle([x1, card_y1, x1 + 5, card_y2], fill=accent)

    # Левая колонка: время + тип
    draw.text((x1 + 16, card_y1 + 10), item.get("time", "--:--"), fill=(22, 45, 80), font=font_main)
    lesson_type = item.get("type", "")
    if lesson_type:
        draw.text((x1 + 16, card_y1 + 34), lesson_type[:18], fill=accent, font=font_sub)

    # Правая колонка: предмет + аудитория · преподаватель
    subject = item.get("subject", "Предмет не указан")
    draw.text((x1 + 145, card_y1 + 10), subject[:36], fill=(25, 30, 40), font=font_main)

    room    = item.get("room", "")
    teacher = item.get("teacher", "")
    if room and teacher:
        info = f"{room}  ·  {teacher}"[:46]
    elif room:
        info = f"Аудитория: {room}"
    else:
        info = teacher[:46]
    draw.text((x1 + 145, card_y1 + 36), info, fill=(100, 116, 139), font=font_sub)


def _draw_main_header(draw, title: str, date_str: str,
                      font_title, font_date) -> None:
    """Рисует общую шапку изображения."""
    draw.rectangle([0, 0, WIDTH, HDR_HEIGHT - 8], fill=(22, 45, 80))
    draw.text((PADDING, 16), title, fill=(255, 255, 255), font=font_title)
    draw.text((PADDING, 46), date_str, fill=(148, 187, 233), font=font_date)
    draw.rectangle([0, HDR_HEIGHT - 8, WIDTH, HDR_HEIGHT - 6], fill=(52, 95, 155))


# ─────────────────────────────────────────────────────────────────────────────
# Публичный API
# ─────────────────────────────────────────────────────────────────────────────

def generate_schedule_image(schedule_data: list[dict], title: str = "Расписание занятий") -> bytes:
    """
    Генерирует PNG-изображение расписания.

    Если в элементах есть поле "day" (недельный режим) — рисует секции по дням недели.
    Иначе — обычное однодневное расписание.
    """
    is_week = bool(schedule_data and "day" in schedule_data[0])

    if is_week:
        return _generate_week_image(schedule_data, title)
    else:
        return _generate_day_image(schedule_data, title)


def _generate_day_image(schedule_data: list[dict], title: str) -> bytes:
    """Рендер расписания на один день (сегодня / завтра)."""
    height = HDR_HEIGHT + (len(schedule_data) * ROW_HEIGHT) + PADDING
    if not schedule_data:
        height = 200

    image = Image.new("RGB", (WIDTH, height), color=(236, 240, 245))
    draw  = ImageDraw.Draw(image)

    font_title, font_date, _, font_main, font_sub = _load_fonts()

    now      = datetime.now()
    day_name = WEEKDAYS_RU[now.weekday()]
    date_str = f"{day_name}, {now.strftime('%d.%m.%Y')}"
    _draw_main_header(draw, title, date_str, font_title, font_date)

    if not schedule_data:
        draw.text((PADDING, HDR_HEIGHT + 30), "Занятий нет — свободный день!", fill=(100, 116, 139), font=font_main)
    else:
        y = HDR_HEIGHT + 6
        for item in schedule_data:
            _draw_lesson_card(draw, item, PADDING, y, WIDTH - PADDING, font_main, font_sub)
            y += ROW_HEIGHT

    return _to_bytes(image)


def _generate_week_image(schedule_data: list[dict], title: str) -> bytes:
    """Рендер недельного расписания с секциями по дням."""
    # Группируем занятия по дате (сохраняем порядок появления)
    days_order: list[str] = []
    days_map: dict[str, list[dict]] = {}
    for item in schedule_data:
        d = item["day"]   # строка вида "28.09.2026"
        if d not in days_map:
            days_map[d] = []
            days_order.append(d)
        days_map[d].append(item)

    # Вычисляем высоту: шапка + для каждого дня (заголовок дня + карточки)
    total_lessons = sum(len(v) for v in days_map.values())
    height = HDR_HEIGHT + len(days_order) * (DAY_HDR_H + 8) + total_lessons * ROW_HEIGHT + PADDING
    if not days_order:
        height = 200

    image = Image.new("RGB", (WIDTH, height), color=(236, 240, 245))
    draw  = ImageDraw.Draw(image)

    font_title, font_date, font_day, font_main, font_sub = _load_fonts()

    now      = datetime.now()
    date_str = f"Неделя, {now.strftime('%d.%m.%Y')}"
    _draw_main_header(draw, title, date_str, font_title, font_date)

    if not days_order:
        draw.text((PADDING, HDR_HEIGHT + 30), "Занятий на неделе нет!", fill=(100, 116, 139), font=font_main)
        return _to_bytes(image)

    y = HDR_HEIGHT + 6
    for idx, date_str_day in enumerate(days_order):
        color = DAY_HEADER_COLORS[idx % len(DAY_HEADER_COLORS)]

        # Определяем название дня недели по дате "28.09.2026"
        try:
            dt = datetime.strptime(date_str_day, "%d.%m.%Y")
            weekday_label = f"{WEEKDAYS_RU[dt.weekday()]}, {dt.strftime('%d.%m')}"
        except ValueError:
            weekday_label = date_str_day

        # Плашка с названием дня
        draw.rectangle([PADDING, y, WIDTH - PADDING, y + DAY_HDR_H], fill=color)
        draw.text((PADDING + 14, y + 11), weekday_label, fill=(255, 255, 255), font=font_day)
        y += DAY_HDR_H + 4

        lessons = days_map[date_str_day]
        if not lessons:
            draw.text((PADDING + 14, y + 8), "Занятий нет", fill=(100, 116, 139), font=font_sub)
            y += 30
        else:
            for item in lessons:
                _draw_lesson_card(draw, item, PADDING, y, WIDTH - PADDING, font_main, font_sub)
                y += ROW_HEIGHT

        y += 8  # отступ между днями

    return _to_bytes(image)


def _to_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()
