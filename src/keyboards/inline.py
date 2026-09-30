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
            [
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu_settings"),
            ],
        ]
    )


def get_schedule_keyboard(current_format: str = "photo") -> InlineKeyboardMarkup:
    """Клавиатура для выбора дня расписания с тумблером формата (Фото/Текст)."""
    toggle_text = "📝 Текстовый вид" if current_format == "photo" else "🖼️ Карточки (фото)"

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
                InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_schedule"),
                InlineKeyboardButton(text=toggle_text, callback_data="toggle_schedule_format"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main_menu"),
            ],
        ]
    )


def get_settings_keyboard(schedule_format: str = "photo", is_subscribed: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура меню настроек (формат расписания и подписка)."""
    format_label = "🖼️ Картинка (PNG)" if schedule_format == "photo" else "📝 Текст (быстро)"
    notify_label = "🔔 Включены" if is_subscribed else "🔕 Отключены"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"Вид расписания: {format_label}", callback_data="settings_toggle_format"),
            ],
            [
                InlineKeyboardButton(text=f"Уведомления о парах: {notify_label}", callback_data="settings_toggle_notifications"),
            ],
            [
                InlineKeyboardButton(text="⬅️ В главное меню", callback_data="back_to_main_menu"),
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


def get_notifications_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню управления уведомлениями об окончании пар."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подписаться на уведомления", callback_data="subscribe_notifications"),
            ],
            [
                InlineKeyboardButton(text="❌ Отписаться от уведомлений", callback_data="unsubscribe_notifications"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main_menu"),
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