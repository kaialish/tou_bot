import sqlite3
import os
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


def init_db():
    """Создает табицы пользователей и подписок, если их еще нет."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            login TEXT NOT NULL,
            encrypted_password TEXT NOT NULL
        )
    """)

    # Таблица подписок на уведомления об окончании пар
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notification_subscriptions (
            user_id INTEGER PRIMARY KEY,
            is_subscribed INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    conn.commit()
    conn.close()


def save_user_credentials(user_id: int, login: str, password: str):
    """Шифрует и сохраняет учётные данные пользователя на диск."""
    enc_password = cipher.encrypt(password.encode()).decode()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (user_id, login, encrypted_password)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            login=excluded.login,
            encrypted_password=excluded.encrypted_password
    """, (user_id, login, enc_password))
    conn.commit()
    conn.close()


def get_user_credentials(user_id: int) -> tuple[str, str] | None:
    """Возвращает (login, decrypted_password) из БД или None."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT login, encrypted_password FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    login, enc_password = row
    try:
        decrypted_password = cipher.decrypt(enc_password.encode()).decode()
        return login, decrypted_password
    except Exception:
        return None


def get_users_stats() -> tuple[int, list[str]]:
    """Возвращает количество пользователей и список их логинов."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT login FROM users")
    rows = cursor.fetchall()
    conn.close()

    logins = [row[0] for row in rows]
    return len(logins), logins


def get_all_user_ids() -> list[int]:
    """Возвращает список всех user_id для админ-рассылки."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


def subscribe_to_notifications(user_id: int) -> bool:
    """Подписывает пользователя на уведомления об окончании пар. Возвращает True если успешно."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO notification_subscriptions (user_id, is_subscribed)
            VALUES (?, 1)
        """, (user_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Ошибка при подписке: {e}")
        conn.close()
        return False


def unsubscribe_from_notifications(user_id: int) -> bool:
    """Отписывает пользователя от уведомлений об окончании пар. Возвращает True если успешно."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO notification_subscriptions (user_id, is_subscribed)
            VALUES (?, 0)
        """, (user_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Ошибка при отписке: {e}")
        conn.close()
        return False


def is_user_subscribed(user_id: int) -> bool:
    """Проверяет, подписан ли пользователь на уведомления."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT is_subscribed FROM notification_subscriptions WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    return bool(row and row[0])


def get_subscribed_users() -> list[int]:
    """Возвращает список user_id пользователей, подписанных на уведомления."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id FROM notification_subscriptions WHERE is_subscribed = 1
    """)
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]