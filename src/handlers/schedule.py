from datetime import datetime
from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    CallbackQuery, BufferedInputFile, InputMediaPhoto,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext

from src.database import (
    get_user_credentials,
    save_cached_schedule,
    get_cached_schedule,
    get_user_schedule_format,
    toggle_user_schedule_format,
)
from src.services import (
    get_schedule_html,
    parse_schedule_items,
    generate_schedule_image,
    generate_week_album,
    format_schedule_text,
)
from src.keyboards import get_schedule_keyboard
from src.utils import cleanup_previous_album

router = Router()


def _format_offline_header(is_offline: bool, cached_at: str) -> str:
    """Формирует предупреждающую плашку, если портал недоступен и показан кэш."""
    if is_offline and cached_at:
        return (
            "⚠️ <b>Портал ToU временно не отвечает</b>\n"
            f"Показано сохранённое расписание (от: <b>{cached_at}</b>)\n\n"
        )
    return ""


async def _ensure_cached_schedule(callback: CallbackQuery, state: FSMContext) -> tuple[str | None, bool, str]:
    """
    Проверяет наличие расписания в FSM или БД. Если нет — загружает с портала ToU.
    Возвращает (html_content, is_offline, cached_at) или (None, False, "").
    """
    user_data = await state.get_data()
    cached_html = user_data.get("cached_html")
    is_offline = user_data.get("is_offline", False)
    cached_at = user_data.get("cached_at", "")

    if cached_html:
        return cached_html, is_offline, cached_at

    login = user_data.get("login")
    password = user_data.get("password")
    if not login or not password:
        saved_data = await get_user_credentials(callback.from_user.id)
        if saved_data:
            login, password = saved_data
            await state.update_data(login=login, password=password)
        else:
            await callback.answer("Сессия истекла. Нажмите /start заново.", show_alert=True)
            return None, False, ""

    await callback.answer("🔄 Загружаем данные...")
    success, html_or_err = await get_schedule_html(login, password, bot=callback.bot)
    if success:
        cached_html = html_or_err
        now_str = datetime.now().strftime("%d.%m.%Y в %H:%M")
        await save_cached_schedule(callback.from_user.id, cached_html, now_str)
        is_offline = False
        cached_at = now_str
        await state.update_data(cached_html=cached_html, is_offline=is_offline, cached_at=cached_at)
        return cached_html, is_offline, cached_at
    else:
        # Проверяем кэш БД
        db_cached = await get_cached_schedule(callback.from_user.id)
        if db_cached:
            cached_html, cached_at = db_cached
            is_offline = True
            await state.update_data(cached_html=cached_html, is_offline=is_offline, cached_at=cached_at)
            return cached_html, is_offline, cached_at
        else:
            retry_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Повторить попытку", callback_data="menu_schedule")],
                [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main_menu")]
            ])
            try:
                await callback.message.edit_text(html_or_err, parse_mode="HTML", reply_markup=retry_kb)
            except Exception:
                await callback.message.answer(html_or_err, parse_mode="HTML", reply_markup=retry_kb)
            return None, False, ""


