import asyncio
from aiogram import Bot
from aiogram.fsm.context import FSMContext


async def cleanup_previous_album(bot: Bot, chat_id: int, state: FSMContext) -> None:
    """
    Удаляет предыдущие сообщения из чата:
    - медиагруппу альбома (week_album_ids) + навигационное сообщение (week_nav_id)
    - одиночное фото расписания (schedule_photo_id) — Сегодня / Завтра
    - текстовое сообщение расписания (schedule_text_id)
    Очищает связанные ID в FSMContext.
    """
    user_data = await state.get_data()
    prev_album_ids: list[int] = user_data.get("week_album_ids", [])
    prev_nav_id: int | None = user_data.get("week_nav_id")
    schedule_photo_id: int | None = user_data.get("schedule_photo_id")
    schedule_text_id: int | None = user_data.get("schedule_text_id")
    grades_msg_ids: list[int] = user_data.get("grades_msg_ids", [])

    # Удаляем сообщения журнала успеваемости (если были)
    if grades_msg_ids:
        for mid in grades_msg_ids:
            try:
                await bot.delete_message(chat_id, mid)
            except Exception:
                pass
        await state.update_data(grades_msg_ids=[])

    # Удаляем альбом недели
    if prev_album_ids:
        for msg_id in prev_album_ids:
            try:
                await bot.delete_message(chat_id, msg_id)
            except Exception:
                pass
        if prev_nav_id:
            try:
                await bot.delete_message(chat_id, prev_nav_id)
            except Exception:
                pass
        await state.update_data(week_album_ids=[], week_nav_id=None)

    # Удаляем одиночное фото расписания (Сегодня / Завтра)
    if schedule_photo_id:
        try:
            await bot.delete_message(chat_id, schedule_photo_id)
        except Exception:
            pass
        await state.update_data(schedule_photo_id=None)

    # Удаляем текстовое сообщение расписания (если есть)
    if schedule_text_id:
        try:
            await bot.delete_message(chat_id, schedule_text_id)
        except Exception:
            pass
        await state.update_data(schedule_text_id=None)


async def clear_chat_history(bot: Bot, chat_id: int, current_msg_id: int, count: int = 2000) -> None:
    """
    Очищает до `count` сообщений в чате (по умолчанию 2000 сообщений — весь чат).
    Удаление идёт в обратном порядке (от самых свежих сообщений к более старым).
    Сначала пытается удалить пачками по 100 через delete_messages.
    При ошибке пачки (например, наличие старого сообщения пользователя >48ч)
    удаляет остальные доступные сообщения пачки параллельно.
    """
    start_id = max(1, current_msg_id - count)
    all_ids = list(range(current_msg_id, start_id - 1, -1))

    sem = asyncio.Semaphore(20)

    async def _safe_delete(mid: int) -> None:
        async with sem:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=mid)
            except Exception:
                pass

    # Telegram API delete_messages принимает максимум 100 ID за один запрос
    for i in range(0, len(all_ids), 100):
        chunk = all_ids[i:i + 100]
        try:
            await bot.delete_messages(chat_id=chat_id, message_ids=chunk)
        except Exception:
            tasks = [_safe_delete(mid) for mid in chunk]
            await asyncio.gather(*tasks, return_exceptions=True)

