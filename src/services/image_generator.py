import io
from datetime import datetime, timedelta
from PIL import Image, ImageDraw

from src.services.image.fonts import draw_mixed, fit_mixed, load_fonts
from src.services.image.theme import (
    BG_DEFAULT,
    CONTENT_MAX_WIDTH,
    CONTENT_X1,
    CONTENT_X2,
    DAY_PALETTES,
    DIVIDER_COLOR,
    HEADER_START_Y,
    ROW_HEIGHT_LARGE,
    ROW_HEIGHT_SMALL,
    TEXT_MUTED,
    TEXT_WHITE,
    WEEKDAY_MAP,
    WEEKDAYS_RU,
    WM_DEFAULT,
    expand_lesson_type,
    get_weekday_date,
)


def _draw_toubot_watermark(canvas: Image.Image, canvas_height: int, wm_color: tuple) -> None:
    """Отрисовывает вертикальный водяной знак 'TOUBOT' вдоль левого края."""
    fonts = load_fonts()
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


def _render_card(
    schedule_data: list[dict],
    header_title: str = "Расписание",
    header_subtitle: str = "",
    day_key: str = "",
) -> bytes:
    """Рендерит карточку расписания. day_key определяет цвет фона."""
    fonts = load_fonts()
    f_bold = fonts["bold"]
    f_reg = fonts["reg"]
    f_light = fonts["light"]
    f_kaz = fonts["kaz"]

    bg_color, wm_color = DAY_PALETTES.get(day_key, (BG_DEFAULT, WM_DEFAULT))

    count = len(schedule_data)
    row_h = ROW_HEIGHT_LARGE if count >= 5 else ROW_HEIGHT_SMALL

    if count == 0:
        height = 440
    else:
        height = max(580, HEADER_START_Y + count * row_h + 44)

    image = Image.new("RGB", (724, height), bg_color)
    draw = ImageDraw.Draw(image)

    _draw_toubot_watermark(image, height, wm_color)
    draw.text((CONTENT_X1, 36), header_title, font=f_bold(46), fill=TEXT_WHITE)

    if header_subtitle:
        draw.text((CONTENT_X1, 84), header_subtitle, font=f_light(24), fill=TEXT_MUTED)

    draw.line([(CONTENT_X1, HEADER_START_Y), (CONTENT_X2, HEADER_START_Y)], fill=DIVIDER_COLOR, width=1)

    if count == 0:
        free_y = HEADER_START_Y + 64
        draw.text((CONTENT_X1, free_y), "Занятий нет", font=f_bold(30), fill=TEXT_WHITE)
        draw.text((CONTENT_X1, free_y + 46), "Свободный день!", font=f_light(20), fill=TEXT_MUTED)
    else:
        y = HEADER_START_Y
        for idx, item in enumerate(schedule_data, 1):
            time_display = item.get("time", "--:--").replace(":", ".")
            time_text = f"{idx}.  {time_display}"

            subject = item.get("subject", "Предмет не указан")
            lesson_type = expand_lesson_type(item.get("type", ""))
            room = item.get("room", "")
            teacher = item.get("teacher", "")

            draw.text((CONTENT_X1, y + 18), time_text, font=f_bold(26), fill=TEXT_WHITE)

            kaz16 = f_kaz(16)
            fit_subj = fit_mixed(subject, f_bold(16), kaz16, CONTENT_MAX_WIDTH)
            draw_mixed(draw, (CONTENT_X1, y + 58), fit_subj, f_bold(16), kaz16, TEXT_WHITE)

            if lesson_type:
                draw.text((CONTENT_X1, y + 84), lesson_type, font=f_reg(14), fill=TEXT_MUTED)

            if room:
                room_text = room if ("-" in room or len(room) <= 8) else f"Ауд. {room}"
                draw_mixed(draw, (CONTENT_X1, y + 108), room_text, f_reg(14), f_kaz(14), TEXT_MUTED)

            if teacher:
                kaz15 = f_kaz(15)
                fit_teacher = fit_mixed(teacher, f_bold(15), kaz15, CONTENT_MAX_WIDTH)
                draw_mixed(draw, (CONTENT_X1, y + 130), fit_teacher, f_bold(15), kaz15, TEXT_WHITE)

            y += row_h
            draw.line([(CONTENT_X1, y), (CONTENT_X2, y)], fill=DIVIDER_COLOR, width=1)

    return _to_bytes(image)


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
    day_key = day_name.lower()
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
    Возвращает список пар (отображаемое_имя_с_датой, png_bytes).
    """
    days_order: list[str] = []
    days_map: dict[str, list[dict]] = {}

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
        lessons = days_map[day_name]
        dt = get_weekday_date(day_name)
        date_str = dt.strftime("%d.%m.%Y") if dt else ""
        subtitle = f"{day_name}  {date_str}".strip()
        day_key = day_name.strip().lower()

        png = _render_card(
            schedule_data=lessons,
            header_title="Расписание",
            header_subtitle=subtitle,
            day_key=day_key,
        )
        display_name = f"{day_name} — {date_str}" if date_str else day_name
        result.append((display_name, png))

    return result
