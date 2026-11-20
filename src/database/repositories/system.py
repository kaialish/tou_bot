import aiosqlite
from src.database.schema import DB_NAME

async def set_maintenance_status(status: bool) -> None:
    """Устанавливает флаг технического перерыва в БД."""
    val = "1" if status else "0"
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO bot_settings (key, value)
            VALUES ('in_maintenance', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (val,))
        await db.commit()


async def is_maintenance_active() -> bool:
    """Проверяет, был ли бот переведён в режим технического обслуживания."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT value FROM bot_settings WHERE key = 'in_maintenance'") as cursor:
            row = await cursor.fetchone()
    if row and row[0] == "1":
        return True
    return False
