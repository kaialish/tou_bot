from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from src.keyboards import get_main_menu_keyboard, get_notifications_menu_keyboard
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