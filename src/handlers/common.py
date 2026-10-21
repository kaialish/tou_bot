from datetime import datetime
import json
from src.config import get_kz_now
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext

from src.database import (
    get_user_credentials,
    get_cached_schedule,
    save_cached_schedule,
    save_cached_academic_status,
    get_cached_academic_status,
    save_cached_zhurnal,
    get_cached_zhurnal,
    subscribe_to_notifications,
    unsubscribe_from_notifications,
    is_user_subscribed,
    get_user_schedule_format,
    toggle_user_schedule_format,
)
from src.services import (
    get_schedule_html,
    get_dashboard_html,
    get_zhurnal_html,
    parse_key_dates,
    format_key_dates_message,
    format_schedule_text,
    parse_academic_status,
    format_academic_status_message,
    parse_zhurnal,
    format_zhurnal_brief,
    format_zhurnal_full_chunks,
)
from src.keyboards import (
    get_main_menu_keyboard,
    get_notifications_menu_keyboard,
    get_settings_keyboard,
    get_academic_status_keyboard,
    get_grades_keyboard,
    get_privacy_policy_keyboard,
    get_current_lesson_keyboard,
)
from src.utils import cleanup_previous_album, PRIVACY_POLICY_TEXT, clear_chat_history
from src.utils.lesson_widget import get_current_lesson_status, format_current_lesson_message
from src.states import AuthForm
from src.config import ADMIN_IDS

router = Router()


@router.message(Command("clear", "clean"))
async def cmd_clear(message: Message, state: FSMContext):
    """
    Команда /clear или /clean — быстрая очистка чата.
    Удаляет историю сообщений (до 100 последних сообщений) и возвращает главное меню.
    """
    chat_id = message.chat.id
    current_msg_id = message.message_id
    bot = message.bot
    user_id = message.from_user.id

    # Определяем количество сообщений для очистки (по умолчанию 100, либо: /clear 50)
    count = 100
    args = message.text.split() if message.text else []
    if len(args) > 1 and args[1].isdigit():
        count = min(100, max(1, int(args[1])))

    # Очищаем состояние FSM и сохранённые ID сообщений
    await state.clear()

    # Очищаем историю чата
    await clear_chat_history(bot=bot, chat_id=chat_id, current_msg_id=current_msg_id, count=count)

    # Отправляем главное меню
    is_admin = user_id in ADMIN_IDS
    creds = await get_user_credentials(user_id)
    if creds:
        await message.answer(
            "🧹 <b>Чат очищен!</b>\n\nГлавное меню бота:",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(is_admin=is_admin)
        )
    else:
        await message.answer(
            "🧹 <b>Чат очищен!</b>\n\nДля авторизации нажмите /start",
            parse_mode="HTML"
        )


@router.callback_query(F.data == "menu_key_dates")
async def process_menu_key_dates(callback: CallbackQuery, state: FSMContext):
    """Раздел: Ключевые даты."""
    user_data = await state.get_data()
    cached_html = user_data.get("cached_html")

    if not cached_html:
        # Сначала проверяем кэшированное расписание из БД
        db_cached = await get_cached_schedule(callback.from_user.id)
        if db_cached:
            cached_html, cached_at = db_cached
            await state.update_data(cached_html=cached_html, is_offline=True, cached_at=cached_at)
        else:
            login = user_data.get("login")
            password = user_data.get("password")
            if not login or not password:
                creds = await get_user_credentials(callback.from_user.id)
                if creds:
                    login, password = creds
                    await state.update_data(login=login, password=password)
                else:
                    await callback.answer("Сессия истекла. Нажмите /start заново.", show_alert=True)
                    return

            await callback.answer("🔄 Загружаем данные...")
            success, html_or_err = await get_schedule_html(login, password, bot=callback.bot)
            if success:
                cached_html = html_or_err
                now_str = get_kz_now().strftime("%d.%m.%Y в %H:%M")
                await save_cached_schedule(callback.from_user.id, cached_html, now_str)
                await state.update_data(cached_html=cached_html, is_offline=False, cached_at=now_str)
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


