import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, BufferedInputFile, InputMediaPhoto, BotCommand
)
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from config import BOT_TOKEN, ADMIN_IDS
from tou_client import get_schedule_html
from parser import parse_schedule_items
from image_generator import generate_schedule_image
from database import (
    init_db, save_user_credentials, get_user_credentials,
    get_users_stats, get_all_user_ids
)

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


class AuthForm(StatesGroup):
    waiting_for_login = State()
    waiting_for_password = State()
    authorized = State()


class AdminState(StatesGroup):
    waiting_for_broadcast_msg = State()


def get_schedule_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Сегодня", callback_data="sched_today"),
            InlineKeyboardButton(text="📅 Завтра", callback_data="sched_tomorrow"),
            InlineKeyboardButton(text="🗓️ Неделя", callback_data="sched_week")
        ]
    ])


def get_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="admin_broadcast")]
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Команды и функционал АДМИН-ПАНЕЛИ
# ─────────────────────────────────────────────────────────────────────────────

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return

    await message.answer("🛠️ **Панель Администратора**", parse_mode="Markdown", reply_markup=get_admin_keyboard())


@dp.callback_query(F.data == "admin_stats")
async def process_admin_stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return

    count, logins = get_users_stats()
    logins_str = "\n".join([f"• `{login}`" for login in logins[:20]]) or "Нет зарегистрированных пользователей"
    
    text = (
        f"📊 **Статистика бота:**\n\n"
        f"👤 Всего пользователей: **{count}**\n\n"
        f"📋 Последние авторизованные логины:\n{logins_str}"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_admin_keyboard())


@dp.callback_query(F.data == "admin_broadcast")
async def process_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return

    await callback.message.edit_text("💬 Отправьте сообщение (текст/фото), которое вы хотите разослать всем пользователям:")
    await state.set_state(AdminState.waiting_for_broadcast_msg)


@dp.message(AdminState.waiting_for_broadcast_msg)
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
        f"✅ **Рассылка завершена!**\n\n"
        f"Успешно доставлено: **{success_count}**\n"
        f"Ошибок отправки (заблокировали бота): **{fail_count}**",
        parse_mode="Markdown"
    )
    await state.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Основная логика бота
# ─────────────────────────────────────────────────────────────────────────────

@dp.message(CommandStart())
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
        await message.answer("Привет! Для получения расписания введите ваш логин:")
        await state.set_state(AuthForm.waiting_for_login)


@dp.callback_query(F.data == "manual_login")
async def process_manual_login(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите ваш логин:")
    await state.set_state(AuthForm.waiting_for_login)


@dp.callback_query(F.data == "quick_login")
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
        
        items = parse_schedule_items(html_or_err, day="today")
        png_bytes = generate_schedule_image(items, title="Расписание на Сегодня", day_mode="today")
        photo = BufferedInputFile(png_bytes, filename="schedule.png")
        
        await status_msg.delete()
        await callback.message.answer_photo(
            photo=photo,
            caption="✅ Авторизация успешна! Актуальное расписание:",
            reply_markup=get_schedule_keyboard()
        )
    else:
        await status_msg.edit_text(f"❌ {html_or_err}")
        await state.clear()


@dp.message(AuthForm.waiting_for_login)
async def process_login(message: Message, state: FSMContext):
    await state.update_data(login=message.text.strip())
    await message.answer("Введите ваш пароль:")
    await state.set_state(AuthForm.waiting_for_password)


@dp.message(AuthForm.waiting_for_password)
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
        
        items = parse_schedule_items(html_or_err, day="today")
        png_bytes = generate_schedule_image(items, title="Расписание на Сегодня", day_mode="today")
        photo = BufferedInputFile(png_bytes, filename="schedule.png")
        
        await status_msg.delete()
        await message.answer_photo(
            photo=photo,
            caption="✅ Авторизация успешна! Актуальное расписание:",
            reply_markup=get_schedule_keyboard()
        )
    else:
        await status_msg.edit_text(f"❌ {html_or_err}")
        await state.clear()


@dp.callback_query(F.data.startswith("sched_"))
async def process_schedule_day(callback: CallbackQuery, state: FSMContext):
    day = callback.data.split("_")[1]
    user_data = await state.get_data()
    login = user_data.get("login")
    password = user_data.get("password")
    cached_html = user_data.get("cached_html")
    
    if not login or not password:
        await callback.answer("Сессия истекла. Нажмите /start заново.", show_alert=True)
        return

    await callback.answer("🔄 Загружаем расписание...")
    
    if not cached_html:
        success, html_or_err = await get_schedule_html(login, password)
        if success:
            cached_html = html_or_err
            await state.update_data(cached_html=cached_html)
        else:
            await callback.message.answer("❌ Не удалось обновить данные с сайта ToU.")
            return

    items = parse_schedule_items(cached_html, day=day)
    day_titles = {"today": "Сегодня", "tomorrow": "Завтра", "week": "Всю неделю"}
    label = day_titles.get(day, '')

    png_bytes = generate_schedule_image(items, title=f"Расписание на {label}", day_mode=day)
    photo = BufferedInputFile(png_bytes, filename="schedule.png")

    try:
        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=photo,
                caption=f"Обновлено: **{label}**",
                parse_mode="Markdown",
            ),
            reply_markup=get_schedule_keyboard()
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            await callback.message.answer_photo(
                photo=photo,
                caption=f"Обновлено: **{label}**",
                parse_mode="Markdown",
                reply_markup=get_schedule_keyboard()
            )


async def main():
    init_db()
    await bot.set_my_commands([
        BotCommand(command="start", description="Перезапустить бота / Авторизация"),
        BotCommand(command="admin", description="Панель администратора")
    ])
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())