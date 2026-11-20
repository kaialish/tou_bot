import os
import sys
from pathlib import Path
from cryptography.fernet import Fernet
from src.config import DATA_DIR

KEY_FILE = DATA_DIR / "secret.key"

# Чтение или генерация ключа шифрования:
# 1. Сначала проверяем переменную окружения SECRET_KEY (рекомендуется для Railway / хостинга)
# 2. На Windows при отсутствии в env пробуем прочитать из реестра пользователя HKCU\Environment
# 3. Если переменной нет, читаем из файла KEY_FILE на диске (для обратной совместимости)
# 4. Если файла нет, генерируем новый и пробуем сохранить
env_secret_key = os.getenv("SECRET_KEY", "").strip()

if not env_secret_key and sys.platform == "win32":
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as reg_key:
            reg_val, _ = winreg.QueryValueEx(reg_key, "SECRET_KEY")
            if reg_val:
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

__all__ = ["cipher", "KEY_FILE"]