async def _load_and_render_academic_status(callback: CallbackQuery, state: FSMContext, is_refresh: bool = False):
    """Общий обработчик для загрузки и отображения академического статуса."""
    await callback.answer("🔄 Загружаем академический статус...")
    await cleanup_previous_album(callback.bot, callback.message.chat.id, state)

    user_data = await state.get_data()
    login = user_data.get("login")
    password = user_data.get("password")

    if not login or not password:
        creds = await get_user_credentials(callback.from_user.id)
        if creds:
            login, password = creds
            await state.update_data(login=login, password=password)
        else:
            await callback.answer("Сессия истекла. Нажмите /start заново.", show_alert=True)
            return

    # Запрашиваем страницу дашборда с портала
    success, html_or_err = await get_dashboard_html(login, password, bot=callback.bot)

    if success:
        status_data = parse_academic_status(html_or_err)
        now_str = get_kz_now().strftime("%d.%m.%Y в %H:%M")
        await save_cached_academic_status(callback.from_user.id, json.dumps(status_data, ensure_ascii=False), now_str)
        text = format_academic_status_message(status_data, updated_at=now_str)
        if is_refresh:
            await callback.answer("✅ Данные обновлены!", show_alert=False)
    else:
        # Проверяем кэш из БД
        cached = await get_cached_academic_status(callback.from_user.id)
        if cached:
            status_json, cached_at = cached
            try:
                status_data = json.loads(status_json)
                text = format_academic_status_message(status_data, updated_at=cached_at)
                text += "\n\n⚠️ <i>Отображены сохранённые данные (портал временно недоступен).</i>"
            except Exception:
                text = f"{html_or_err}\n\n<i>Кэш академического статуса повреждён. Попробуйте позже.</i>"
        else:
            text = html_or_err

    kb = get_academic_status_keyboard()

    if is_refresh:
        # При нажатии "Обновить" удаляем старое сообщение и отправляем свежее
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        # При первом входе из меню пробуем изменить текст на месте
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except TelegramBadRequest as e:
            if "message is not modified" in str(e).lower():
                pass
            else:
                try:
                    await callback.message.delete()
                except Exception:
                    pass
                await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data == "menu_academic_status")
async def process_menu_academic_status(callback: CallbackQuery, state: FSMContext):
    """Раздел: Академический статус."""
    await _load_and_render_academic_status(callback, state, is_refresh=False)


@router.callback_query(F.data == "refresh_academic_status")
async def process_refresh_academic_status(callback: CallbackQuery, state: FSMContext):
    """Обновление раздела Академический статус."""
    await _load_and_render_academic_status(callback, state, is_refresh=True)


async def _cleanup_grades_messages(bot, chat_id: int, state: FSMContext) -> None:
    """Удаляет предыдущие сообщения полного журнала при переключении."""
    user_data = await state.get_data()
    msg_ids = user_data.get("grades_msg_ids", [])
    for mid in msg_ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=mid)
        except Exception:
            pass
    await state.update_data(grades_msg_ids=[])


async def _load_and_render_grades(callback: CallbackQuery, state: FSMContext, is_refresh: bool = False, view: str = "brief") -> None:
    """Загружает данные журнала успеваемости и отображает их пользователю."""
    user_data = await state.get_data()
    login = user_data.get("login")
    password = user_data.get("password")

    # Если в стейте нет логина/пароля, достаем из БД
    if not login or not password:
        creds = await get_user_credentials(callback.from_user.id)
        if not creds:
            await callback.answer("⚠️ Вы не авторизованы. Отправьте /start", show_alert=True)
            return
        login, password = creds
        await state.update_data(login=login, password=password)

    courses = None
    cached_at = ""

    # Если это не переключение вида при уже загруженном журнале — проверяем/запрашиваем
    cached_courses_json = user_data.get("cached_zhurnal_json")
    cached_courses_time = user_data.get("cached_zhurnal_time")

    if cached_courses_json and not is_refresh:
        try:
            courses = json.loads(cached_courses_json)
            cached_at = cached_courses_time or ""
        except Exception:
            courses = None

    if courses is None or is_refresh:
        success, html_or_err = await get_zhurnal_html(login, password, bot=callback.bot)

        if success:
            courses = parse_zhurnal(html_or_err)
            now_str = get_kz_now().strftime("%d.%m.%Y в %H:%M")
            cached_at = now_str
            courses_json = json.dumps(courses, ensure_ascii=False)
            await state.update_data(cached_zhurnal_json=courses_json, cached_zhurnal_time=now_str)
            await save_cached_zhurnal(callback.from_user.id, courses_json, now_str)
            if is_refresh:
                await callback.answer("✅ Журнал обновлен!", show_alert=False)
        else:
            # Пробуем достать кэш из БД
            db_cached = await get_cached_zhurnal(callback.from_user.id)
            if db_cached:
                try:
                    courses = json.loads(db_cached[0])
                    cached_at = f"{db_cached[1]} (кэш)"
                except Exception:
                    courses = None

            if not courses:
                # Ошибка и нет кэша
                try:
                    await callback.message.edit_text(html_or_err, parse_mode="HTML", reply_markup=get_grades_keyboard("brief"))
                except Exception:
                    await callback.message.answer(html_or_err, parse_mode="HTML", reply_markup=get_grades_keyboard("brief"))
                return

    # Очищаем старые сообщения полного журнала если были
    await _cleanup_grades_messages(callback.bot, callback.message.chat.id, state)

    kb = get_grades_keyboard(view)

    if view == "brief":
        text = format_zhurnal_brief(courses, updated_at=cached_at)
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
            await state.update_data(grades_msg_ids=[callback.message.message_id])
        except TelegramBadRequest as e:
            if "message is not modified" in str(e).lower():
                await state.update_data(grades_msg_ids=[callback.message.message_id])
            else:
                try:
                    await callback.message.delete()
                except Exception:
                    pass
                sent = await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
                await state.update_data(grades_msg_ids=[sent.message_id])
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            sent = await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
            await state.update_data(grades_msg_ids=[sent.message_id])
    else:
        # view == "full"
        chunks = format_zhurnal_full_chunks(courses, updated_at=cached_at)
        # Удаляем предыдущее меню/сообщение
        try:
            await callback.message.delete()
        except Exception:
            pass

        sent_ids = []
        for idx, chunk in enumerate(chunks):
            # Кнопки прикрепляем только к последнему сообщению
            reply_markup = kb if idx == len(chunks) - 1 else None
            sent = await callback.message.answer(chunk, parse_mode="HTML", reply_markup=reply_markup)
            sent_ids.append(sent.message_id)

        await state.update_data(grades_msg_ids=sent_ids)


