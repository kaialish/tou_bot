import aiosqlite
from src.database.schema import DB_NAME

async def subscribe_to_notifications(user_id: int) -> bool:
    """Подписывает пользователя на уведомления об окончании пар."""
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("""
                INSERT OR REPLACE INTO notification_subscriptions (user_id, is_subscribed)
                VALUES (?, 1)
            """, (user_id,))
            await db.commit()
        return True
    except Exception as e:
        print(f"Ошибка при подписке: {e}")
        return False


async def unsubscribe_from_notifications(user_id: int) -> bool:
    """Отписывает пользователя от уведомлений об окончании пар."""
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("""
                INSERT OR REPLACE INTO notification_subscriptions (user_id, is_subscribed)
                VALUES (?, 0)
            """, (user_id,))
            await db.commit()
        return True
    except Exception as e:
        print(f"Ошибка при отписке: {e}")
        return False


async def is_user_subscribed(user_id: int) -> bool:
    """Проверяет, подписан ли пользователь на уведомления."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT is_subscribed FROM notification_subscriptions WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()

    return bool(row and row[0])


async def get_subscribed_users() -> list[int]:
    """Возвращает список user_id пользователей, подписанных на уведомления."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("""
            SELECT user_id FROM notification_subscriptions WHERE is_subscribed = 1
        """) as cursor:
            rows = await cursor.fetchall()
    return [row[0] for row in rows]


async def get_subscribed_users_with_schedules() -> list[tuple[int, str | None, bool, int | None]]:
    """Возвращает список (user_id, schedule_html, notify_mook, last_notification_msg_id) для всех подписанных пользователей."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("""
            SELECT s.user_id, c.schedule_html, COALESCE(s.notify_mook, 0), s.last_notification_msg_id
            FROM notification_subscriptions s
            LEFT JOIN cached_schedules c ON s.user_id = c.user_id
            WHERE s.is_subscribed = 1
        """) as cursor:
            rows = await cursor.fetchall()
    return [(row[0], row[1], bool(row[2]), row[3]) for row in rows]


async def get_user_mook_setting(user_id: int) -> bool:
    """Проверяет, включены ли у пользователя уведомления для пар MOOK (по умолчанию False - отключены)."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT notify_mook FROM notification_subscriptions WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
    return bool(row and row[0])


async def toggle_user_mook_setting(user_id: int) -> bool:
    """Переключает тумблер уведомлений для пар MOOK. Возвращает новое состояние."""
    current = await get_user_mook_setting(user_id)
    new_val = 0 if current else 1
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO notification_subscriptions (user_id, is_subscribed, notify_mook)
            VALUES (?, 1, ?)
            ON CONFLICT(user_id) DO UPDATE SET notify_mook = excluded.notify_mook
        """, (user_id, new_val))
        await db.commit()
    return bool(new_val)


async def get_last_notification_msg_id(user_id: int) -> int | None:
    """Возвращает message_id последнего отправленного уведомления."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT last_notification_msg_id FROM notification_subscriptions WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
    return row[0] if row and row[0] else None


async def set_last_notification_msg_id(user_id: int, message_id: int | None) -> None:
    """Сохраняет message_id последнего отправленного уведомления для последующего удаления."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE notification_subscriptions
            SET last_notification_msg_id = ?
            WHERE user_id = ?
        """, (message_id, user_id))
        await db.commit()




async def get_user_schedule_format(user_id: int) -> str:
    """Возвращает формат отображения расписания для пользователя: 'photo' или 'text'."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT schedule_format FROM user_settings WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()

    if row and row[0]:
        return row[0]
    return "photo"


async def set_user_schedule_format(user_id: int, format_type: str) -> None:
    """Устанавливает формат отображения расписания ('photo' или 'text')."""
    if format_type not in ("photo", "text"):
        format_type = "photo"
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO user_settings (user_id, schedule_format)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET schedule_format = excluded.schedule_format
        """, (user_id, format_type))
        await db.commit()


async def toggle_user_schedule_format(user_id: int) -> str:
    """Переключает формат отображения расписания (photo <-> text) и возвращает новый формат."""
    current = await get_user_schedule_format(user_id)
    new_format = "text" if current == "photo" else "photo"
    await set_user_schedule_format(user_id, new_format)
    return new_format
