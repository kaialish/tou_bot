import aiosqlite
import os
from datetime import datetime
from pathlib import Path
from cryptography.fernet import Fernet

# Определение путей к директории хранения данных
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

KEY_FILE = DATA_DIR / "secret.key"
DB_NAME = str(DATA_DIR / "users_data.db")

# Чтение или генерация ключа шифрования
if not KEY_FILE.exists():
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
else:
    with open(KEY_FILE, "rb") as f:
        key = f.read()

cipher = Fernet(key)


async def init_db() -> None:
    """Создает таблицы пользователей, настроек, подписок и кэша расписания (асинхронно)."""
    async with aiosqlite.connect(DB_NAME) as db:
        # Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                login TEXT NOT NULL,
                encrypted_password TEXT NOT NULL
            )
        """)

        # Таблица подписок на уведомления об окончании пар
        await db.execute("""
            CREATE TABLE IF NOT EXISTS notification_subscriptions (
                user_id INTEGER PRIMARY KEY,
                is_subscribed INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # Таблица сохранённого расписания на случай сбоев или падения портала ToU
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cached_schedules (
                user_id INTEGER PRIMARY KEY,
                schedule_html TEXT NOT NULL,
                cached_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # Таблица системных настроек и состояний бота
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Таблица пользовательских настроек (вид расписания: 'photo' или 'text')
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                schedule_format TEXT DEFAULT 'photo',
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        await db.commit()


async def save_user_credentials(user_id: int, login: str, password: str) -> None:
    """Шифрует и сохраняет учётные данные пользователя на диск."""
    enc_password = cipher.encrypt(password.encode()).decode()
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO users (user_id, login, encrypted_password)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                login=excluded.login,
                encrypted_password=excluded.encrypted_password
        """, (user_id, login, enc_password))
        await db.commit()


async def get_user_credentials(user_id: int) -> tuple[str, str] | None:
    """Возвращает (login, decrypted_password) из БД или None."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT login, encrypted_password FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()

    if not row:
        return None

    login, enc_password = row
    try:
        decrypted_password = cipher.decrypt(enc_password.encode()).decode()
        return login, decrypted_password
    except Exception:
        return None


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


async def save_cached_schedule(user_id: int, schedule_html: str, cached_at: str | None = None) -> None:
    """Сохраняет HTML расписания и время обновления в БД."""
    if not cached_at:
        cached_at = datetime.now().strftime("%d.%m.%Y в %H:%M")

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