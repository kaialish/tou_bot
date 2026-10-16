import io
import os
from functools import lru_cache
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

# ─────────────────────────────────────────────────────────────────────────────
# Пути к шрифтам
# ─────────────────────────────────────────────────────────────────────────────
FONT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "assets", "fonts", "gros-ventre"
)

# Системные шрифты Windows, поддерживающие казахский алфавит (фолбэк)
_KAZ_FALLBACK_PATHS = [
    r"C:\Windows\Fonts\seguisb.ttf",    # Segoe UI Semibold — лучший вариант
    r"C:\Windows\Fonts\segoeuib.ttf",   # Segoe UI Bold
    r"C:\Windows\Fonts\segoeui.ttf",    # Segoe UI Regular
    r"C:\Windows\Fonts\arialbd.ttf",    # Arial Bold
    r"C:\Windows\Fonts\arial.ttf",      # Arial
]

# Казахские буквы, которых нет в стандартном кириллическом блоке
_KAZAKH_CHARS = frozenset("ӘәҒғҚқҢңӨөҰұҮүІіҺһ")

# ─────────────────────────────────────────────────────────────────────────────
# Дни недели
# ─────────────────────────────────────────────────────────────────────────────
WEEKDAYS_RU = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

WEEKDAY_MAP = {
    "понедельник": 0, "вторник": 1, "среда": 2,
    "четверг": 3, "пятница": 4, "суббота": 5, "воскресенье": 6,
}

# ─────────────────────────────────────────────────────────────────────────────
# Палитра фонов по дням недели (фон, цвет водяного знака)
# ─────────────────────────────────────────────────────────────────────────────
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

# ─────────────────────────────────────────────────────────────────────────────
# Константы разметки
# ─────────────────────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────────────────────
# Утилиты
# ─────────────────────────────────────────────────────────────────────────────

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


def _expand_lesson_type(raw_type: str) -> str:
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


def _has_kazakh(text: str) -> bool:
    """Проверяет, содержит ли строка казахские буквы."""
    return any(c in _KAZAKH_CHARS for c in text)


def _font_width(font: ImageFont.ImageFont, text: str) -> int:
    bb = font.getbbox(text)
    return bb[2] - bb[0]


# ─────────────────────────────────────────────────────────────────────────────
# Загрузка шрифтов (кэшировано)
# ─────────────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _find_kaz_path() -> str | None:
    """Возвращает путь к первому доступному шрифту с поддержкой казахского."""
    for path in _KAZ_FALLBACK_PATHS:
        if os.path.exists(path):
            return path
    return None


