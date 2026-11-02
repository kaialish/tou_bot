from datetime import datetime
from src.config import get_kz_now
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext

from src.database import (
    get_user_credentials, save_user_credentials,
    save_cached_schedule, get_cached_schedule
)
from src.services import get_schedule_html
from src.keyboards import get_disclaimer_keyboard, get_main_menu_keyboard, get_storage_mode_keyboard
from src.states import AuthForm
from src.utils import DISCLAIMER_TEXT
from src.config import ADMIN_IDS

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    saved_data = await get_user_credentials(message.from_user.id)

    if saved_data:
        saved_login, saved_password = saved_data
        if saved_password:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"🔑 Войти как {saved_login}", callback_data="quick_login")],
                [InlineKeyboardButton(text="✏️ Ввести другой логин", callback_data="manual_login")]
            ])
            await message.answer("С возвращением! Войти под сохраненным аккаунтом?", reply_markup=kb)
        else:
            # Пользователь в режиме максимальной безопасности (без пароля)
            db_cached = await get_cached_schedule(message.from_user.id)
            if db_cached:
                cached_html, cached_at = db_cached
                await state.set_state(AuthForm.authorized)
                await state.update_data(login=saved_login, cached_html=cached_html, is_offline=True, cached_at=cached_at)
                msg = await message.answer(
                    f"👋 С возвращением в ToUBot, <b>{saved_login}</b>!\n"
                    f"Режим: 🛡️ <b>Максимальная безопасность</b> (без сохранения пароля)\n\n"
                    f"Выберите нужный раздел из меню ниже:",
                    parse_mode="HTML",
                    reply_markup=get_main_menu_keyboard(is_admin=(message.from_user.id in ADMIN_IDS))
                )
                await state.update_data(main_menu_msg_id=msg.message_id)
            else:
                await message.answer(DISCLAIMER_TEXT, parse_mode="HTML", reply_markup=get_disclaimer_keyboard())
                await state.set_state(AuthForm.waiting_for_disclaimer_accept)
    else:
        # Показываем дисклеймер перед первичным вводом
        await message.answer(DISCLAIMER_TEXT, parse_mode="HTML", reply_markup=get_disclaimer_keyboard())
        await state.set_state(AuthForm.waiting_for_disclaimer_accept)


@router.callback_query(F.data == "manual_login")
async def process_manual_login(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(DISCLAIMER_TEXT, parse_mode="HTML", reply_markup=get_disclaimer_keyboard())
    await state.set_state(AuthForm.waiting_for_disclaimer_accept)


@router.callback_query(F.data == "accept_disclaimer")
async def process_accept_disclaimer(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("👤 Введите ваш логин от портала ToU:")
    await state.set_state(AuthForm.waiting_for_login)


@router.callback_query(F.data == "quick_login")
async def process_quick_login(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    saved_data = await get_user_credentials(user_id)
    if not saved_data:
        await callback.answer("Данные не найдены. Введите логин вручную.", show_alert=True)
        await callback.message.edit_text(DISCLAIMER_TEXT, parse_mode="HTML", reply_markup=get_disclaimer_keyboard())
        await state.set_state(AuthForm.waiting_for_disclaimer_accept)
        return

    login, password = saved_data
    await state.update_data(login=login, password=password)

    status_msg = await callback.message.edit_text("🔄 Подключаемся к порталу ToU...")

    success, html_or_err = await get_schedule_html(login, password, bot=callback.bot)
    if success:
        now_str = get_kz_now().strftime("%d.%m.%Y в %H:%M")
        await save_cached_schedule(user_id, html_or_err, now_str)
        await state.set_state(AuthForm.authorized)
        await state.update_data(cached_html=html_or_err, is_offline=False, cached_at=now_str)

        await status_msg.delete()
        msg = await callback.message.answer(
            f"✅ Добро пожаловать, <b>{login}</b>!\nВыберите нужный раздел из меню ниже:",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(is_admin=(user_id in ADMIN_IDS))
        )
        await state.update_data(main_menu_msg_id=msg.message_id)
    else:
        # Проверяем, есть ли сохранённое расписание в БД
        db_cached = await get_cached_schedule(user_id)
        if db_cached:
            cached_html, cached_at = db_cached
            await state.set_state(AuthForm.authorized)
            await state.update_data(cached_html=cached_html, is_offline=True, cached_at=cached_at)
            await status_msg.delete()
            msg = await callback.message.answer(
                f"⚠️ <b>Портал ToU временно не отвечает</b>\n\n"
                f"Вы вошли в автономном режиме. Доступно сохранённое расписание (загружено: <b>{cached_at}</b>).\n\n"
                f"Выберите нужный раздел:",
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard(is_admin=(user_id in ADMIN_IDS))
            )
            await state.update_data(main_menu_msg_id=msg.message_id)
        else:
            retry_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="quick_login")],
                [InlineKeyboardButton(text="✏️ Ввести другой логин", callback_data="manual_login")]
            ])
            await status_msg.edit_text(html_or_err, parse_mode="HTML", reply_markup=retry_kb)