@router.callback_query(F.data == "menu_grades")
async def process_menu_grades(callback: CallbackQuery, state: FSMContext):
    """Раздел: Успеваемость (краткий вид по умолчанию)."""
    await _load_and_render_grades(callback, state, is_refresh=False, view="brief")


@router.callback_query(F.data == "refresh_grades")
async def process_refresh_grades(callback: CallbackQuery, state: FSMContext):
    """Обновление журнала успеваемости."""
    await _load_and_render_grades(callback, state, is_refresh=True, view="brief")


@router.callback_query(F.data == "grades_view_full")
async def process_grades_view_full(callback: CallbackQuery, state: FSMContext):
    """Переключение на полный вид журнала успеваемости."""
    await _load_and_render_grades(callback, state, is_refresh=False, view="full")


@router.callback_query(F.data == "grades_view_brief")
async def process_grades_view_brief(callback: CallbackQuery, state: FSMContext):
    """Переключение на краткий вид журнала успеваемости."""
    await _load_and_render_grades(callback, state, is_refresh=False, view="brief")


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
                "🏠 <b>Главное меню</b>\nВыберите нужный раздел:",
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard(is_admin=is_admin)
            )
            await state.update_data(main_menu_msg_id=callback.message.message_id)
            return
        except Exception:
            pass

    main_msg = await callback.bot.send_message(
        chat_id=chat_id,
        text="🏠 <b>Главное меню</b>\nВыберите нужный раздел:",
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard(is_admin=is_admin)
    )
    await state.update_data(main_menu_msg_id=main_msg.message_id)


# ────────────────────────────────────────────────────────────────────────────
# Раздел: Настройки и вид расписания
# ────────────────────────────────────────────────────────────────────────────

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

    notify_desc = "✅ <b>Включены</b>" if is_sub else "❌ <b>Отключены</b>"

    text = (
        "⚙️ <b>Настройки бота</b>\n\n"
        f"🔔 <b>Уведомления об окончании пар:</b> {notify_desc}\n\n"
        "<i>💡 При включении бот будет присылать уведомление за пару минут до окончания пары, "
        "а также сообщать, сколько продлится следующая перемена (её длительность и время на отдых).</i>\n\n"
        "Нажмите на кнопку ниже, чтобы переключить параметр:"
    )

    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_settings_keyboard(is_subscribed=is_sub)
        )
    except Exception:
        await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=get_settings_keyboard(is_subscribed=is_sub)
        )


@router.callback_query(F.data == "settings_toggle_format")
async def process_settings_toggle_format(callback: CallbackQuery):
    """Переключение вида расписания из меню настроек (для обратной совместимости)."""
    user_id = callback.from_user.id
    new_format = await toggle_user_schedule_format(user_id)
    is_sub = await is_user_subscribed(user_id)

    mode_name = "📝 Текстовый вид" if new_format == "text" else "🖼️ Картинка (PNG)"
    await callback.answer(f"Вид изменен на: {mode_name}", show_alert=False)

    notify_desc = "✅ <b>Включены</b>" if is_sub else "❌ <b>Отключены</b>"

    text = (
        "⚙️ <b>Настройки бота</b>\n\n"
        f"🔔 <b>Уведомления об окончании пар:</b> {notify_desc}\n\n"
        "<i>💡 При включении бот будет присылать уведомление за пару минут до окончания пары, "
        "а также сообщать, сколько продлится следующая перемена (её длительность и время на отдых).</i>\n\n"
        "Нажмите на кнопку ниже, чтобы переключить параметр:"
    )

    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_settings_keyboard(is_subscribed=is_sub)
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

    notify_desc = "✅ <b>Включены</b>" if new_sub else "❌ <b>Отключены</b>"

    text = (
        "⚙️ <b>Настройки бота</b>\n\n"
        f"🔔 <b>Уведомления об окончании пар:</b> {notify_desc}\n\n"
        "<i>💡 При включении бот будет присылать уведомление за пару минут до окончания пары, "
        "а также сообщать, сколько продлится следующая перемена (её длительность и время на отдых).</i>\n\n"
        "Нажмите на кнопку ниже, чтобы переключить параметр:"
    )

    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_settings_keyboard(is_subscribed=new_sub)
        )
    except Exception:
        pass


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


@router.callback_query(F.data == "widget_current_lesson")
async def process_current_lesson(callback: CallbackQuery):
    """Отображает текущую пару/перемену в виде виджета."""
    status = get_current_lesson_status()
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