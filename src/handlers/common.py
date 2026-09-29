from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from src.services import get_schedule_html, parse_key_dates, format_key_dates_message
from src.keyboards import get_main_menu_keyboard
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
            await callback.message.answer("❌ Не удалось обновить данные с сайта ToU.")
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