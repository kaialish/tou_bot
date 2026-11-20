from datetime import datetime
from src.config import get_kz_now
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from src.database import (
    get_cached_schedule,
    save_cached_schedule,
    get_user_credentials,
)
from src.services import (
    get_schedule_html,
    parse_schedule_items,
    format_schedule_text,
)
from src.keyboards import (
    get_main_menu_keyboard,
    get_current_lesson_keyboard,
)
from src.utils import cleanup_previous_album, clear_chat_history
from src.utils.lesson_widget import get_current_lesson_status, format_current_lesson_message
from src.states import AuthForm
from src.config import ADMIN_IDS

router = Router()

@router.message(Command("clear", "clean"))
async def cmd_clear(message: Message, state: FSMContext):
    """
    Команда /clear или /clean — быстрая очистка чата.
    Удаляет историю сообщений (весь чат) и возвращает главное меню.
    """
    chat_id = message.chat.id
    current_msg_id = message.message_id
    bot = message.bot
    user_id = message.from_user.id

    # Определяем количество сообщений для очистки:
    # По умолчанию — 2000 (весь чат от начала до конца), либо указанное число: /clear 50
    count = 2000
    args = message.text.split() if message.text else []
    if len(args) > 1 and args[1].isdigit():
        count = max(1, int(args[1]))

    # Сначала удаляем временные сохранённые медиагруппы альбомов
    try:
        await cleanup_previous_album(bot, chat_id, state)
    except Exception:
        pass

    # Очищаем состояние FSM и сохранённые ID сообщений
    await state.clear()

    # Очищаем историю чата
    await clear_chat_history(bot=bot, chat_id=chat_id, current_msg_id=current_msg_id, count=count)

    # Отправляем главное меню
    is_admin = user_id in ADMIN_IDS
    creds = await get_user_credentials(user_id)
    if creds:
        await state.set_state(AuthForm.authorized)
        msg = await message.answer(
            "🧹 <b>Чат полностью очищен!</b>\n\nГлавное меню бота:",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(is_admin=is_admin)
        )
        await state.update_data(main_menu_msg_id=msg.message_id)
    else:
        await message.answer(
            "🧹 <b>Чат полностью очищен!</b>\n\nДля авторизации нажмите /start",
            parse_mode="HTML"
        )




@router.callback_query(F.data == "back_to_main_menu")
async def process_back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в Главное меню. Удаляет текущее сообщение (панель админа, расписание, статус и т.д.) и отображает Главное меню."""
    await callback.answer()

    data = await state.get_data()
    admin_panel_msg_id = data.get("admin_panel_msg_id")

    chat_id = callback.message.chat.id if callback.message else callback.from_user.id

    # Сначала удаляем ВСЕ временные сообщения (альбом расписания, сообщения полного журнала) ДО очистки состояния
    try:
        await cleanup_previous_album(callback.bot, chat_id, state)
    except Exception:
        pass

    try:
        await _cleanup_grades_messages(callback.bot, chat_id, state)
    except Exception:
        pass

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

    if admin_panel_msg_id and admin_panel_msg_id != (callback.message.message_id if callback.message else None):
        try:
            await callback.bot.delete_message(chat_id=chat_id, message_id=admin_panel_msg_id)
        except Exception:
            pass

    await state.set_state(AuthForm.authorized)
    await state.update_data(admin_panel_msg_id=None)

    is_admin = callback.from_user.id in ADMIN_IDS

    if not deleted and callback.message:
        # Если удалить сообщение не удалось, редактируем его в Главное меню
        try:
            await callback.message.edit_text(
                "🏠 <b>Главное меню ToU Bot</b>\nНажмите кнопку ниже, чтобы открыть приложение:",
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard(is_admin=is_admin)
            )
            await state.update_data(main_menu_msg_id=callback.message.message_id)
            return
        except Exception:
            pass

    main_msg = await callback.bot.send_message(
        chat_id=chat_id,
        text="🎓 <b>Добро пожаловать в ToUBot!</b>\n\nНажмите по кнопке ниже для перехода в приложение:",
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard(is_admin=is_admin)
    )
    await state.update_data(main_menu_msg_id=main_msg.message_id)


# ────────────────────────────────────────────────────────────────────────────
# Раздел: Настройки и вид расписания
# ────────────────────────────────────────────────────────────────────────────



@router.callback_query(F.data == "widget_current_lesson")
async def process_current_lesson(callback: CallbackQuery, state: FSMContext):
    """Отображает текущую пару/перемену в виде виджета с предметом и аудиторией."""
    user_id = callback.from_user.id
    user_data = await state.get_data()
    cached_html = user_data.get("cached_html")

    if not cached_html:
        db_cached = await get_cached_schedule(user_id)
        if db_cached:
            cached_html, cached_at = db_cached
            await state.update_data(cached_html=cached_html, is_offline=True, cached_at=cached_at)

    today_lessons = None
    if cached_html:
        try:
            today_lessons = parse_schedule_items(cached_html, day="today")
        except Exception:
            today_lessons = None

    status = get_current_lesson_status(today_lessons=today_lessons)
    text = format_current_lesson_message(status)
    reply_markup = get_current_lesson_keyboard()

    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
        await callback.answer("✅ Данные обновлены!", show_alert=False)
    except TelegramBadRequest:
        # Сообщение не изменилось при повторном нажатии "Обновить"
        await callback.answer("✅ Данные актуальны", show_alert=False)
    except Exception:
        await callback.answer()
        await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
