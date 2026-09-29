from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from src.services import get_schedule_html, parse_key_dates, format_key_dates_message
from src.keyboards import get_main_menu_keyboard, get_notifications_menu_keyboard
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
        success, html_or_err = await get_schedule_html(login, password)
        if success:
            cached_html = html_or_err
            await state.update_data(cached_html=cached_html)
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
    """Возврат в Главное меню."""
    await cleanup_previous_album(callback.bot, callback.message.chat.id, state)
    
    kb = get_main_menu_keyboard()
    try:
        await callback.message.edit_text("🏠 <b>Главное меню</b>\nВыберите нужный раздел:", parse_mode="HTML", reply_markup=kb)
    except Exception:
        await callback.message.answer("🏠 <b>Главное меню</b>\nВыберите нужный раздел:", parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data == "subscribe_notifications")
async def process_subscribe_notifications(callback: CallbackQuery):
    """Подписать пользователя на уведомления об окончании пар."""
    from src.database import subscribe_to_notifications

    user_id = callback.from_user.id
    success = subscribe_to_notifications(user_id)

    if success:
        await callback.answer("✅ Вы подписаны на уведомления об окончании пар!", show_alert=False)
    else:
        await callback.answer("❌ Ошибка при подписке. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data == "unsubscribe_notifications")
async def process_unsubscribe_notifications(callback: CallbackQuery):
    """Отписать пользователя от уведомлений об окончании пар."""
    from src.database import unsubscribe_from_notifications

    user_id = callback.from_user.id
    success = unsubscribe_from_notifications(user_id)

    if success:
        await callback.answer("👋 Вы отписаны от уведомлений об окончании пар.", show_alert=False)
    else:
        await callback.answer("❌ Ошибка при отписке. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data == "menu_notifications")
async def process_menu_notifications(callback: CallbackQuery):
    """Открыть меню управления уведомлениями об окончании пар."""
    from src.database import is_user_subscribed

    user_id = callback.from_user.id
    is_subscribed = is_user_subscribed(user_id)

    status = "✅ Вы подписаны на уведомления об окончании пар" if is_subscribed else "❌ Вы отписаны от уведомлений"

    text = (
        "🔔 <b>Управление уведомлениями</b>\n\n"
        f"Статус: {status}\n\n"
        "Вы будете получать уведомления за 5 минут до окончания каждой пары "
        "(пн-пт) с информацией о длительности перемены."
    )

    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_notifications_menu_keyboard()
        )
    except Exception:
        await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=get_notifications_menu_keyboard()
        )