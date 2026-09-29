from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    CallbackQuery, BufferedInputFile, InputMediaPhoto,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext

from src.services import (
    get_schedule_html, parse_schedule_items,
    generate_schedule_image, generate_week_album
)
from src.keyboards import get_schedule_keyboard
from src.utils import cleanup_previous_album

router = Router()


@router.callback_query(F.data == "menu_schedule")
async def process_menu_schedule(callback: CallbackQuery, state: FSMContext):
    """Переход в раздел Расписание."""
    user_data = await state.get_data()
    cached_html = user_data.get("cached_html")

    if not cached_html:
        login = user_data.get("login")
        password = user_data.get("password")
        if not login or not password:
            await callback.answer("Сессия истекла. Нажмите /start заново.", show_alert=True)
            return

        await callback.answer("🔄 Загружаем данные...")
        success, html_or_err = await get_schedule_html(login, password)
        if success:
            cached_html = html_or_err
            await state.update_data(cached_html=cached_html)
        else:
            retry_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Повторить попытку", callback_data="menu_schedule")],
                [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main_menu")]
            ])
            try:
                await callback.message.edit_text(html_or_err, parse_mode="HTML", reply_markup=retry_kb)
            except Exception:
                await callback.message.answer(html_or_err, parse_mode="HTML", reply_markup=retry_kb)
            return


    # Очищаем старый альбом (если остался)
    await cleanup_previous_album(callback.bot, callback.message.chat.id, state)

    # По умолчанию при входе в раздел показываем расписание на Сегодня
    items = parse_schedule_items(cached_html, day="today")
    png_bytes = generate_schedule_image(items, title="Расписание на Сегодня", day_mode="today")
    photo = BufferedInputFile(png_bytes, filename="schedule.png")

    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer_photo(
        photo=photo,
        caption="📅 <b>Раздел: Расписание</b>\nВыберите нужный день:",
        parse_mode="HTML",
        reply_markup=get_schedule_keyboard()
    )


@router.callback_query(F.data.startswith("sched_"))
async def process_schedule_day(callback: CallbackQuery, state: FSMContext):
    day = callback.data.split("_")[1]
    user_data = await state.get_data()
    login     = user_data.get("login")
    password  = user_data.get("password")
    cached_html = user_data.get("cached_html")

    if not login or not password:
        await callback.answer("Сессия истекла. Нажмите /start заново.", show_alert=True)
        return

    await callback.answer("🔄 Загружаем расписание...")

    if not cached_html:
        success, html_or_err = await get_schedule_html(login, password)
        if success:
            cached_html = html_or_err
            await state.update_data(cached_html=cached_html)
        else:
            retry_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Повторить попытку", callback_data=callback.data)],
                [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main_menu")]
            ])
            try:
                await callback.message.edit_text(html_or_err, parse_mode="HTML", reply_markup=retry_kb)
            except Exception:
                await callback.message.answer(html_or_err, parse_mode="HTML", reply_markup=retry_kb)
            return


    items = parse_schedule_items(cached_html, day=day)
    day_titles = {"today": "Сегодня", "tomorrow": "Завтра", "week": "Всю неделю"}
    label = day_titles.get(day, '')

    # ────────────────────────────────────────────────────────────────────────────
    if day == "week":
        # Недельное расписание → альбом (5 фото по дням)
        # ────────────────────────────────────────────────────────────────────────────
        # 1. Удаляем старое фото-сообщение или старый альбом
        await cleanup_previous_album(callback.bot, callback.message.chat.id, state)
        try:
            await callback.message.delete()
        except Exception:
            pass

        # 2. Генерируем PNG для каждого дня
        day_images = generate_week_album(items)

        if not day_images:
            nav_msg = await callback.message.answer(
                "📅 <b>Недельное расписание</b>\n\nЗанятий на этой неделе нет.",
                parse_mode="HTML",
                reply_markup=get_schedule_keyboard()
            )
            await state.update_data(week_album_ids=[], week_nav_id=nav_msg.message_id)
            return

        # 3. Отправляем альбом (media group от 1 до 10 фото)
        media_group = [
            InputMediaPhoto(
                media=BufferedInputFile(png, filename=f"day_{i+1}.png"),
                caption=f"📅 <b>{name}</b>",
                parse_mode="HTML",
            )
            for i, (name, png) in enumerate(day_images)
        ]
        album_msgs = await callback.message.answer_media_group(media=media_group)
        album_ids  = [m.message_id for m in album_msgs]

        # 4. Отправляем клавиатуру отдельным сообщением
        nav_msg = await callback.message.answer(
            "📅 <b>Расписание на неделю</b> — пролистайте карточки по дням →",
            parse_mode="HTML",
            reply_markup=get_schedule_keyboard()
        )
        # 5. Сохраняем ID для последующей чистки
        await state.update_data(week_album_ids=album_ids, week_nav_id=nav_msg.message_id)

    else:
        # ────────────────────────────────────────────────────────────────────────────
        # Сегодня / Завтра → одно фото
        # ────────────────────────────────────────────────────────────────────────────
        # 1. Если предыдущий режим был альбомным — чистим его
        prev_album_ids: list[int] = user_data.get("week_album_ids", [])
        if prev_album_ids:
            await cleanup_previous_album(callback.bot, callback.message.chat.id, state)

            # Отправляем новое фото-сообщение
            png_bytes = generate_schedule_image(items, title=f"Расписание на {label}", day_mode=day)
            photo = BufferedInputFile(png_bytes, filename="schedule.png")
            await callback.message.answer_photo(
                photo=photo,
                caption=f"📅 <b>Раздел: Расписание</b>\nВыбрано: <b>{label}</b>",
                parse_mode="HTML",
                reply_markup=get_schedule_keyboard()
            )
        else:
            # 2. Обычное переключение today ↔ tomorrow — редактируем фото
            png_bytes = generate_schedule_image(items, title=f"Расписание на {label}", day_mode=day)
            photo = BufferedInputFile(png_bytes, filename="schedule.png")
            try:
                await callback.message.edit_media(
                    media=InputMediaPhoto(
                        media=photo,
                        caption=f"📅 <b>Раздел: Расписание</b>\nВыбрано: <b>{label}</b>",
                        parse_mode="HTML",
                    ),
                    reply_markup=get_schedule_keyboard()
                )
            except TelegramBadRequest as e:
                if "message is not modified" not in str(e):
                    await callback.message.answer_photo(
                        photo=photo,
                        caption=f"📅 <b>Раздел: Расписание</b>\nВыбрано: <b>{label}</b>",
                        parse_mode="HTML",
                        reply_markup=get_schedule_keyboard()
                    )
