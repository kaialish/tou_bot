from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from src.keyboards import get_main_menu_keyboard

router = Router()


@router.callback_query(F.data == "menu_important_dates")
async def process_menu_important_dates(callback: CallbackQuery):
    """Заглушка раздела Важная информация."""
    await callback.answer("📌 Этот раздел находится в разработке!", show_alert=True)


@router.callback_query(F.data == "menu_grades")
async def process_menu_grades(callback: CallbackQuery):
    """Заглушка раздела Успеваемость."""
    await callback.answer("📊 Этот раздел находится в разработке!", show_alert=True)


@router.callback_query(F.data == "back_to_main_menu")
async def process_back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в Главное меню."""
    await callback.message.delete()
    await callback.message.answer(
        "🏠 **Главное меню**: ",
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard()
    )