@router.message(AuthForm.waiting_for_login)
async def process_login(message: Message, state: FSMContext):
    await state.update_data(login=message.text.strip())
    await message.answer("🔑 Введите ваш пароль:")
    await state.set_state(AuthForm.waiting_for_password)


@router.message(AuthForm.waiting_for_password)
async def process_password(message: Message, state: FSMContext):
    password = message.text.strip()
    user_id = message.from_user.id

    try:
        await message.delete()
    except Exception:
        pass

    user_data = await state.get_data()
    login = user_data.get('login')

    await state.update_data(password=password)
    status_msg = await message.answer("🔄 Подключаемся к порталу ToU...")

    success, html_or_err = await get_schedule_html(login, password, bot=message.bot)

    if success:
        now_str = get_kz_now().strftime("%d.%m.%Y в %H:%M")
        await save_cached_schedule(user_id, html_or_err, now_str)
        await state.update_data(
            cached_html=html_or_err,
            is_offline=False,
            cached_at=now_str,
            temp_login=login,
            temp_password=password
        )

        await status_msg.delete()
        mode_text = (
            "🔐 <b>Авторизация успешна!</b>\n\n"
            "Выберите режим хранения ваших данных в боте:\n\n"
            "⚡ <b>Обычный (Быстрый вход)</b>\n"
            "<i>Пароль надёжно шифруется (Fernet). Бот автоматически обновляет расписание, статус и журнал оценок в 1 клик.</i>\n\n"
            "🛡️ <b>Максимальная безопасность</b>\n"
            "<i>Пароль НЕ сохраняется в базе бота. Сохраняется только расписание на семестр. Пароль сразу же стирается.</i>"
        )
        await message.answer(
            mode_text,
            parse_mode="HTML",
            reply_markup=get_storage_mode_keyboard()
        )
        await state.set_state(AuthForm.waiting_for_storage_mode)
    else:
        retry_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="retry_auth")],
            [InlineKeyboardButton(text="✏️ Ввести заново", callback_data="manual_login")]
        ])
        await status_msg.edit_text(html_or_err, parse_mode="HTML", reply_markup=retry_kb)


