import aiosqlite
from src.database.schema import DB_NAME
from src.database.crypto import cipher

async def save_user_credentials(user_id: int, login: str, password: str, save_password: bool = True) -> None:
    """Шифрует и сохраняет учётные данные пользователя на диск (или только логин в защищённом режиме)."""
    enc_password = cipher.encrypt(password.encode()).decode() if (save_password and password) else ""
    save_flag = 1 if (save_password and password) else 0
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO users (user_id, login, encrypted_password, save_password)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                login=excluded.login,
                encrypted_password=excluded.encrypted_password,
                save_password=excluded.save_password
        """, (user_id, login, enc_password, save_flag))
        await db.commit()


async def get_user_credentials(user_id: int) -> tuple[str, str | None] | None:
    """Возвращает (login, decrypted_password_or_None) из БД или None."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT login, encrypted_password, COALESCE(save_password, 1) FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()

    if not row:
        return None

    login, enc_password, save_flag = row
    if not save_flag or not enc_password:
        return login, None

    try:
        decrypted_password = cipher.decrypt(enc_password.encode()).decode()
        return login, decrypted_password
    except Exception:
        return login, None


async def is_user_password_saved(user_id: int) -> bool:
    """Проверяет, сохранён ли пароль пользователя в базе данных."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT COALESCE(save_password, 1), encrypted_password FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
    if not row:
        return False
    save_flag, enc_pw = row
    return bool(save_flag and enc_pw)


async def delete_user_account(user_id: int) -> bool:
    """Полностью и безвозвратно стирает все данные пользователя из всех таблиц базы."""
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            await db.execute("DELETE FROM notification_subscriptions WHERE user_id = ?", (user_id,))
            await db.execute("DELETE FROM cached_schedules WHERE user_id = ?", (user_id,))
            await db.execute("DELETE FROM cached_academic_status WHERE user_id = ?", (user_id,))
            await db.execute("DELETE FROM cached_zhurnal WHERE user_id = ?", (user_id,))
            await db.execute("DELETE FROM user_settings WHERE user_id = ?", (user_id,))
            await db.commit()
        return True
    except Exception as e:
        print(f"Ошибка при удалении аккаунта пользователя {user_id}: {e}")
        return False


async def get_users_stats() -> tuple[int, list[str]]:
    """Возвращает количество пользователей и список их логинов."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT login FROM users") as cursor:
            rows = await cursor.fetchall()

    logins = [row[0] for row in rows]
    return len(logins), logins


async def get_all_user_ids() -> list[int]:
    """Возвращает список всех user_id для рассылки."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
    return [row[0] for row in rows]
