import sqlite3
import os
from cryptography.fernet import Fernet

# Чтение или генерация ключа шифрования
KEY_FILE = "secret.key"
if not os.path.exists(KEY_FILE):
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
else:
    with open(KEY_FILE, "rb") as f:
        key = f.read()

cipher = Fernet(key)
DB_NAME = "users_data.db"


def init_db():
    """Создает таблицу пользователей, если ее еще нет."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            login TEXT NOT NULL,
            encrypted_password TEXT NOT NULL
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