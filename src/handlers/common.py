from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from src.database import (
    get_cached_schedule,
    save_cached_schedule,
    subscribe_to_notifications,
    unsubscribe_from_notifications,
    is_user_subscribed,
    get_user_schedule_format,
    toggle_user_schedule_format,
)
from src.services import get_schedule_html, parse_key_dates, format_key_dates_message
from src.keyboards import (
    get_main_menu_keyboard,
    get_notifications_menu_keyboard,
    get_settings_keyboard,
)
from src.utils import cleanup_previous_album

router = Router()


@router.callback_query(F.data == "menu_key_dates")
async def process_menu_key_dates(callback: CallbackQuery, state: FSMContext):
    """Раздел: Ключевые даты."""
    user_data = await state.get_data()
    cached_html = user_data.get("cached_html")

    if not cached_html:
        login = user_data.get("login")
        password = user_data.get("password")
        if not login or not password:
            await callback.answer("Сессия истекла. Нажмите /start заново.", show_alert=True)
            return

        await callback.answer("🔄 Загружаем данные...")
        success, html_or_err = await get_schedule_html(login, password, bot=callback.bot)
        if success:
            cached_html = html_or_err
            now_str = datetime.now().strftime("%d.%m.%Y в %H:%M")
            await save_cached_schedule(callback.from_user.id, cached_html, now_str)
            await state.update_data(cached_html=cached_html, is_offline=False, cached_at=now_str)
        else:
            db_cached = await get_cached_schedule(callback.from_user.id)
            if db_cached:
                cached_html, cached_at = db_cached
                await state.update_data(cached_html=cached_html, is_offline=True, cached_at=cached_at)
            else:
                retry_kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Повторить попытку", callback_data="menu_key_dates")],
                    [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main_menu")]
                ])
                try:
                    await callback.message.edit_text(html_or_err, parse_mode="HTML", reply_markup=retry_kb)
                except Exception:
                    await callback.message.answer(html_or_err, parse_mode="HTML", reply_markup=retry_kb)
                return

    await cleanup_previous_album(callback.bot, callback.message.chat.id, state)

    dates = parse_key_dates(cached_html)
    text = format_key_dates_message(dates)

    back_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main_menu")]
        ]
    )

    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb)
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=back_kb)


@router.callback_query(F.data == "menu_academic_status")
async def process_menu_academic_status(callback: CallbackQuery):
    """Раздел: Академический статус."""
    await callback.answer("📌 Раздел 'Академический статус' находится в разработке!", show_alert=True)


@router.callback_query(F.data == "menu_grades")
async def process_menu_grades(callback: CallbackQuery):
    """Раздел: Успеваемость."""
    await callback.answer("📊 Раздел 'Успеваемость' находится в разработке!", show_alert=True)


