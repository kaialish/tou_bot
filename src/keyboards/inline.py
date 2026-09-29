from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню бота."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 Расписание", callback_data="menu_schedule"),
            ],
            [
                InlineKeyboardButton(text="📆 Ключевые даты", callback_data="menu_key_dates"),
            ],
            [
                InlineKeyboardButton(text="📌 Академический статус", callback_data="menu_academic_status"),
                InlineKeyboardButton(text="📊 Успеваемость", callback_data="menu_grades"),
            ],
        ]
    )


def get_schedule_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора дня расписания."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Сегодня", callback_data="schedule_today"),
                InlineKeyboardButton(text="Завтра", callback_data="schedule_tomorrow"),
            ],
            [
                InlineKeyboardButton(text="Вся неделя", callback_data="schedule_week"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main_menu"),
            ],
        ]
    )


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура панели администратора."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
                InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"),
            ],
            [
                InlineKeyboardButton(text="⬅️ В главное меню", callback_data="back_to_main_menu"),
            ],
        ]
    )


def get_disclaimer_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой принятия условий."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принять и продолжить", callback_data="accept_disclaimer"),
            ]
        ]
    )