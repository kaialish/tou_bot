from datetime import datetime
from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    CallbackQuery, BufferedInputFile, InputMediaPhoto,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext

from src.database import get_user_credentials, save_cached_schedule, get_cached_schedule
from src.services import (
    get_schedule_html, parse_schedule_items,
    generate_schedule_image, generate_week_album
)
from src.keyboards import get_schedule_keyboard
from src.utils import cleanup_previous_album

router = Router()


def _format_offline_header(is_offline: bool, cached_at: str) -> str:
    """Формирует предупреждающую плашку, если портал недоступен и показан кэш."""
    if is_offline and cached_at:
        return (
            "⚠️ <b>Портал ToU временно не отвечает</b>\n"
            f"Показано последнее сохранённое расписание (загружено: <b>{cached_at}</b>)\n\n"
        )
    return ""


@router.callback_query(F.data == "menu_schedule")
async def process_menu_schedule(callback: CallbackQuery, state: FSMContext):
    """Переход в раздел Расписание."""
    user_data = await state.get_data()
    cached_html = user_data.get("cached_html")
    is_offline = user_data.get("is_offline", False)
    cached_at = user_data.get("cached_at", "")

    if not cached_html:
        login = user_data.get("login")
        password = user_data.get("password")
        if not login or not password:
            saved_data = get_user_credentials(callback.from_user.id)
            if saved_data:
                login, password = saved_data
                await state.update_data(login=login, password=password)
            else:
                await callback.answer("Сессия истекла. Нажмите /start заново.", show_alert=True)
                return

        await callback.answer("🔄 Загружаем данные...")
        success, html_or_err = await get_schedule_html(login, password)
        if success:
            cached_html = html_or_err
            now_str = datetime.now().strftime("%d.%m.%Y в %H:%M")
            save_cached_schedule(callback.from_user.id, cached_html, now_str)
            is_offline = False
            cached_at = now_str
            await state.update_data(cached_html=cached_html, is_offline=is_offline, cached_at=cached_at)
        else:
            # Если сайт ToU лёг, пробуем достать сохранённое расписание из БД
            db_cached = get_cached_schedule(callback.from_user.id)
            if db_cached:
                cached_html, cached_at = db_cached
                is_offline = True
                await state.update_data(cached_html=cached_html, is_offline=is_offline, cached_at=cached_at)
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

    header = _format_offline_header(is_offline, cached_at)
    photo_msg = await callback.message.answer_photo(
        photo=photo,
        caption=f"{header}📅 <b>Раздел: Расписание</b>\nВыберите нужный день:",
        parse_mode="HTML",
        reply_markup=get_schedule_keyboard()
    )
    await state.update_data(schedule_photo_id=photo_msg.message_id)