@router.callback_query(F.data == "retry_auth")
async def process_retry_auth(callback: CallbackQuery, state: FSMContext):
    """Повторная попытка авторизации после сбоя портала ToU."""
    user_data = await state.get_data()
    login = user_data.get("login")
    password = user_data.get("password")

    if not login or not password:
        saved_data = await get_user_credentials(callback.from_user.id)
        if saved_data:
            login, password = saved_data
            await state.update_data(login=login, password=password)
        else:
            await callback.answer("Данные не найдены. Введите логин заново.", show_alert=True)
            await callback.message.edit_text("👤 Введите ваш логин от портала ToU:")
            await state.set_state(AuthForm.waiting_for_login)
            return

    status_msg = await callback.message.edit_text("🔄 Подключаемся к порталу ToU...")

    success, html_or_err = await get_schedule_html(login, password, bot=callback.bot)
    if success:
        now_str = get_kz_now().strftime("%d.%m.%Y в %H:%M")
        await save_cached_schedule(callback.from_user.id, html_or_err, now_str)
        await state.set_state(AuthForm.authorized)
        await state.update_data(cached_html=html_or_err, is_offline=False, cached_at=now_str)
        await save_user_credentials(callback.from_user.id, login, password)

        await status_msg.delete()
        msg = await callback.message.answer(
            f"✅ Авторизация успешна! Добро пожаловать, <b>{login}</b>.\nВыберите нужный раздел:",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(is_admin=(callback.from_user.id in ADMIN_IDS))
        )
        await state.update_data(main_menu_msg_id=msg.message_id)
    else:
        db_cached = await get_cached_schedule(callback.from_user.id)
        if db_cached:
            cached_html, cached_at = db_cached
            await state.set_state(AuthForm.authorized)
            await state.update_data(cached_html=cached_html, is_offline=True, cached_at=cached_at)
            await status_msg.delete()
            msg = await callback.message.answer(
                f"⚠️ <b>Портал ToU временно не отвечает</b>\n\n"
                f"Вы вошли в автономном режиме. Доступно сохранённое расписание (загружено: <b>{cached_at}</b>).\n\n"
                f"Выберите нужный раздел:",
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard(is_admin=(callback.from_user.id in ADMIN_IDS))
            )
            await state.update_data(main_menu_msg_id=msg.message_id)
        else:
            retry_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="retry_auth")],
                [InlineKeyboardButton(text="✏️ Ввести заново", callback_data="manual_login")]
            ])
            await status_msg.edit_text(html_or_err, parse_mode="HTML", reply_markup=retry_kb)


@router.callback_query(F.data == "auth_mode_standard", AuthForm.waiting_for_storage_mode)
async def process_auth_mode_standard(callback: CallbackQuery, state: FSMContext):
    """Выбран обычный режим: пароль шифруется и сохраняется."""
    user_id = callback.from_user.id
    user_data = await state.get_data()
    login = user_data.get("temp_login")
    password = user_data.get("temp_password")

    await save_user_credentials(user_id, login, password, save_password=True)
    await state.update_data(login=login, password=password, temp_login=None, temp_password=None)
    await state.set_state(AuthForm.authorized)

    try:
        await callback.message.delete()
    except Exception:
        pass

    msg = await callback.message.answer(
        f"✅ <b>Добро пожаловать в ToUBot, {login}!</b>\n"
        f"Режим: ⚡ <b>Обычный (Быстрый вход)</b>\n\n"
        f"Выберите нужный раздел из меню ниже:",
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard(is_admin=(user_id in ADMIN_IDS))
    )
    await state.update_data(main_menu_msg_id=msg.message_id)


@router.callback_query(F.data == "auth_mode_secure", AuthForm.waiting_for_storage_mode)
async def process_auth_mode_secure(callback: CallbackQuery, state: FSMContext):
    """Выбран режим повышенной безопасности: пароль НЕ сохраняется в БД."""
    user_id = callback.from_user.id
    user_data = await state.get_data()
    login = user_data.get("temp_login")

    # Пароль не сохраняется в базе и стирается из стейта
    await save_user_credentials(user_id, login, "", save_password=False)
    await state.update_data(login=login, password=None, temp_login=None, temp_password=None)
    await state.set_state(AuthForm.authorized)

    try:
        await callback.message.delete()
    except Exception:
        pass

    msg = await callback.message.answer(
        f"✅ <b>Добро пожаловать в ToUBot, {login}!</b>\n"
        f"Режим: 🛡️ <b>Максимальная безопасность</b> (пароль не сохранён)\n\n"
        f"Выберите нужный раздел из меню ниже:",
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard(is_admin=(user_id in ADMIN_IDS))
    )
    await state.update_data(main_menu_msg_id=msg.message_id)
