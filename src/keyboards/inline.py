from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Главное меню бота."""
    keyboard = [
        [
            InlineKeyboardButton(text="🔎 Текущая пара", callback_data="widget_current_lesson"),
        ],
        [
            InlineKeyboardButton(text="📅 Расписание", callback_data="menu_schedule"),
        ],
        [
            InlineKeyboardButton(text="📆 Ключевые даты", callback_data="menu_key_dates"),
            InlineKeyboardButton(text="📊 Успеваемость", callback_data="menu_grades"),
        ],
        [
            InlineKeyboardButton(text="📌 Академический статус", callback_data="menu_academic_status"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu_settings"),
        ],
    ]
    if is_admin:
        keyboard.append([
            InlineKeyboardButton(text="🛠️ Панель администратора", callback_data="admin_panel"),
        ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_current_lesson_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для экрана виджета 'Текущая пара'."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Обновить", callback_data="widget_current_lesson"),
            ],
            [
                InlineKeyboardButton(text="⬅️ В главное меню", callback_data="back_to_main_menu"),
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


def get_settings_keyboard(is_subscribed: bool = True, *args, **kwargs) -> InlineKeyboardMarkup:
    """Клавиатура меню настроек (уведомления и конфиденциальность)."""
    notify_label = "🔔 Включены" if is_subscribed else "🔕 Отключены"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"Уведомления о парах: {notify_label}", callback_data="settings_toggle_notifications"),
            ],
            [
                InlineKeyboardButton(text="🛡️ Политика конфиденциальности", callback_data="settings_privacy_policy"),
            ],
            [
                InlineKeyboardButton(text="⬅️ В главное меню", callback_data="back_to_main_menu"),
            ],
        ]
    )


def get_privacy_policy_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для экрана политики конфиденциальности."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🐙 Исходный код на GitHub", url="https://github.com/kaialish/tou_bot"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад в настройки", callback_data="menu_settings"),
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


def get_academic_status_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для раздела 'Академический статус'."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_academic_status"),
            ],
            [
                InlineKeyboardButton(text="⬅️ В главное меню", callback_data="back_to_main_menu"),
            ],
        ]
    )


def get_grades_keyboard(current_view: str = "brief", current_part: int = 1) -> InlineKeyboardMarkup:
    """
    Клавиатура для раздела 'Успеваемость'.
    current_view: 'brief' (краткий) или 'full' (полный).
    """
    if current_view == "brief":
        toggle_button = InlineKeyboardButton(text="📖 Полный журнал", callback_data="grades_view_full")
    else:
        toggle_button = InlineKeyboardButton(text="📋 Краткий журнал", callback_data="grades_view_brief")

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{'✓ ' if current_part == part else ''}{part} часть",
                    callback_data=f"grades_part_{part}",
                )
                for part in (1, 2)
            ],
            [
                toggle_button,
                InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_grades"),
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