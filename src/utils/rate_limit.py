"""
Модуль ограничения частоты сетевых запросов к порталу университета (Rate Limiting).
Защищает ToU (tou.edu.kz) от избыточных запросов и предотвращает блокировку IP-адреса бота.
"""
import time
from typing import Dict, Tuple

# Хранилище времени последних запросов в памяти: {(user_id, action): timestamp}
_USER_LAST_REQUEST: Dict[Tuple[int, str], float] = {}

# Стандартный кулдаун (в секундах) между сетевыми обновлениями для одного студента
DEFAULT_COOLDOWN_SECONDS = 60


def check_rate_limit(
    user_id: int,
    action: str = "refresh",
    cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS,
) -> Tuple[bool, int]:
    """
    Проверяет, прошло ли достаточно времени с момента последнего сетевого запроса.
    
    :param user_id: Telegram ID пользователя
    :param action: Тип действия ('refresh', 'grades', 'status', 'schedule')
    :param cooldown_seconds: Необходимый интервал ожидания в секундах
    :return: (can_proceed: bool, remaining_seconds: int)
    """
    now = time.time()
    key = (user_id, action)
    last_time = _USER_LAST_REQUEST.get(key, 0.0)
    elapsed = now - last_time

    if elapsed < cooldown_seconds:
        remaining = int(cooldown_seconds - elapsed) + 1
        return False, remaining

    return True, 0


def update_rate_limit(user_id: int, action: str = "refresh") -> None:
    """
    Фиксирует время выполнения сетевого запроса к порталу.
    """
    _USER_LAST_REQUEST[(user_id, action)] = time.time()


def format_cooldown_message(remaining_seconds: int) -> str:
    """
    Возвращает понятное пользователю сообщение об активном кулдауне.
    """
    return (
        f"⏳ Слишком частые запросы к порталу ToU.\n"
        f"Пожалуйста, подождите ещё {remaining_seconds} сек."
    )
