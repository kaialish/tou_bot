import aiosqlite
import os
import sys
from datetime import datetime
from pathlib import Path
from cryptography.fernet import Fernet
from src.config import DATA_DIR, get_kz_now

KEY_FILE = DATA_DIR / "secret.key"
DB_NAME = str(DATA_DIR / "users_data.db")

# Чтение или генерация ключа шифрования:
# 1. Сначала проверяем переменную окружения SECRET_KEY (рекомендуется для Railway / хостинга)
# 2. На Windows при отсутствии в env пробуем прочитать из реестра пользователя HKCU\Environment
# 3. Если переменной нет, читаем из файла KEY_FILE на диске (для обратной совместимости)
# 4. Если файла нет, генерируем новый и пробуем сохранить
env_secret_key = os.getenv("SECRET_KEY", "").strip()
if not env_secret_key and sys.platform == "win32":
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as rkey:
            reg_val, _ = winreg.QueryValueEx(rkey, "SECRET_KEY")
            env_secret_key = str(reg_val).strip()
    except Exception:
        pass

if env_secret_key:
    key = env_secret_key.encode()
elif KEY_FILE.exists():
    with open(KEY_FILE, "rb") as f:
        key = f.read().strip()
else:
    key = Fernet.generate_key()
    try:
        with open(KEY_FILE, "wb") as f:
            f.write(key)
    except Exception:
        pass

cipher = Fernet(key)


async def init_db() -> None:
    """Создает таблицы пользователей, настроек, подписок и кэша расписания (асинхронно)."""
    async with aiosqlite.connect(DB_NAME) as db:
        # Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                login TEXT NOT NULL,
                encrypted_password TEXT NOT NULL,
                save_password INTEGER DEFAULT 1
            )
        """)

        try:
            await db.execute("ALTER TABLE users ADD COLUMN save_password INTEGER DEFAULT 1")
        except Exception:
            pass

        # Таблица подписок на уведомления об окончании пар
        await db.execute("""
            CREATE TABLE IF NOT EXISTS notification_subscriptions (
                user_id INTEGER PRIMARY KEY,
                is_subscribed INTEGER DEFAULT 1,
                notify_mook INTEGER DEFAULT 0,
                last_notification_msg_id INTEGER DEFAULT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # Безопасная миграция колонок для существующих баз данных
        try:
            await db.execute("ALTER TABLE notification_subscriptions ADD COLUMN notify_mook INTEGER DEFAULT 0")
        except Exception:
            pass

        try:
            await db.execute("ALTER TABLE notification_subscriptions ADD COLUMN last_notification_msg_id INTEGER DEFAULT NULL")
        except Exception:
            pass

        # Таблица сохранённого расписания на случай сбоев или падения портала ToU
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cached_schedules (
                user_id INTEGER PRIMARY KEY,
                schedule_html TEXT NOT NULL,
                cached_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # Таблица сохранённого академического статуса
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cached_academic_status (
                user_id INTEGER PRIMARY KEY,
                status_json TEXT NOT NULL,
                cached_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # Таблица сохранённого журнала успеваемости
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cached_zhurnal (
                user_id INTEGER PRIMARY KEY,
                zhurnal_json TEXT NOT NULL,
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