@router.callback_query(F.data.startswith("schedule_") | F.data.startswith("sched_"))
async def process_schedule_day(callback: CallbackQuery, state: FSMContext):
    # Сразу отвечаем на callback_query, чтобы у пользователя моментально погас спиннер загрузки на кнопке
    await callback.answer()

    day = callback.data.split("_")[1]
    user_data = await state.get_data()
    login     = user_data.get("login")
    password  = user_data.get("password")
    cached_html = user_data.get("cached_html")
    is_offline = user_data.get("is_offline", False)
    cached_at = user_data.get("cached_at", "")

    if not login or not password:
        saved_data = get_user_credentials(callback.from_user.id)
        if saved_data:
            login, password = saved_data
            await state.update_data(login=login, password=password)
        else:
            await callback.message.answer("Сессия истекла. Нажмите /start заново.")
            return

    if not cached_html:
        success, html_or_err = await get_schedule_html(login, password)
        if success:
            cached_html = html_or_err
            now_str = datetime.now().strftime("%d.%m.%Y в %H:%M")
            save_cached_schedule(callback.from_user.id, cached_html, now_str)
            is_offline = False
            cached_at = now_str
            await state.update_data(cached_html=cached_html, is_offline=is_offline, cached_at=cached_at)
        else:
            # Проверяем локальный кэш
            db_cached = get_cached_schedule(callback.from_user.id)
            if db_cached:
                cached_html, cached_at = db_cached
                is_offline = True
                await state.update_data(cached_html=cached_html, is_offline=is_offline, cached_at=cached_at)
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
    header = _format_offline_header(is_offline, cached_at)

    # ────────────────────────────────────────────────────────────────────────────
    if day == "week":
        # Недельное расписание → альбом по дням
        # ────────────────────────────────────────────────────────────────────────────
        await cleanup_previous_album(callback.bot, callback.message.chat.id, state)
        try:
            await callback.message.delete()
        except Exception:
            pass

        day_images = generate_week_album(items)

        if not day_images:
            nav_msg = await callback.message.answer(
                f"{header}📅 <b>Недельное расписание</b>\n\nЗанятий на этой неделе нет.",
                parse_mode="HTML",
                reply_markup=get_schedule_keyboard()
            )
            await state.update_data(week_album_ids=[], week_nav_id=nav_msg.message_id)
            return

        if len(day_images) == 1:
            name, png = day_images[0]
            album_msg = await callback.message.answer_photo(
                photo=BufferedInputFile(png, filename="day_1.png"),
                caption=f"📅 <b>{name}</b>",
                parse_mode="HTML",
            )
            album_ids = [album_msg.message_id]
        else:
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

        nav_msg = await callback.message.answer(
            f"{header}📅 <b>Расписание на неделю</b> — пролистайте карточки по дням →",
            parse_mode="HTML",
            reply_markup=get_schedule_keyboard()
        )

        await state.update_data(week_album_ids=album_ids, week_nav_id=nav_msg.message_id)

    else:
        # ────────────────────────────────────────────────────────────────────────────
        # Сегодня / Завтра → одно фото
        # ────────────────────────────────────────────────────────────────────────────
        caption_text = f"{header}📅 <b>Раздел: Расписание</b>\nВыбрано: <b>{label}</b>"
        prev_album_ids: list[int] = user_data.get("week_album_ids", [])

        if prev_album_ids:
            await cleanup_previous_album(callback.bot, callback.message.chat.id, state)

            png_bytes = generate_schedule_image(items, title=f"Расписание на {label}", day_mode=day)
            photo = BufferedInputFile(png_bytes, filename="schedule.png")
            photo_msg = await callback.message.answer_photo(
                photo=photo,
                caption=caption_text,
                parse_mode="HTML",
                reply_markup=get_schedule_keyboard()
            )
            await state.update_data(schedule_photo_id=photo_msg.message_id)
        else:
            png_bytes = generate_schedule_image(items, title=f"Расписание на {label}", day_mode=day)
            photo = BufferedInputFile(png_bytes, filename="schedule.png")
            try:
                await callback.message.edit_media(
                    media=InputMediaPhoto(
                        media=photo,
                        caption=caption_text,
                        parse_mode="HTML",
                    ),
                    reply_markup=get_schedule_keyboard()
                )
            except TelegramBadRequest as e:
                if "message is not modified" not in str(e):
                    photo_msg = await callback.message.answer_photo(
                        photo=photo,
                        caption=caption_text,
                        parse_mode="HTML",
                        reply_markup=get_schedule_keyboard()
                    )
                    await state.update_data(schedule_photo_id=photo_msg.message_id)


@router.callback_query(F.data == "refresh_schedule")
async def process_refresh_schedule(callback: CallbackQuery, state: FSMContext):
    """Принудительное обновление расписания с портала ToU."""
    user_data = await state.get_data()
    login = user_data.get("login")
    password = user_data.get("password")

    if not login or not password:
        saved_data = get_user_credentials(callback.from_user.id)
        if saved_data:
            login, password = saved_data
            await state.update_data(login=login, password=password)
        else:
            await callback.answer("Сессия истекла. Нажмите /start заново.", show_alert=True)
            return

    await callback.answer("🔄 Проверяем портал ToU...")
    success, html_or_err = await get_schedule_html(login, password)

    if success:
        now_str = datetime.now().strftime("%d.%m.%Y в %H:%M")
        save_cached_schedule(callback.from_user.id, html_or_err, now_str)
        await state.update_data(cached_html=html_or_err, is_offline=False, cached_at=now_str)

        await cleanup_previous_album(callback.bot, callback.message.chat.id, state)
        items = parse_schedule_items(html_or_err, day="today")
        png_bytes = generate_schedule_image(items, title="Расписание на Сегодня", day_mode="today")
        photo = BufferedInputFile(png_bytes, filename="schedule.png")
        caption = (
            f"✅ <b>Расписание успешно обновлено с портала ToU!</b> ({now_str})\n\n"
            f"📅 <b>Раздел: Расписание</b>\nВыбрано: <b>Сегодня</b>"
        )
        try:
            await callback.message.edit_media(
                media=InputMediaPhoto(media=photo, caption=caption, parse_mode="HTML"),
                reply_markup=get_schedule_keyboard()
            )
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer_photo(
                photo=photo,
                caption=caption,
                parse_mode="HTML",
                reply_markup=get_schedule_keyboard()
            )
    else:
        # Портал всё ещё лежит
        db_cached = get_cached_schedule(callback.from_user.id)
        if db_cached:
            cached_html, cached_at = db_cached
            await state.update_data(cached_html=cached_html, is_offline=True, cached_at=cached_at)
            await callback.answer(
                f"⚠️ Портал ToU недоступен. Показано сохранённое расписание от {cached_at}.",
                show_alert=True
            )
        else:
            await callback.answer(
                "⚠️ Портал ToU временно недоступен и нет сохранённого расписания.",
                show_alert=True
            )
