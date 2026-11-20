import json
from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from src.database import (
    get_user_credentials,
    save_cached_zhurnal,
    get_cached_zhurnal,
)
from src.services import (
    get_zhurnal_html,
    parse_zhurnal,
    get_zhurnal_part,
    format_zhurnal_brief,
    format_zhurnal_full_chunks,
)
from src.keyboards import (
    get_main_menu_keyboard,
    get_grades_keyboard,
)
from src.utils import cleanup_previous_album, check_rate_limit, update_rate_limit
from src.states import AuthForm
from src.config import ADMIN_IDS

router = Router()

async def _cleanup_grades_messages(bot, chat_id: int, state: FSMContext) -> None:
    """Удаляет предыдущие сообщения полного журнала при переключении."""
    user_data = await state.get_data()
    msg_ids = user_data.get("grades_msg_ids", [])
    for mid in msg_ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=mid)
        except Exception:
            pass
    await state.update_data(grades_msg_ids=[])


async def _load_and_render_grades(
    callback: CallbackQuery, state: FSMContext, is_refresh: bool = False,
    view: str | None = None, part: int | None = None,
) -> None:
    """Загружает данные журнала успеваемости и отображает их пользователю."""
    user_data = await state.get_data()
    view = view or user_data.get("grades_view", "brief")
    part = part if part is not None else user_data.get("grades_part")
    login = user_data.get("login")
    password = user_data.get("password")

    # Если в стейте нет логина/пароля, достаем из БД
    if not login or not password:
        creds = await get_user_credentials(callback.from_user.id)
        if not creds:
            await callback.answer("⚠️ Вы не авторизованы. Отправьте /start", show_alert=True)
            return
        login, db_pw = creds
        password = password or db_pw
        await state.update_data(login=login, password=password)

    if is_refresh:
        can_refresh, remaining = check_rate_limit(callback.from_user.id, action="grades_refresh", cooldown_seconds=60)
        if not can_refresh:
            await callback.answer(f"⏳ Слишком частые запросы к ToU. Подождите ещё {remaining} сек.", show_alert=True)
            return
        update_rate_limit(callback.from_user.id, action="grades_refresh")

    await callback.answer()
    courses = None
    cached_at = ""

    # Если это не переключение вида при уже загруженном журнале — проверяем/запрашиваем
    cached_courses_json = user_data.get("cached_zhurnal_json")
    cached_courses_time = user_data.get("cached_zhurnal_time")

    if cached_courses_json and not is_refresh:
        try:
            courses = json.loads(cached_courses_json)
            cached_at = cached_courses_time or ""
        except Exception:
            courses = None

    if (courses is None or is_refresh) and not password:
        # Режим без сохранения пароля: пробуем взять сохранённый кэш из БД
        db_cached = await get_cached_zhurnal(callback.from_user.id)
        if db_cached:
            try:
                courses = json.loads(db_cached[0])
                cached_at = f"{db_cached[1]} (сохранено)"
            except Exception:
                courses = None
        if not courses:
            await callback.answer("Для загрузки журнала требуется пароль. Отправьте /start для обновления.", show_alert=True)
            return

    elif courses is None or is_refresh:
        success, html_or_err = await get_zhurnal_html(login, password, bot=callback.bot)

        if success:
            courses = parse_zhurnal(html_or_err)
            now_str = get_kz_now().strftime("%d.%m.%Y в %H:%M")
            cached_at = now_str
            courses_json = json.dumps(courses, ensure_ascii=False)
            await state.update_data(cached_zhurnal_json=courses_json, cached_zhurnal_time=now_str)
            await save_cached_zhurnal(callback.from_user.id, courses_json, now_str)
        else:
            # Пробуем достать кэш из БД
            db_cached = await get_cached_zhurnal(callback.from_user.id)
            if db_cached:
                try:
                    courses = json.loads(db_cached[0])
                    cached_at = f"{db_cached[1]} (кэш)"
                except Exception:
                    courses = None

            if not courses:
                # Ошибка и нет кэша
                try:
                    await callback.message.edit_text(html_or_err, parse_mode="HTML", reply_markup=get_grades_keyboard(view, part or 1))
                except Exception:
                    await callback.message.answer(html_or_err, parse_mode="HTML", reply_markup=get_grades_keyboard(view, part or 1))
                return

    # Очищаем старые сообщения полного журнала если были
    await _cleanup_grades_messages(callback.bot, callback.message.chat.id, state)

    part = get_zhurnal_part(courses) if part is None else part
    await state.update_data(grades_part=part, grades_view=view)
    kb = get_grades_keyboard(view, part)

    if view == "brief":
        text = format_zhurnal_brief(courses, updated_at=cached_at, part=part)
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
            await state.update_data(grades_msg_ids=[callback.message.message_id])
        except TelegramBadRequest as e:
            if "message is not modified" in str(e).lower():
                await state.update_data(grades_msg_ids=[callback.message.message_id])
            else:
                try:
                    await callback.message.delete()
                except Exception:
                    pass
                sent = await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
                await state.update_data(grades_msg_ids=[sent.message_id])
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            sent = await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
            await state.update_data(grades_msg_ids=[sent.message_id])
    else:
        # view == "full"
        chunks = format_zhurnal_full_chunks(courses, updated_at=cached_at, part=part)
        # Удаляем предыдущее меню/сообщение
        try:
            await callback.message.delete()
        except Exception:
            pass

        sent_ids = []
        for idx, chunk in enumerate(chunks):
            # Кнопки прикрепляем только к последнему сообщению
            reply_markup = kb if idx == len(chunks) - 1 else None
            sent = await callback.message.answer(chunk, parse_mode="HTML", reply_markup=reply_markup)
            sent_ids.append(sent.message_id)

        await state.update_data(grades_msg_ids=sent_ids)


@router.callback_query(F.data == "menu_grades")
async def process_menu_grades(callback: CallbackQuery, state: FSMContext):
    """Раздел: Успеваемость (краткий вид по умолчанию)."""
    await state.update_data(grades_part=None)
    await _load_and_render_grades(callback, state, is_refresh=False, view="brief")


@router.callback_query(F.data == "refresh_grades")
async def process_refresh_grades(callback: CallbackQuery, state: FSMContext):
    """Обновление журнала успеваемости."""
    await _load_and_render_grades(callback, state, is_refresh=True)


@router.callback_query(F.data == "grades_view_full")
async def process_grades_view_full(callback: CallbackQuery, state: FSMContext):
    """Переключение на полный вид журнала успеваемости."""
    await _load_and_render_grades(callback, state, is_refresh=False, view="full")


@router.callback_query(F.data == "grades_view_brief")
async def process_grades_view_brief(callback: CallbackQuery, state: FSMContext):
    """Переключение на краткий вид журнала успеваемости."""
    await _load_and_render_grades(callback, state, is_refresh=False, view="brief")


@router.callback_query(F.data.in_({"grades_part_1", "grades_part_2"}))
async def process_grades_part(callback: CallbackQuery, state: FSMContext):
    """Переключение части с сохранением краткого или полного вида."""
    await _load_and_render_grades(callback, state, part=int(callback.data.rsplit("_", 1)[1]))
