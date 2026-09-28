from aiogram import Bot
from aiogram.fsm.context import FSMContext


async def cleanup_previous_album(bot: Bot, chat_id: int, state: FSMContext) -> None:
    """
    Удаляет предыдущие сообщения медиагруппы (альбома на неделю) и навигации из чата.
    Очищает связанные ID в FSMContext.
    """
    user_data = await state.get_data()
    prev_album_ids: list[int] = user_data.get("week_album_ids", [])
    prev_nav_id: int | None = user_data.get("week_nav_id")

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