@lru_cache(maxsize=1)
def _load_fonts() -> dict:
    """Кэшированная загрузка шрифтов Gros-Ventre + казахский фолбэк."""
    def _gv(filename: str, fallback: str, size: int) -> ImageFont.ImageFont:
        path = os.path.join(FONT_DIR, filename)
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except IOError:
                pass
        try:
            return ImageFont.truetype(fallback, size)
        except IOError:
            return ImageFont.load_default()

    def _kaz(size: int) -> ImageFont.ImageFont | None:
        p = _find_kaz_path()
        if p:
            try:
                return ImageFont.truetype(p, size)
            except IOError:
                pass
        return None

    return {
        "bold":  lambda sz: _gv("Gros-Ventre-Bold.ttf",     "arialbd.ttf", sz),
        "semi":  lambda sz: _gv("Gros-Ventre-Semibold.ttf", "arialbd.ttf", sz),
        "reg":   lambda sz: _gv("Gros-Ventre-Regular.ttf",  "arial.ttf",   sz),
        "light": lambda sz: _gv("Gros-Ventre-Light.ttf",    "arial.ttf",   sz),
        "kaz":   _kaz,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Смешанный рендеринг: Gros-Ventre для обычных символов, Segoe UI для казахских
# ─────────────────────────────────────────────────────────────────────────────

def _draw_mixed(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    main_font: ImageFont.ImageFont,
    kaz_font: ImageFont.ImageFont | None,
    fill: tuple,
) -> None:
    """
    Рисует текст посегментно: обычные символы — main_font (Gros-Ventre),
    казахские буквы — kaz_font (Segoe UI). Если kaz_font недоступен — весь
    текст через main_font.
    """
    if not text:
        return
    if not _has_kazakh(text) or kaz_font is None:
        draw.text(xy, text, font=main_font, fill=fill)
        return

    x, y = xy
    segment = ""
    in_kaz = text[0] in _KAZAKH_CHARS

    for ch in text:
        ch_is_kaz = ch in _KAZAKH_CHARS
        if ch_is_kaz != in_kaz:
            font = kaz_font if in_kaz else main_font
            draw.text((x, y), segment, font=font, fill=fill)
            x += _font_width(font, segment)
            segment = ch
            in_kaz = ch_is_kaz
        else:
            segment += ch

    if segment:
        font = kaz_font if in_kaz else main_font
        draw.text((x, y), segment, font=font, fill=fill)


def _mixed_width(
    text: str,
    main_font: ImageFont.ImageFont,
    kaz_font: ImageFont.ImageFont | None,
) -> int:
    """Ширина текста с учётом смешанных шрифтов."""
    if not text or not _has_kazakh(text) or kaz_font is None:
        return _font_width(main_font, text) if text else 0

    total, segment, in_kaz = 0, "", text[0] in _KAZAKH_CHARS
    for ch in text:
        ch_is_kaz = ch in _KAZAKH_CHARS
        if ch_is_kaz != in_kaz:
            total += _font_width(kaz_font if in_kaz else main_font, segment)
            segment, in_kaz = ch, ch_is_kaz
        else:
            segment += ch
    if segment:
        total += _font_width(kaz_font if in_kaz else main_font, segment)
    return total


def _fit_mixed(
    text: str,
    main_font: ImageFont.ImageFont,
    kaz_font: ImageFont.ImageFont | None,
    max_width: int = CONTENT_MAX_WIDTH,
) -> str:
    """Обрезает mixed-текст с '…', если превышает max_width."""
    if not text or _mixed_width(text, main_font, kaz_font) <= max_width:
        return text
    while text:
        candidate = text + "…"
        if _mixed_width(candidate, main_font, kaz_font) <= max_width:
            return candidate
        text = text[:-1]
    return "…"


# ─────────────────────────────────────────────────────────────────────────────
# Водяной знак
# ─────────────────────────────────────────────────────────────────────────────

def _draw_toubot_watermark(canvas: Image.Image, canvas_height: int, wm_color: tuple) -> None:
    """Отрисовывает вертикальный водяной знак 'TOUBOT' вдоль левого края."""
    fonts = _load_fonts()
    wm_font = fonts["bold"](190)
    wm_txt = "TOUBOT"

    bbox = wm_font.getbbox(wm_txt)
    wm_w = bbox[2] - bbox[0] + 40
    wm_h = bbox[3] - bbox[1] + 50

    wm_img = Image.new("RGBA", (wm_w, wm_h), (0, 0, 0, 0))
    wm_draw = ImageDraw.Draw(wm_img)
    wm_draw.text((10, 10), wm_txt, font=wm_font, fill=wm_color + (255,))

    rotated_wm = wm_img.rotate(270, expand=True)

    if rotated_wm.height > canvas_height - 120:
        crop_h = max(10, canvas_height - 130)
        rotated_wm = rotated_wm.crop((0, 0, rotated_wm.width, crop_h))

    canvas.paste(rotated_wm, (-15, 135), rotated_wm)


def _to_bytes(image: Image.Image) -> bytes:
    bio = io.BytesIO()
    image.save(bio, format="PNG", optimize=True)
    bio.seek(0)
    return bio.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Основная функция рендеринга карточки
# ─────────────────────────────────────────────────────────────────────────────

def _render_card(
    schedule_data: list[dict],
    header_title: str = "Расписание",
    header_subtitle: str = "",
    day_key: str = "",
) -> bytes:
    """Рендерит карточку расписания. day_key определяет цвет фона."""
    fonts  = _load_fonts()
    f_bold = fonts["bold"]
    f_reg  = fonts["reg"]
    f_light = fonts["light"]
    f_kaz  = fonts["kaz"]   # callable(size) -> font | None

    bg_color, wm_color = DAY_PALETTES.get(day_key, (BG_DEFAULT, WM_DEFAULT))

    count = len(schedule_data)
    row_h = ROW_HEIGHT_LARGE if count >= 5 else ROW_HEIGHT_SMALL

    if count == 0:
        height = 440
    else:
        height = max(580, HEADER_START_Y + count * row_h + 44)

    image = Image.new("RGB", (WIDTH, height), bg_color)
    draw  = ImageDraw.Draw(image)

    # 1. Водяной знак
    _draw_toubot_watermark(image, height, wm_color)

    # 2. Заголовок «Расписание»
    draw.text((CONTENT_X1, 36), header_title, font=f_bold(46), fill=TEXT_WHITE)

    # 3. Подзаголовок (день + дата)
    if header_subtitle:
        draw.text((CONTENT_X1, 84), header_subtitle, font=f_light(24), fill=TEXT_MUTED)

    # 4. Разделитель под шапкой
    draw.line([(CONTENT_X1, HEADER_START_Y), (CONTENT_X2, HEADER_START_Y)],
              fill=DIVIDER_COLOR, width=1)

    # 5. Занятия
    if count == 0:
        free_y = HEADER_START_Y + 64
        draw.text((CONTENT_X1, free_y),      "Занятий нет",    font=f_bold(30),  fill=TEXT_WHITE)
        draw.text((CONTENT_X1, free_y + 46), "Свободный день!", font=f_light(20), fill=TEXT_MUTED)
    else:
        y = HEADER_START_Y
        for idx, item in enumerate(schedule_data, 1):
            time_raw     = item.get("time", "--:--")
            time_display = time_raw.replace(":", ".")
            time_text    = f"{idx}.  {time_display}"

            subject     = item.get("subject", "Предмет не указан")
            lesson_type = _expand_lesson_type(item.get("type", ""))
            room        = item.get("room",    "")
            teacher     = item.get("teacher", "")

            # Вертикальные позиции строк внутри ячейки
            line1_y = y + 18    # Номер и время
            line2_y = y + 58    # Название предмета
            line3_y = y + 84    # Тип занятия
            line4_y = y + 108   # Аудитория
            line5_y = y + 130   # Преподаватель

            # ── Строка 1: номер + время (Bold 26px) ──────────────────────
            draw.text((CONTENT_X1, line1_y), time_text, font=f_bold(26), fill=TEXT_WHITE)

            # ── Строка 2: предмет (Bold 16px, mixed) ─────────────────────
            kaz16     = f_kaz(16)
            fit_subj  = _fit_mixed(subject, f_bold(16), kaz16, CONTENT_MAX_WIDTH)
            _draw_mixed(draw, (CONTENT_X1, line2_y), fit_subj, f_bold(16), kaz16, TEXT_WHITE)

            # ── Строка 3: тип (Regular 14px) ─────────────────────────────
            if lesson_type:
                draw.text((CONTENT_X1, line3_y), lesson_type, font=f_reg(14), fill=TEXT_MUTED)

            # ── Строка 4: аудитория (Regular 14px, mixed) ────────────────
            if room:
                room_text = room if ("-" in room or len(room) <= 8) else f"Ауд. {room}"
                kaz14 = f_kaz(14)
                _draw_mixed(draw, (CONTENT_X1, line4_y), room_text, f_reg(14), kaz14, TEXT_MUTED)

            # ── Строка 5: преподаватель (Bold 15px, mixed) ────────────────
            if teacher:
                kaz15      = f_kaz(15)
                fit_teacher = _fit_mixed(teacher, f_bold(15), kaz15, CONTENT_MAX_WIDTH)
                _draw_mixed(draw, (CONTENT_X1, line5_y), fit_teacher, f_bold(15), kaz15, TEXT_WHITE)

            y += row_h
            draw.line([(CONTENT_X1, y), (CONTENT_X2, y)], fill=DIVIDER_COLOR, width=1)

    return _to_bytes(image)


# ─────────────────────────────────────────────────────────────────────────────
# Публичный API
# ─────────────────────────────────────────────────────────────────────────────

def generate_schedule_image(
    schedule_data: list[dict],
    title: str = "Расписание занятий",
    day_mode: str = "today",
) -> bytes:
    """
    Генерирует PNG-карточку расписания на один день (Сегодня / Завтра).
    Цвет фона зависит от дня недели.
    """
    target_dt = datetime.now()
    if day_mode == "tomorrow":
        target_dt += timedelta(days=1)

    day_name = WEEKDAYS_RU[target_dt.weekday()]
    day_key  = day_name.lower()
    date_str = target_dt.strftime("%d.%m.%Y")
    subtitle = f"{day_name}  {date_str}"

    return _render_card(
        schedule_data=schedule_data,
        header_title="Расписание",
        header_subtitle=subtitle,
        day_key=day_key,
    )


def generate_week_album(schedule_data: list[dict]) -> list[tuple[str, bytes]]:
    """
    Генерирует PNG-карточки для каждого дня недели (для альбома).
    Каждая карточка имеет свой цвет фона по дню.
    Возвращает список пар (отображаемое_имя_с_датой, png_bytes).
    """
    days_order: list[str] = []
    days_map:  dict[str, list[dict]] = {}

    for item in schedule_data:
        d = item.get("day", "").strip()
        if not d:
            continue
        if d not in days_map:
            days_map[d] = []
            days_order.append(d)
        days_map[d].append(item)

    days_order.sort(key=lambda name: WEEKDAY_MAP.get(name.strip().lower(), 99))

    result: list[tuple[str, bytes]] = []
    for day_name in days_order:
        lessons  = days_map[day_name]
        dt       = get_weekday_date(day_name)
        date_str = dt.strftime("%d.%m.%Y") if dt else ""
        subtitle = f"{day_name}  {date_str}".strip()
        day_key  = day_name.strip().lower()

        png = _render_card(
            schedule_data=lessons,
            header_title="Расписание",
            header_subtitle=subtitle,
            day_key=day_key,
        )
        display_name = f"{day_name} — {date_str}" if date_str else day_name
        result.append((display_name, png))

    return result
