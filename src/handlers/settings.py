from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from src.database import (
    subscribe_to_notifications,
    unsubscribe_from_notifications,
    is_user_subscribed,
    get_user_schedule_format,
    toggle_user_schedule_format,
    get_user_mook_setting,
    toggle_user_mook_setting,
    is_user_password_saved,
    delete_user_account,
)
from src.keyboards import (
    get_settings_keyboard,
    get_privacy_policy_keyboard,
    get_confirm_delete_keyboard,
    get_notifications_menu_keyboard,
)
from src.utils import PRIVACY_POLICY_TEXT
from src.states import AuthForm

router = Router()

async def _render_settings(callback: CallbackQuery, is_sub: bool, notify_mook: bool, is_pw_saved: bool = True):
    """Отображает экран настроек с актуальным состоянием параметров."""
    notify_desc = "✅ <b>Включены</b>" if is_sub else "❌ <b>Отключены</b>"
    mook_desc = "✅ <b>Включены</b>" if notify_mook else "❌ <b>Отключены</b>"
    pw_mode_desc = "⚡ <b>Обычный (Быстрый вход)</b>" if is_pw_saved else "🛡️ <b>Максимальная безопасность (без пароля)</b>"

    mook_line = (
        f"📱 <b>Уведомления для пар MOOK (дистант):</b> {mook_desc}\n"
        "<i>💡 При отключении уведомления о дистанционных парах приходить не будут.</i>\n\n"
    ) if is_sub else ""

    text = (
        "⚙️ <b>Настройки бота</b>\n\n"
        f"🔐 <b>Режим данных:</b> {pw_mode_desc}\n\n"
        f"🔔 <b>Уведомления об окончании пар:</b> {notify_desc}\n\n"
        "<i>💡 При включении бот будет присылать уведомление за пару минут до окончания пары, "
        "а также сообщать, сколько продлится следующая перемена (её длительность и время на отдых).</i>\n\n"
        f"{mook_line}"
        "Нажмите на кнопку ниже, чтобы переключить параметр:"
    )

    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_settings_keyboard(is_subscribed=is_sub, notify_mook=notify_mook)
        )
    except Exception:
        await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=get_settings_keyboard(is_subscribed=is_sub, notify_mook=notify_mook)
        )


@router.callback_query(F.data == "menu_settings")
async def process_menu_settings(callback: CallbackQuery, state: FSMContext):
    """Раздел персональных настроек пользователя."""
    chat_id = callback.message.chat.id if callback.message else callback.from_user.id
    try:
        await cleanup_previous_album(callback.bot, chat_id, state)
    except Exception:
        pass
    try:
        await _cleanup_grades_messages(callback.bot, chat_id, state)
    except Exception:
        pass

    user_id = callback.from_user.id
    is_sub = await is_user_subscribed(user_id)
    notify_mook = await get_user_mook_setting(user_id)
    is_pw_saved = await is_user_password_saved(user_id)
    await _render_settings(callback, is_sub, notify_mook, is_pw_saved)


@router.callback_query(F.data == "settings_toggle_format")
async def process_settings_toggle_format(callback: CallbackQuery):
    """Переключение вида расписания из меню настроек (для обратной совместимости)."""
    user_id = callback.from_user.id
    new_format = await toggle_user_schedule_format(user_id)
    is_sub = await is_user_subscribed(user_id)
    notify_mook = await get_user_mook_setting(user_id)
    is_pw_saved = await is_user_password_saved(user_id)

    mode_name = "📝 Текстовый вид" if new_format == "text" else "🖼️ Картинка (PNG)"
    await callback.answer(f"Вид изменен на: {mode_name}", show_alert=False)
    await _render_settings(callback, is_sub, notify_mook, is_pw_saved)


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

    notify_mook = await get_user_mook_setting(user_id)
    is_pw_saved = await is_user_password_saved(user_id)
    await _render_settings(callback, new_sub, notify_mook, is_pw_saved)


@router.callback_query(F.data == "settings_toggle_mook")
async def process_settings_toggle_mook(callback: CallbackQuery):
    """Переключение уведомлений для пар MOOK (дистанционное обучение)."""
    user_id = callback.from_user.id
    new_mook = await toggle_user_mook_setting(user_id)
    is_sub = await is_user_subscribed(user_id)
    label = "включены" if new_mook else "отключены"
    is_pw_saved = await is_user_password_saved(user_id)
    await callback.answer(f"📱 Уведомления MOOK {label}", show_alert=False)
    await _render_settings(callback, is_sub, new_mook, is_pw_saved)


@router.callback_query(F.data == "settings_privacy_policy")
async def process_settings_privacy_policy(callback: CallbackQuery):
    """Отображение политики конфиденциальности и защиты данных."""
    await callback.answer()
    try:
        await callback.message.edit_text(
            PRIVACY_POLICY_TEXT,
            parse_mode="HTML",
            reply_markup=get_privacy_policy_keyboard()
        )
    except Exception:
        await callback.message.answer(
            PRIVACY_POLICY_TEXT,
            parse_mode="HTML",
            reply_markup=get_privacy_policy_keyboard()
        )




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

@router.callback_query(F.data == "settings_delete_account")
async def process_settings_delete_account(callback: CallbackQuery):
    """Запрос подтверждения удаления всех данных пользователя."""
    await callback.answer()
    text = (
        "⚠️ <b>Удаление всех персональных данных</b>\n\n"
        "Вы действительно хотите безвозвратно удалить все свои данные из ToUBot?\n\n"
        "Будут удалены:\n"
        "• Ваша учётная запись и логин\n"
        "• Сохранённый пароль (если был сохранён)\n"
        "• Подписки на уведомления об окончании пар\n"
        "• Весь сохранённый кэш расписания, оценок и статуса\n\n"
        "❗️ <b>Это действие необратимо!</b>"
    )
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_confirm_delete_keyboard())
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=get_confirm_delete_keyboard())


@router.callback_query(F.data == "confirm_delete_account")
async def process_confirm_delete_account(callback: CallbackQuery, state: FSMContext):
    """Окончательное удаление всех данных пользователя."""
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id if callback.message else user_id

    try:
        await cleanup_previous_album(callback.bot, chat_id, state)
    except Exception:
        pass
    try:
        await _cleanup_grades_messages(callback.bot, chat_id, state)
    except Exception:
        pass

    await delete_user_account(user_id)
    await state.clear()

    await callback.answer("✅ Все данные успешно удалены", show_alert=True)
    text = (
        "🗑️ <b>Ваши данные полностью удалены</b>\n\n"
        "Все ваши персональные данные, учётная запись, подписки и кэш безвозвратно стёрты из базы бота.\n\n"
        "Спасибо, что пользовались ToUBot! Если захотите вернуться, просто отправьте команду /start ✨"
    )
    try:
        await callback.message.edit_text(text, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, parse_mode="HTML")
