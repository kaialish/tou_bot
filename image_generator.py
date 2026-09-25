from PIL import Image, ImageDraw, ImageFont
import io

def generate_schedule_image(schedule_data: list[dict], title: str = "Расписание занятий") -> bytes:
    width = 650
    row_height = 85
    header_height = 90
    padding = 20
    
    height = header_height + (len(schedule_data) * row_height) + padding
    if not schedule_data:
        height = 180

    image = Image.new("RGB", (width, height), color=(248, 249, 250))
    draw = ImageDraw.Draw(image)

    try:
        font_title = ImageFont.truetype("arial.ttf", 22)
        font_main = ImageFont.truetype("arial.ttf", 16)
        font_sub = ImageFont.truetype("arial.ttf", 13)
    except IOError:
        font_title = font_main = font_sub = ImageFont.load_default()

    # Шапка карточки
    draw.rectangle([0, 0, width, 65], fill=(28, 54, 87))
    draw.text((padding, 18), title, fill=(255, 255, 255), font=font_title)

    if not schedule_data:
        draw.text((padding, 100), "🎉 На этот день пар нет!", fill=(100, 100, 100), font=font_main)
    else:
        y = header_height
        for item in schedule_data:
            draw.rectangle([padding, y, width - padding, y + row_height - 12], fill=(255, 255, 255), outline=(220, 224, 230))
            draw.text((padding + 15, y + 14), item.get("time", "--:--"), fill=(28, 54, 87), font=font_main)
            
            subject = item.get("subject", "Предмет не указан")
            draw.text((padding + 150, y + 14), subject[:40], fill=(30, 30, 30), font=font_main)
            
            info = f"{item.get('type', '')}  |  Аудитория: {item.get('room', 'Н/Д')}"
            draw.text((padding + 150, y + 42), info, fill=(110, 110, 110), font=font_sub)
            
            y += row_height

    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    return img_byte_arr.getvalue()