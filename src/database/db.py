"""
Слой базы данных (фасад для 100% обратной совместимости).
Все реализации вынесены в специализированные модули:
- `src.database.crypto` — управление мастер-ключом (SECRET_KEY) и шифрование Fernet
- `src.database.schema` — путь к SQLite базе и DDL миграции (init_db)
- `src.database.repositories.users` — учётные записи, пароли, статистика пользователей
- `src.database.repositories.subscriptions` — подписки на пары, MOOK, формат расписания
- `src.database.repositories.cache` — кэширование расписания, GPA и журнала успеваемости
- `src.database.repositories.system` — технические перерывы и состояние бота
"""

from src.database.crypto import cipher, KEY_FILE
from src.database.schema import DB_NAME, init_db
from src.database.repositories.users import (
    save_user_credentials,
    get_user_credentials,
    is_user_password_saved,
    delete_user_account,
    get_users_stats,
    get_all_user_ids,
)
from src.database.repositories.subscriptions import (
    subscribe_to_notifications,
    unsubscribe_from_notifications,
    is_user_subscribed,
    get_subscribed_users,
    get_subscribed_users_with_schedules,
    get_user_mook_setting,
    toggle_user_mook_setting,
    get_last_notification_msg_id,
    set_last_notification_msg_id,
    get_user_schedule_format,
    set_user_schedule_format,
    toggle_user_schedule_format,
)
from src.database.repositories.cache import (
    save_cached_schedule,
    get_cached_schedule,
    save_cached_academic_status,
    get_cached_academic_status,
    save_cached_zhurnal,
    get_cached_zhurnal,
)
from src.database.repositories.system import (
    set_maintenance_status,
    is_maintenance_active,
)

__all__ = [
    "cipher",
    "KEY_FILE",
    "DB_NAME",
    "init_db",
    "save_user_credentials",
    "get_user_credentials",
    "is_user_password_saved",
    "delete_user_account",
    "get_users_stats",
    "get_all_user_ids",
    "subscribe_to_notifications",
    "unsubscribe_from_notifications",
    "is_user_subscribed",
    "get_subscribed_users",
    "get_subscribed_users_with_schedules",
    "get_user_mook_setting",
    "toggle_user_mook_setting",
    "get_last_notification_msg_id",
    "set_last_notification_msg_id",
    "get_user_schedule_format",
    "set_user_schedule_format",
    "toggle_user_schedule_format",
    "save_cached_schedule",
    "get_cached_schedule",
    "save_cached_academic_status",
    "get_cached_academic_status",
    "save_cached_zhurnal",
    "get_cached_zhurnal",
    "set_maintenance_status",
    "is_maintenance_active",
]
