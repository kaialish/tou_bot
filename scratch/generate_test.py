import os
from PIL import Image, ImageDraw, ImageFont

font_dir = r"assets/fonts/gros-ventre"
f_bold = lambda sz: ImageFont.truetype(os.path.join(font_dir, "Gros-Ventre-Bold.ttf"), sz)
f_semi = lambda sz: ImageFont.truetype(os.path.join(font_dir, "Gros-Ventre-Semibold.ttf"), sz)
f_reg  = lambda sz: ImageFont.truetype(os.path.join(font_dir, "Gros-Ventre-Regular.ttf"), sz)
f_light = lambda sz: ImageFont.truetype(os.path.join(font_dir, "Gros-Ventre-Light.ttf"), sz)

sample_lessons = [
    {
        "number": 1,
        "time": "08.15-09.05",
        "subject": "Объектно-ориентированное программирование (Java)",
        "type": "Практика",
        "room": "А-531",
        "teacher": "Егинбаев Мирас Тлекович"
    },
    {
        "number": 2,
        "time": "09.15-10.05",
        "subject": "История Казахстана (ГЭ)",
        "type": "Лекция",
        "room": "А-2",
        "teacher": "Шабамбаева Анара Габдулбариевна"
    },
    {
        "number": 3,
        "time": "10.15-11.05",
        "subject": "Научные исследования в IT",
        "type": "Практика",
        "room": "А-409",
        "teacher": "Исимбаева Ассель Базарбаевна"
    },
    {
        "number": 4,
        "time": "11.15-12.05",
        "subject": "Научные исследования в IT",
        "type": "Практика",
        "room": "А-409",
        "teacher": "Исимбаева Ассель Базарбаевна"
    },
    {
        "number": 5,
        "time": "12.35-13.25",
        "subject": "Разработка ИИ-систем",
        "type": "Лекция",
        "room": "А-409",
        "teacher": "Улихина Юлия Викторовна"
    },
    {
        "number": 6,
        "time": "13.35-14.25",
        "subject": "Объектно-ориентированное программирование (Java)",
        "type": "Практика",
        "room": "А-531",
        "teacher": "Егинбаев Мирас Тлекович"
    }
]

BG_COLOR = (1, 35, 38)
DIVIDER_COLOR = (245, 250, 250)
WM_COLOR = (32, 66, 68)

width = 724
start_y = 112
row_h = 149
height = 1024

img = Image.new("RGB", (width, height), BG_COLOR)
draw = ImageDraw.Draw(img)

# Watermark TOUBOT
wm_font = f_bold(145)
wm_txt = "TOUBOT"
bbox = wm_font.getbbox(wm_txt)
wm_w = bbox[2] - bbox[0] + 30
wm_h = bbox[3] - bbox[1] + 40
wm_img = Image.new("RGBA", (wm_w, wm_h), (0, 0, 0, 0))
wm_draw = ImageDraw.Draw(wm_img)
wm_draw.text((10, 10), wm_txt, font=wm_font, fill=WM_COLOR + (255,))
rotated_wm = wm_img.rotate(270, expand=True)

# Paste watermark on the left (crop if taller than canvas)
if rotated_wm.height > height:
    rotated_wm = rotated_wm.crop((0, 0, rotated_wm.width, height))
img.paste(rotated_wm, (-15, 50), rotated_wm)

# Draw header
draw.text((174, 38), "Расписание", font=f_bold(42), fill=(255, 255, 255))
draw.text((174, 82), "Понедельник 28.09.2026", font=f_light(22), fill=(240, 245, 245))

# Header divider
draw.line([(174, start_y), (626, start_y)], fill=DIVIDER_COLOR, width=1)

y = start_y
for item in sample_lessons:
    # 1. Number & Time
    time_text = f"{item['number']}. {item['time']}"
    draw.text((174, y + 14), time_text, font=f_bold(22), fill=(255, 255, 255))

    # 2. Subject
    draw.text((174, y + 46), item["subject"], font=f_bold(13), fill=(255, 255, 255))

    # 3. Type
    draw.text((174, y + 66), item["type"], font=f_reg(13), fill=(210, 230, 230))

    # 4. Room
    draw.text((174, y + 96), item["room"], font=f_reg(13), fill=(210, 230, 230))

    # 5. Teacher
    draw.text((174, y + 114), item["teacher"], font=f_bold(13), fill=(255, 255, 255))

    y += row_h
    # Divider line
    if y <= height - 50:
        draw.line([(174, y), (626, y)], fill=DIVIDER_COLOR, width=1)

os.makedirs("scratch", exist_ok=True)
img.save("scratch/test_full.png")
print("Full test saved successfully to scratch/test_full.png!")
