# ToU Bot — Карта проекта

> Telegram-бот для просмотра расписания студентов Торайгыров Университета.

---

## 📁 Структура проекта (модульная архитектура)

```
tou_bot/
├── bot.py                  ← Точка входа (Bot, Dispatcher, main_router)
├── data/                   ← Защищённое хранилище (БД SQLite, ключ Fernet)
├── src/
│   ├── config.py           ← Настройки, переменные окружения, URL-константы
│   ├── database/           ← Слой БД (db.py, шифрование credentials)
│   ├── states/             ← FSM-состояния (AuthForm, AdminState)
│   ├── keyboards/          ← Клавиатуры (inline.py)
│   ├── services/           ← Сервисы (tou_client, parser, image_generator)
│   ├── handlers/           ← Aiogram-роутеры (auth, schedule, admin, common)
│   └── utils/              ← Утилиты и тексты (texts.py, cleanup.py)
├── requirements.txt        ← Зависимости
└── .venv/                  ← Виртуальное окружение
```

---

## 🔄 Поток данных

```
Telegram → bot.py → tou_client.py → portal ToU (HTTPS)
                                          ↓ HTML (mod=rasp)
                        parser.py  ← HTML расписания
                             ↓ list[dict]
                    image_generator.py → PNG bytes
                             ↓
               bot.py → edit_media → Telegram (фото обновляется)
```

---

## 📄 Файлы и их роли

### `bot.py`
Главный файл. Содержит aiogram-хендлеры.

| Хендлер | Триггер | Действие |
|---------|---------|----------|
| `cmd_start` | `/start` | Запрашивает логин |
| `process_login` | Состояние `waiting_for_login` | Запрашивает пароль |
| `process_password` | Состояние `waiting_for_password` | Авторизация + первое расписание |
| `process_schedule_day` | Callback `sched_today/tomorrow/week` | Обновляет расписание по кнопке |

---

### `config.py`
Хранит константы. Не содержит логики.

```python
BOT_TOKEN     = "..."
LOGIN_URL     = "https://tou.edu.kz/student_cabinet/index.php?lang=rus"
SCHEDULE_URL  = "https://tou.edu.kz/student_cabinet/index.php?lang=rus&mod=rasp"  # ← НОВОЕ
DASHBOARD_URL = "..."  # устарел, оставлен для совместимости
```

---

### `tou_client.py`
Один клиентский метод. Создаёт `httpx.AsyncClient` (сессия с cookies),
делает POST-логин → GET расписания → возвращает `(success: bool, html: str)`.

```python
async def get_schedule_html(login, password) -> tuple[bool, str]
```

Сохраняет `debug_schedule.html` для отладки.

---

### `parser.py`
Парсит HTML-таблицу расписания. Публичный интерфейс — одна функция:

```python
def parse_schedule_items(html: str, day: str) -> list[dict]
# day: "today" | "tomorrow" | "week"
```

Каждый элемент списка:
```python
{
    "day":     "Понедельник",           # название дня недели
    "time":    "08:15-09:05",           # время занятия
    "subject": "Компьютерные сети",     # название предмета
    "type":    "лек.",                  # тип: лек. / пр./сем. / лаб.
    "room":    "А-7",                   # аудитория
    "teacher": "ст.преп. Самуратов А.Т.",  # преподаватель
}
```

---

### `image_generator.py`
Генерирует PNG-изображение расписания. Публичный интерфейс:

```python
def generate_schedule_image(schedule_data: list[dict], title: str) -> bytes
```

Внутренние функции:

| Функция | Назначение |
|---------|------------|
| `_generate_day_image` | PNG для одного дня |
| `_generate_week_image` | PNG с секциями по дням |
| `_draw_lesson_card` | Одна карточка занятия |
| `_draw_main_header` | Шапка изображения |
| `_load_fonts` | Загрузка шрифтов (fallback на дефолтные) |

---

## ✅ Изменения по сравнению с исходным кодом

### 1. `parser.py` — **Полный рефакторинг**

**Было (исходный код):**
- Парсил `data-schedule-panel` дивы (`today`, `tomorrow`, `week`) из дашборда
- Для `week`: разбирал плоский текст по строкам через regex (даты, счётчики пар, время)
- Для `today/tomorrow`: искал строки по формату `HH:MM`
- Не знал о преподавателях и типах занятий