async def _render_schedule(
    callback: CallbackQuery,
    state: FSMContext,
    day: str,
    cached_html: str,
    is_offline: bool,
    cached_at: str,
    fmt: str,
    force_new_message: bool = False
) -> None:
    """Рендерит и отправляет расписание в выбранном формате (текст или картинка)."""
    items = parse_schedule_items(cached_html, day=day)
    day_titles = {"today": "Сегодня", "tomorrow": "Завтра", "week": "Всю неделю"}
    label = day_titles.get(day, "Сегодня")
    header = _format_offline_header(is_offline, cached_at)
    keyboard = get_schedule_keyboard(current_format=fmt)

    await cleanup_previous_album(callback.bot, callback.message.chat.id, state)
    await state.update_data(current_schedule_day=day)

    # ────────────────────────────────────────────────────────────────────────────
    # ТЕКСТОВЫЙ РЕЖИМ (TEXT MODE) - молниеносная скорость
    # ────────────────────────────────────────────────────────────────────────────
    if fmt == "text":
        title_map = {"today": "Сегодня", "tomorrow": "Завтра", "week": "Всю неделю"}
        title_text = f"Расписание на {title_map.get(day, 'Сегодня')}"
        text_content = format_schedule_text(items, title=title_text, day_mode=day)
        full_text = f"{header}{text_content}"

        if force_new_message:
            try:
                await callback.message.delete()
            except Exception:
                pass
            sent_msg = await callback.message.answer(
                full_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            await state.update_data(schedule_text_id=sent_msg.message_id)
        else:
            try:
                await callback.message.edit_text(
                    full_text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            except TelegramBadRequest as e:
                if "message is not modified" not in str(e):
                    try:
                        await callback.message.delete()
                    except Exception:
                        pass
                    sent_msg = await callback.message.answer(
                        full_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                    await state.update_data(schedule_text_id=sent_msg.message_id)
            except Exception:
                try:
                    await callback.message.delete()
                except Exception:
                    pass
                sent_msg = await callback.message.answer(
                    full_text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                await state.update_data(schedule_text_id=sent_msg.message_id)

    # ────────────────────────────────────────────────────────────────────────────
    # ГРАФИЧЕСКИЙ РЕЖИМ (PHOTO MODE)
    # ────────────────────────────────────────────────────────────────────────────
    else:
        if day == "week":
            try:
                await callback.message.delete()
            except Exception:
                pass

            day_images = generate_week_album(items)
            if not day_images:
                nav_msg = await callback.message.answer(
                    f"{header}📅 <b>Недельное расписание</b>\n\nЗанятий на этой неделе нет.",
                    parse_mode="HTML",
                    reply_markup=keyboard
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
                album_ids = [m.message_id for m in album_msgs]

            nav_msg = await callback.message.answer(
                f"{header}📅 <b>Расписание на неделю</b> — пролистайте карточки по дням →",
                parse_mode="HTML",
                reply_markup=keyboard
            )
            await state.update_data(week_album_ids=album_ids, week_nav_id=nav_msg.message_id)

        else:
            caption_text = f"{header}📅 <b>Раздел: Расписание</b>\nВыбрано: <b>{label}</b>"
            png_bytes = generate_schedule_image(items, title=f"Расписание на {label}", day_mode=day)
            photo = BufferedInputFile(png_bytes, filename="schedule.png")

            if force_new_message:
                try:
                    await callback.message.delete()
                except Exception:
                    pass
                photo_msg = await callback.message.answer_photo(
                    photo=photo,
                    caption=caption_text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                await state.update_data(schedule_photo_id=photo_msg.message_id)
            else:
                try:
                    await callback.message.edit_media(
                        media=InputMediaPhoto(media=photo, caption=caption_text, parse_mode="HTML"),
                        reply_markup=keyboard
                    )
                except TelegramBadRequest as e:
                    if "message is not modified" not in str(e):
                        try:
                            await callback.message.delete()
                        except Exception:
                            pass
                        photo_msg = await callback.message.answer_photo(
                            photo=photo,
                            caption=caption_text,
                            parse_mode="HTML",
                            reply_markup=keyboard
                        )
                        await state.update_data(schedule_photo_id=photo_msg.message_id)
                except Exception:
                    try:
                        await callback.message.delete()
                    except Exception:
                        pass
                    photo_msg = await callback.message.answer_photo(
                        photo=photo,
                        caption=caption_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                    await state.update_data(schedule_photo_id=photo_msg.message_id)


@router.callback_query(F.data == "menu_schedule")
async def process_menu_schedule(callback: CallbackQuery, state: FSMContext):
    """Переход в раздел Расписание."""
    cached_html, is_offline, cached_at = await _ensure_cached_schedule(callback, state)
    if not cached_html:
        return

    fmt = await get_user_schedule_format(callback.from_user.id)
    await _render_schedule(
        callback, state,
        day="today",
        cached_html=cached_html,
        is_offline=is_offline,
        cached_at=cached_at,
        fmt=fmt,
        force_new_message=True
    )


@router.callback_query(F.data.startswith("schedule_") | F.data.startswith("sched_"))
async def process_schedule_day(callback: CallbackQuery, state: FSMContext):
    """Выбор дня расписания (Сегодня, Завтра, Вся неделя)."""
    await callback.answer()
    day = callback.data.split("_")[1]

    cached_html, is_offline, cached_at = await _ensure_cached_schedule(callback, state)
    if not cached_html:
        return

    fmt = await get_user_schedule_format(callback.from_user.id)
    await _render_schedule(
        callback, state,
        day=day,
        cached_html=cached_html,
        is_offline=is_offline,
        cached_at=cached_at,
        fmt=fmt,
        force_new_message=False
    )


@router.callback_query(F.data == "toggle_schedule_format")
async def process_toggle_schedule_format(callback: CallbackQuery, state: FSMContext):
    """Быстрое переключение формата расписания (Текст <-> Картинка)."""
    user_id = callback.from_user.id
    new_format = await toggle_user_schedule_format(user_id)

    mode_label = "📝 Текстовый" if new_format == "text" else "🖼️ Картинки (PNG)"
    await callback.answer(f"Формат изменён: {mode_label}", show_alert=False)

    user_data = await state.get_data()
    day = user_data.get("current_schedule_day", "today")

    cached_html, is_offline, cached_at = await _ensure_cached_schedule(callback, state)
    if not cached_html:
        return

    await _render_schedule(
        callback, state,
        day=day,
        cached_html=cached_html,
        is_offline=is_offline,
        cached_at=cached_at,
        fmt=new_format,
        force_new_message=True
    )


@router.callback_query(F.data == "refresh_schedule")
async def process_refresh_schedule(callback: CallbackQuery, state: FSMContext):
    """Принудительное обновление расписания с портала ToU."""
    user_data = await state.get_data()
    login = user_data.get("login")
    password = user_data.get("password")

    if not login or not password:
        saved_data = await get_user_credentials(callback.from_user.id)
        if saved_data:
            login, password = saved_data
            await state.update_data(login=login, password=password)
        else:
            await callback.answer("Сессия истекла. Нажмите /start заново.", show_alert=True)
            return

    await callback.answer("🔄 Проверяем портал ToU...")
    success, html_or_err = await get_schedule_html(login, password, bot=callback.bot)

    if success:
        now_str = datetime.now().strftime("%d.%m.%Y в %H:%M")
        await save_cached_schedule(callback.from_user.id, html_or_err, now_str)
        await state.update_data(cached_html=html_or_err, is_offline=False, cached_at=now_str)

        fmt = await get_user_schedule_format(callback.from_user.id)
        current_day = user_data.get("current_schedule_day", "today")

        await _render_schedule(
            callback, state,
            day=current_day,
            cached_html=html_or_err,
            is_offline=False,
            cached_at=now_str,
            fmt=fmt,
            force_new_message=True
        )
    else:
        # Портал всё ещё лежит
        db_cached = await get_cached_schedule(callback.from_user.id)
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