@router.callback_query(F.data == "back_to_main_menu")
async def process_back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в Главное меню. Удаляет все сообщения расписания перед показом меню."""
    await cleanup_previous_album(callback.bot, callback.message.chat.id, state)

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        "🏠 <b>Главное меню</b>\nВыберите нужный раздел:",
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard()
    )


# ────────────────────────────────────────────────────────────────────────────
# Раздел: Настройки и вид расписания
# ────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu_settings")
async def process_menu_settings(callback: CallbackQuery):
    """Раздел персональных настроек пользователя."""
    user_id = callback.from_user.id
    current_format = await get_user_schedule_format(user_id)
    is_sub = await is_user_subscribed(user_id)

    format_desc = "🖼️ <b>Картинка (PNG)</b>" if current_format == "photo" else "📝 <b>Текст (быстрый режим)</b>"
    notify_desc = "✅ <b>Включены</b>" if is_sub else "❌ <b>Отключены</b>"

    text = (
        "⚙️ <b>Настройки бота</b>\n\n"
        f"🎨 <b>Вид расписания:</b> {format_desc}\n"
        "<i>Текстовый режим загружается мгновенно и экономит интернет, а картинка оформлена графическими карточками.</i>\n\n"
        f"🔔 <b>Уведомления об окончании пар:</b> {notify_desc}\n\n"
        "Нажмите на кнопку ниже, чтобы переключить параметр:"
    )

    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_settings_keyboard(current_format, is_sub)
        )
    except Exception:
        await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=get_settings_keyboard(current_format, is_sub)
        )


@router.callback_query(F.data == "settings_toggle_format")
async def process_settings_toggle_format(callback: CallbackQuery):
    """Переключение вида расписания из меню настроек."""
    user_id = callback.from_user.id
    new_format = await toggle_user_schedule_format(user_id)
    is_sub = await is_user_subscribed(user_id)

    mode_name = "📝 Текстовый вид" if new_format == "text" else "🖼️ Картинка (PNG)"
    await callback.answer(f"Вид изменен на: {mode_name}", show_alert=False)

    format_desc = "🖼️ <b>Картинка (PNG)</b>" if new_format == "photo" else "📝 <b>Текст (быстрый режим)</b>"
    notify_desc = "✅ <b>Включены</b>" if is_sub else "❌ <b>Отключены</b>"

    text = (
        "⚙️ <b>Настройки бота</b>\n\n"
        f"🎨 <b>Вид расписания:</b> {format_desc}\n"
        "<i>Текстовый режим загружается мгновенно и экономит интернет, а картинка оформлена графическими карточками.</i>\n\n"
        f"🔔 <b>Уведомления об окончании пар:</b> {notify_desc}\n\n"
        "Нажмите на кнопку ниже, чтобы переключить параметр:"
    )

    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_settings_keyboard(new_format, is_sub)
        )
    except Exception:
        pass


@router.callback_query(F.data == "settings_toggle_notifications")
async def process_settings_toggle_notifications(callback: CallbackQuery):
    """Переключение уведомлений из меню настроек."""
    user_id = callback.from_user.id
    is_sub = await is_user_subscribed(user_id)

    if is_sub:
        await unsubscribe_from_notifications(user_id)
        new_sub = False
        await callback.answer("🔕 Уведомления выключены", show_alert=False)
    else:
        await subscribe_to_notifications(user_id)
        new_sub = True
        await callback.answer("🔔 Уведомления включены", show_alert=False)

    current_format = await get_user_schedule_format(user_id)
    format_desc = "🖼️ <b>Картинка (PNG)</b>" if current_format == "photo" else "📝 <b>Текст (быстрый режим)</b>"
    notify_desc = "✅ <b>Включены</b>" if new_sub else "❌ <b>Отключены</b>"

    text = (
        "⚙️ <b>Настройки бота</b>\n\n"
        f"🎨 <b>Вид расписания:</b> {format_desc}\n"
        "<i>Текстовый режим загружается мгновенно и экономит интернет, а картинка оформлена графическими карточками.</i>\n\n"
        f"🔔 <b>Уведомления об окончании пар:</b> {notify_desc}\n\n"
        "Нажмите на кнопку ниже, чтобы переключить параметр:"
    )

    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_settings_keyboard(current_format, new_sub)
        )
    except Exception:
        pass


# ────────────────────────────────────────────────────────────────────────────
# Раздел: Уведомления
# ────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "subscribe_notifications")
async def process_subscribe_notifications(callback: CallbackQuery):
    """Подписать пользователя на уведомления об окончании пар."""
    user_id = callback.from_user.id
    success = await subscribe_to_notifications(user_id)

    if success:
        await callback.answer("✅ Вы подписаны на уведомления об окончании пар!", show_alert=False)
    else:
        await callback.answer("❌ Ошибка при подписке. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data == "unsubscribe_notifications")
async def process_unsubscribe_notifications(callback: CallbackQuery):
    """Отписать пользователя от уведомлений об окончании пар."""
    user_id = callback.from_user.id
    success = await unsubscribe_from_notifications(user_id)

    if success:
        await callback.answer("👋 Вы отписаны от уведомлений об окончании пар.", show_alert=False)
    else:
        await callback.answer("❌ Ошибка при отписке. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data == "menu_notifications")
async def process_menu_notifications(callback: CallbackQuery):
    """Перенаправление старого вызова уведомлений в объединённый раздел настроек."""
    await process_menu_settings(callback)