**Стало:**
- Парсит `<table class="schedule-table">` — реальную HTML-таблицу из `mod=rasp`
- Каждая строка `<tr>` → ячейки `sc-day`, `sc-time`, `sc-body`
- Из `<span class="sc-dis">` извлекает **предмет** и **тип занятия**
- Из `<span class="sc-meta">` извлекает **аудиторию** и **преподавателя**
- Обрабатывает блоки **числитель/знаменатель** (`sc-cz-block--muted` — неактивный, пропускается)
- Фильтрация `today/tomorrow` по дню недели через `datetime.now().weekday()`

---

### 2. `config.py` — Новый URL

**Добавлено:**
```python
SCHEDULE_URL = "https://tou.edu.kz/student_cabinet/index.php?lang=rus&mod=rasp"
```

**Причина:** дашборд (`mod=dashboard`) не содержит структурированной таблицы расписания.

---

### 3. `tou_client.py` — Смена URL и функция

**Было:**
```python
async def get_dashboard_html(login, password) → (bool, str)
# GET → mod=dashboard
# Проверка: "student-card--schedule" in html
```

**Стало:**
```python
async def get_schedule_html(login, password) → (bool, str)
# GET → mod=rasp (SCHEDULE_URL)
# Проверка: "schedule-table" in html
# Отладка: debug_schedule.html (вместо debug.html)
```

---

### 4. `image_generator.py` — Преподаватель + недельный рендер

**`_draw_lesson_card` — добавлен преподаватель:**

| До | После |
|----|-------|
| `Аудитория: А-7` | `А-7  ·  ст.преп. Самуратов А. Т.` |

**`_generate_week_image` — исправлен рендер дней:**

- **Было:** поле `"day"` содержало дату `"28.09.2026"`, заголовок секции показывал дату
- **Стало:** `datetime.strptime` конвертирует дату → `"Понедельник, 28.09"`
- После рефакторинга парсера: `"day"` теперь содержит `"Понедельник"` напрямую из HTML — конвертация больше не нужна

---

### 5. `bot.py` — Кнопки обновляют фото (не создают новое)

**Было:**
```python
await callback.message.answer_photo(photo=photo, ...)  # новое сообщение каждый раз
```

**Стало:**
```python
await callback.message.edit_media(
    media=InputMediaPhoto(media=photo, caption=..., parse_mode="Markdown"),
    reply_markup=get_schedule_keyboard()
)
# Fallback → answer_photo если сообщение нельзя редактировать
```

**Также:** добавлен импорт `InputMediaPhoto`.

---

## 🐛 Известные ограничения

| Проблема | Статус |
|----------|--------|
| Сетевые ошибки Telegram (`ServerDisconnectedError`) | Требуется настройка proxy в `bot.py` |
| `"Завтра"` на выходных — показывает пустое расписание | Ожидаемое поведение (нет занятий) |
| Длинные названия предметов обрезаются (`[:36]`) | Допустимо, PNG ограничен шириной |
| Страница расписания показывает только текущую неделю | Для следующей недели нужен доп. параметр `week_nom` |

---

## 📜 История версий

- **v0.1.0** — 25.09.2026: Первичная реализация. Парсинг dashboard, генерация изображений.
- **v0.2.0** — 26.09.2026: Рефакторинг под mod=rasp (HTML-таблица), преподаватель в карточке, база данных SQLite + панель администратора.
- **v0.3.0** — 28.09.2026: Альбомный режим недельного расписания (5 PNG -> media group).
- **v0.3.1** — 28.09.2026: Отображение даты каждого дня недели в карточках и подписях альбома + оптимизация PNG.
- **v0.4.0** — 28.09.2026: Модульная архитектура (пакет `src/`: handlers, services, database, keyboards, data/).
- **v0.4.1** — 28.09.2026: Завершение декомпозиции (`src/states/`, `src/utils/`), исправление утечки сообщений альбома, поддержка Visual Studio (`tou_bot.pyproj`), `.env.example`.
- **v0.5.0** — 29.09.2026: Оффлайн-кэш расписания в SQLite при падении портала ToU с указанием времени последнего обновления, кнопка «🔄 Обновить», автономный вход в систему.
- **v0.6.0** — 30.09.2026: 
  - Полный переход базы данных на асинхронный **aiosqlite** (ликвидация блокировок Event Loop).
  - Система мониторинга и алертов для администраторов (`src/services/admin_alerts.py`): запуск/остановка бота, отслеживание падений/восстановления портала ToU, глобальный перехватчик исключений с уведомлениями админов.
  - Оптимизация производительности: добавлен быстрый **текстовый режим расписания** (без нагрузки на CPU и Pillow, экономия трафика), тумблер переключения формата прямо в карточке расписания и в новом разделе «⚙️ Настройки».
  - Поддержка очистки текстовых сообщений расписания в `cleanup_previous_album`.


