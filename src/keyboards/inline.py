from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_disclaimer_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с подтверждением согласия с дисклеймером."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Понимаю и принимаю", callback_data="accept_disclaimer")]
    ])


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню личного кабинета из 3 пунктов."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Расписание", callback_data="menu_schedule")],
        [InlineKeyboardButton(text="📌 Академический статус", callback_data="menu_important_dates")],
        [InlineKeyboardButton(text="📊 Успеваемость", callback_data="menu_grades")]
    ])


def get_schedule_keyboard() -> InlineKeyboardMarkup:
    """Подменю выбора дня расписания + кнопка возврата в Главное меню."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Сегодня", callback_data="sched_today"),
            InlineKeyboardButton(text="📅 Завтра", callback_data="sched_tomorrow"),
            InlineKeyboardButton(text="🗓️ Неделя", callback_data="sched_week")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main_menu")
        ]
    ])


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура панели администратора."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="admin_broadcast")]
    ])
