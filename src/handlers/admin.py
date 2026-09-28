import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from src.config import ADMIN_IDS
from src.database import get_users_stats, get_all_user_ids
from src.keyboards import get_admin_keyboard
from src.states import AdminState

router = Router()


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return

    await message.answer("🛠️ <b>Панель Администратора</b>", parse_mode="HTML", reply_markup=get_admin_keyboard())


@router.callback_query(F.data == "admin_stats")
async def process_admin_stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return

    count, logins = get_users_stats()
    logins_str = "\n".join([f"• <code>{login}</code>" for login in logins[:20]]) or "Нет зарегистрированных пользователей"

    text = (
        f"📊 <b>Статистика бота:</b>\n\n"
        f"👤 Всего пользователей: <b>{count}</b>\n\n"
        f"📋 Последние авторизованные логины:\n{logins_str}"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_keyboard())


@router.callback_query(F.data == "admin_broadcast")
async def process_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return

    await callback.message.edit_text("💬 Отправьте сообщение (текст/фото), которое вы хотите разослать всем пользователям:")
    await state.set_state(AdminState.waiting_for_broadcast_msg)


@router.message(AdminState.waiting_for_broadcast_msg)
async def process_broadcast_send(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return

    user_ids = get_all_user_ids()
    await message.answer(f"🚀 Начинаем рассылку для {len(user_ids)} пользователей...")

    success_count = 0
    fail_count = 0

    for u_id in user_ids:
        try:
            await message.copy_to(chat_id=u_id)
            success_count += 1
            await asyncio.sleep(0.05)
        except Exception:
            fail_count += 1

    await message.answer(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"Успешно доставлено: <b>{success_count}</b>\n"
        f"Ошибок отправки (заблокировали бота): <b>{fail_count}</b>",
        parse_mode="HTML"
    )
    await state.clear()
