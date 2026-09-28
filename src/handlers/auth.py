from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from src.database import get_user_credentials, save_user_credentials
from src.services import get_schedule_html
from src.keyboards import get_main_menu_keyboard

router = Router()


class AuthForm(StatesGroup):
    waiting_for_login = State()
    waiting_for_password = State()
    authorized = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    saved_data = get_user_credentials(message.from_user.id)

    if saved_data:
        saved_login, _ = saved_data
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🔑 Войти как {saved_login}", callback_data="quick_login")],
            [InlineKeyboardButton(text="✏️ Ввести другой логин", callback_data="manual_login")]
        ])
        await message.answer("С возвращением! Войти под сохраненным аккаунтом?", reply_markup=kb)
    else:
        await message.answer("Привет! Для получения доступа к личному кабинету введите ваш логин:")
        await state.set_state(AuthForm.waiting_for_login)


@router.callback_query(F.data == "manual_login")
async def process_manual_login(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите ваш логин:")
    await state.set_state(AuthForm.waiting_for_login)


@router.callback_query(F.data == "quick_login")
async def process_quick_login(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    saved_data = get_user_credentials(user_id)
    if not saved_data:
        await callback.answer("Данные не найдены. Введите логин вручную.", show_alert=True)
        await state.set_state(AuthForm.waiting_for_login)
        return

    login, password = saved_data
    await state.update_data(login=login, password=password)

    status_msg = await callback.message.edit_text("🔄 Подключаемся к порталу ToU...")

    success, html_or_err = await get_schedule_html(login, password)
    if success:
        await state.set_state(AuthForm.authorized)
        await state.update_data(cached_html=html_or_err)

        await status_msg.delete()
        await callback.message.answer(
            f"✅ Добро пожаловать, **{login}**!\nВыберите нужный раздел из меню ниже:",
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await status_msg.edit_text(f"❌ {html_or_err}")
        await state.clear()


@router.message(AuthForm.waiting_for_login)
async def process_login(message: Message, state: FSMContext):
    await state.update_data(login=message.text.strip())
    await message.answer("Введите ваш пароль:")
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

    success, html_or_err = await get_schedule_html(login, password)

    if success:
        await state.set_state(AuthForm.authorized)
        await state.update_data(cached_html=html_or_err)
        save_user_credentials(user_id, login, password)

        await status_msg.delete()
        await message.answer(
            f"✅ Авторизация успешна! Добро пожаловать, **{login}**.\nВыберите нужный раздел:",
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await status_msg.edit_text(f"❌ {html_or_err}")
        await state.clear()
