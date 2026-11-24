import os
from functools import lru_cache
from PIL import ImageDraw, ImageFont

from src.services.image.theme import CONTENT_MAX_WIDTH

FONT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "assets", "fonts", "gros-ventre"
)

# Системные шрифты (Windows и Linux/Docker), поддерживающие казахский алфавит (фолбэк)
_KAZ_FALLBACK_PATHS = [
    r"C:\Windows\Fonts\seguisb.ttf",
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
]

# Казахские буквы, которых нет в стандартном кириллическом блоке
_KAZAKH_CHARS = frozenset("ӘәҒғҚқҢңӨөҰұҮүІіҺһ")


def _has_kazakh(text: str) -> bool:
    """Проверяет, содержит ли строка казахские буквы."""
    return any(c in _KAZAKH_CHARS for c in text)


def _font_width(font: ImageFont.ImageFont, text: str) -> int:
    bb = font.getbbox(text)
    return bb[2] - bb[0]


@lru_cache(maxsize=1)
def _find_kaz_path() -> str | None:
    """Возвращает путь к первому доступному шрифту с поддержкой казахского."""
    for path in _KAZ_FALLBACK_PATHS:
        if os.path.exists(path):
            return path
    return None


@lru_cache(maxsize=1)
def load_fonts() -> dict:
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


def draw_mixed(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    main_font: ImageFont.ImageFont,
    kaz_font: ImageFont.ImageFont | None,
    fill: tuple,
) -> None:
    """
    Рисует текст посегментно: обычные символы — main_font (Gros-Ventre),
    казахские буквы — kaz_font (Segoe UI).
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


def mixed_width(
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


def fit_mixed(
    text: str,
    main_font: ImageFont.ImageFont,
    kaz_font: ImageFont.ImageFont | None,
    max_width: int = CONTENT_MAX_WIDTH,
) -> str:
    """Обрезает mixed-текст с '…', если превышает max_width."""
    if not text or mixed_width(text, main_font, kaz_font) <= max_width:
        return text
    while text:
        candidate = text + "…"
        if mixed_width(candidate, main_font, kaz_font) <= max_width:
            return candidate
        text = text[:-1]
    return "…"
