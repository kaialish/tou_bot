from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from src.keyboards import get_main_menu_keyboard
from src.utils import cleanup_previous_album

router = Router()


@router.callback_query(F.data == "menu_important_dates")
async def process_menu_important_dates(callback: CallbackQuery):
    """Заглушка раздела Академический статус / Важная информация."""
    await callback.answer("📌 Этот раздел находится в разработке!", show_alert=True)


@router.callback_query(F.data == "menu_grades")
async def process_menu_grades(callback: CallbackQuery):
    """Заглушка раздела Успеваемость."""
    await callback.answer("📊 Этот раздел находится в разработке!", show_alert=True)


@router.callback_query(F.data == "back_to_main_menu")
async def process_back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в Главное меню."""
    await cleanup_previous_album(callback.bot, callback.message.chat.id, state)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        "🏠 <b>Главное меню:</b>",
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard()
    )
