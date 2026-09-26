import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BufferedInputFile, InputMediaPhoto
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from config import BOT_TOKEN
from tou_client import get_schedule_html
from parser import parse_schedule_items
from image_generator import generate_schedule_image

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class AuthForm(StatesGroup):
    waiting_for_login = State()
    waiting_for_password = State()
    authorized = State()

def get_schedule_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Сегодня", callback_data="sched_today"),
            InlineKeyboardButton(text="📅 Завтра", callback_data="sched_tomorrow"),
            InlineKeyboardButton(text="🗓️ Неделя", callback_data="sched_week")
        ]
    ])

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await message.answer("Привет! Для получения расписания введите ваш логин:")
    await state.set_state(AuthForm.waiting_for_login)

@dp.message(AuthForm.waiting_for_login)
async def process_login(message: Message, state: FSMContext):
    await state.update_data(login=message.text)
    await message.answer("Введите ваш пароль:")
    await state.set_state(AuthForm.waiting_for_password)

@dp.message(AuthForm.waiting_for_password)
async def process_password(message: Message, state: FSMContext):
    password = message.text
    user_data = await state.get_data()
    login = user_data['login']
    
    await state.update_data(password=password)
    await message.answer("🔄 Подключаемся к порталу ToU...")
    
    success, html_or_err = await get_schedule_html(login, password)
    
    if success:
        await state.set_state(AuthForm.authorized)
        items = parse_schedule_items(html_or_err, day="today")
        
        png_bytes = generate_schedule_image(items, title="Расписание на Сегодня")
        photo = BufferedInputFile(png_bytes, filename="schedule.png")
        
        await message.answer_photo(
            photo=photo,
            caption="✅ Авторизация успешна! Актуальное расписание:",
            reply_markup=get_schedule_keyboard()
        )
    else:
        await message.answer(f"❌ {html_or_err}")
        await state.clear()

@dp.callback_query(F.data.startswith("sched_"))
async def process_schedule_day(callback: CallbackQuery, state: FSMContext):
    day = callback.data.split("_")[1]
    user_data = await state.get_data()
    login = user_data.get("login")
    password = user_data.get("password")
    
    if not login or not password:
        await callback.answer("Сессия истекла. Нажмите /start заново.", show_alert=True)
        return

    await callback.answer("🔄 Обновляем расписание с сайта...")
    
    success, html_or_err = await get_schedule_html(login, password)
    
    if success:
        items = parse_schedule_items(html_or_err, day=day)
        day_titles = {"today": "Сегодня", "tomorrow": "Завтра", "week": "Всю неделю"}
        label = day_titles.get(day, '')

        png_bytes = generate_schedule_image(items, title=f"Расписание на {label}")
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
        except Exception:
            # Если сообщение нельзя отредактировать — отправляем новое
            await callback.message.answer_photo(
                photo=photo,
                caption=f"Обновлено: **{label}**",
                parse_mode="Markdown",
                reply_markup=get_schedule_keyboard()
            )
    else:
        await callback.message.answer("❌ Не удалось обновить данные с сайта ToU.")


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
