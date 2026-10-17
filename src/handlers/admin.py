import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from src.config import ADMIN_IDS
from src.database import get_users_stats, get_all_user_ids
from src.keyboards import get_admin_keyboard
from src.states import AdminState

router = Router()


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return

    # Удаляем входящую команду /admin
    try:
        await message.delete()
    except Exception:
        pass

    # Удаляем предыдущее сообщение Главного меню, если оно было
    data = await state.get_data()
    main_menu_msg_id = data.get("main_menu_msg_id")
    if main_menu_msg_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=main_menu_msg_id)
        except Exception:
            pass
    else:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id - 1)
        except Exception:
            pass

    await state.clear()
    admin_msg = await message.answer("🛠️ <b>Панель Администратора</b>", parse_mode="HTML", reply_markup=get_admin_keyboard())
    await state.update_data(admin_panel_msg_id=admin_msg.message_id)


@router.callback_query(F.data == "admin_stats")
async def process_admin_stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return

    await callback.answer()
    count, logins = await get_users_stats()
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

    await callback.answer()
    cancel_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data="admin_panel")]
        ]
    )
    await callback.message.edit_text(
        "💬 Отправьте сообщение (текст/фото), которое вы хотите разослать всем пользователям:",
        reply_markup=cancel_kb
    )
    await state.set_state(AdminState.waiting_for_broadcast_msg)


@router.callback_query(F.data == "admin_panel")
async def process_admin_panel(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return

    await callback.answer()
    await state.clear()

    chat_id = callback.message.chat.id if callback.message else callback.from_user.id

    # Удаляем текущее Главное меню перед показом админ-панели
    deleted = False
    if callback.message:
        try:
            await callback.bot.delete_message(
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id
            )
            deleted = True
        except Exception:
            try:
                await callback.message.delete()
                deleted = True
            except Exception:
                pass

    if not deleted and callback.message:
        try:
            await callback.message.edit_text(
                "🛠️ <b>Панель Администратора</b>",
                parse_mode="HTML",
                reply_markup=get_admin_keyboard()
            )
            await state.update_data(admin_panel_msg_id=callback.message.message_id)
            return
        except Exception:
            pass

    admin_msg = await callback.bot.send_message(
        chat_id=chat_id,
        text="🛠️ <b>Панель Администратора</b>",
        parse_mode="HTML",
        reply_markup=get_admin_keyboard()
    )
    await state.update_data(admin_panel_msg_id=admin_msg.message_id)


@router.message(AdminState.waiting_for_broadcast_msg)
async def process_broadcast_send(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return

    user_ids = await get_all_user_ids()
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
