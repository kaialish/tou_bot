"""
Модуль парсеров данных портала ToU (фасад для 100% обратной совместимости).
Все реализации вынесены в специализированные модули пакета `src.services.parsers`:
- `schedule_parser.py` — парсинг расписания занятий
- `dates_parser.py`    — парсинг ключевых дат учебного года
- `status_parser.py`   — парсинг академического статуса (GPA, допуски)
- `grades_parser.py`   — парсинг журнала успеваемости, баллов ТУ и РК
"""

from src.services.parsers.schedule_parser import (
    WEEKDAY_MAP,
    parse_schedule_items,
    format_schedule_text,
)
from src.services.parsers.dates_parser import (
    DEFAULT_KEY_DATES,
    get_calculated_key_dates,
    parse_key_dates,
    get_days_declension,
    format_key_dates_message,
)
from src.services.parsers.status_parser import (
    parse_academic_status,
    format_academic_status_message,
)
from src.services.parsers.grades_parser import (
    extract_current_week,
    parse_zhurnal,
    get_zhurnal_part,
    format_zhurnal_brief,
    format_zhurnal_full_chunks,
    _calc_course_real_tu,
    _format_score,
    _get_traffic_light,
    _get_part_week_range,
    _filter_grades_by_current_week,
)

__all__ = [
    "WEEKDAY_MAP",
    "parse_schedule_items",
    "format_schedule_text",
    "DEFAULT_KEY_DATES",
    "get_calculated_key_dates",
    "parse_key_dates",
    "get_days_declension",
    "format_key_dates_message",
    "parse_academic_status",
    "format_academic_status_message",
    "extract_current_week",
    "parse_zhurnal",
    "get_zhurnal_part",
    "format_zhurnal_brief",
    "format_zhurnal_full_chunks",
    "_calc_course_real_tu",
    "_format_score",
    "_get_traffic_light",
    "_get_part_week_range",
    "_filter_grades_by_current_week",
]
