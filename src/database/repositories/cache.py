import aiosqlite
from src.database.schema import DB_NAME

async def save_cached_schedule(user_id: int, schedule_html: str, cached_at: str | None = None) -> None:
    """Сохраняет HTML расписания и время обновления в БД."""
    if not cached_at:
        cached_at = get_kz_now().strftime("%d.%m.%Y в %H:%M")

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO cached_schedules (user_id, schedule_html, cached_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                schedule_html=excluded.schedule_html,
                cached_at=excluded.cached_at
        """, (user_id, schedule_html, cached_at))
        await db.commit()


async def get_cached_schedule(user_id: int) -> tuple[str, str] | None:
    """Возвращает (schedule_html, cached_at) из БД или None, если кэш пуст."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT schedule_html, cached_at FROM cached_schedules WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()

    if not row:
        return None
    return row[0], row[1]


async def save_cached_academic_status(user_id: int, status_json: str, cached_at: str | None = None) -> None:
    """Сохраняет JSON академического статуса и время обновления в БД."""
    if not cached_at:
        cached_at = get_kz_now().strftime("%d.%m.%Y в %H:%M")

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO cached_academic_status (user_id, status_json, cached_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                status_json=excluded.status_json,
                cached_at=excluded.cached_at
        """, (user_id, status_json, cached_at))
        await db.commit()


async def get_cached_academic_status(user_id: int) -> tuple[str, str] | None:
    """Возвращает (status_json, cached_at) из БД или None, если кэш пуст."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT status_json, cached_at FROM cached_academic_status WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()

    if not row:
        return None
    return row[0], row[1]


async def save_cached_zhurnal(user_id: int, zhurnal_json: str, cached_at: str | None = None) -> None:
    """Сохраняет JSON журнала успеваемости и время обновления в БД."""
    if not cached_at:
        cached_at = get_kz_now().strftime("%d.%m.%Y в %H:%M")

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO cached_zhurnal (user_id, zhurnal_json, cached_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                zhurnal_json=excluded.zhurnal_json,
                cached_at=excluded.cached_at
        """, (user_id, zhurnal_json, cached_at))
        await db.commit()


async def get_cached_zhurnal(user_id: int) -> tuple[str, str] | None:
    """Возвращает (zhurnal_json, cached_at) из БД или None, если кэш пуст."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT zhurnal_json, cached_at FROM cached_zhurnal WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()

    if not row:
        return None
    return row[0], row[1]
