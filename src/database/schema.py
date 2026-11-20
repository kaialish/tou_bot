import aiosqlite
from src.config import DATA_DIR

DB_NAME = str(DATA_DIR / "users_data.db")

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



__all__ = ["DB_NAME", "init_db"]
