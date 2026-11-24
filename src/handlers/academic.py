import json
from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from src.database import (
    get_user_credentials,
    save_cached_academic_status,
    get_cached_academic_status,
    get_cached_schedule,
    save_cached_schedule,
)
from src.services import (
    get_dashboard_html,
    get_schedule_html,
    parse_key_dates,
    format_key_dates_message,
    parse_academic_status,
    format_academic_status_message,
)
from src.keyboards import (
    get_main_menu_keyboard,
    get_academic_status_keyboard,
)
from src.utils import cleanup_previous_album, check_rate_limit, update_rate_limit
from src.states import AuthForm
from src.config import ADMIN_IDS, get_kz_now

router = Router()

@router.callback_query(F.data == "menu_key_dates")
async def process_menu_key_dates(callback: CallbackQuery, state: FSMContext):
    """Раздел: Ключевые даты."""
    user_data = await state.get_data()
    cached_html = user_data.get("cached_html")

    if not cached_html:
        # Сначала проверяем кэшированное расписание из БД
        db_cached = await get_cached_schedule(callback.from_user.id)
        if db_cached:
            cached_html, cached_at = db_cached
            await state.update_data(cached_html=cached_html, is_offline=True, cached_at=cached_at)
        else:
            login = user_data.get("login")
            password = user_data.get("password")
            if not login or not password:
                creds = await get_user_credentials(callback.from_user.id)
                if creds:
                    login, password = creds
                    await state.update_data(login=login, password=password)
                else:
                    await callback.answer("Сессия истекла. Нажмите /start заново.", show_alert=True)
                    return

            await callback.answer("🔄 Загружаем данные...")
            success, html_or_err = await get_schedule_html(login, password, bot=callback.bot)
            if success:
                cached_html = html_or_err
                now_str = get_kz_now().strftime("%d.%m.%Y в %H:%M")
                await save_cached_schedule(callback.from_user.id, cached_html, now_str)
                await state.update_data(cached_html=cached_html, is_offline=False, cached_at=now_str)
            else:
                retry_kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Повторить попытку", callback_data="menu_key_dates")],
                    [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main_menu")]
                ])
                try:
                    await callback.message.edit_text(html_or_err, parse_mode="HTML", reply_markup=retry_kb)
                except Exception:
                    await callback.message.answer(html_or_err, parse_mode="HTML", reply_markup=retry_kb)
                return

    await cleanup_previous_album(callback.bot, callback.message.chat.id, state)

    dates = parse_key_dates(cached_html)
    text = format_key_dates_message(dates)

    back_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main_menu")]
        ]
    )

    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb)
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=back_kb)


async def _load_and_render_academic_status(callback: CallbackQuery, state: FSMContext, is_refresh: bool = False):
    """Общий обработчик для загрузки и отображения академического статуса."""
    if is_refresh:
        can_refresh, remaining = check_rate_limit(callback.from_user.id, action="status_refresh", cooldown_seconds=60)
        if not can_refresh:
            await callback.answer(f"⏳ Слишком частые запросы к ToU. Подождите ещё {remaining} сек.", show_alert=True)
            return
        update_rate_limit(callback.from_user.id, action="status_refresh")

    await callback.answer("🔄 Загружаем академический статус...")
    await cleanup_previous_album(callback.bot, callback.message.chat.id, state)

    user_data = await state.get_data()
    login = user_data.get("login")
    password = user_data.get("password")

    if not login or not password:
        creds = await get_user_credentials(callback.from_user.id)
        if creds:
            login, db_pw = creds
            password = password or db_pw
            await state.update_data(login=login, password=password)
        else:
            await callback.answer("Сессия истекла. Нажмите /start заново.", show_alert=True)
            return

    # Если пароль не сохранён (режим безопасности), проверяем кэш
    if not password and not is_refresh:
        cached = await get_cached_academic_status(callback.from_user.id)
        if cached:
            status_json, cached_at = cached
            try:
                status_data = json.loads(status_json)
                text = format_academic_status_message(status_data, updated_at=cached_at)
                text += "\n\n🛡️ <i>Вы в режиме максимальной безопасности (без пароля). Отображены сохранённые данные.</i>"
                kb = get_academic_status_keyboard()
                try:
                    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
                except Exception:
                    await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
                return
            except Exception:
                pass

    if not password:
        await callback.answer("Для обновления с портала введите логин и пароль через /start", show_alert=True)
        return

    # Запрашиваем страницу дашборда с портала
    success, html_or_err = await get_dashboard_html(login, password, bot=callback.bot)

    if success:
        status_data = parse_academic_status(html_or_err)
        now_str = get_kz_now().strftime("%d.%m.%Y в %H:%M")
        await save_cached_academic_status(callback.from_user.id, json.dumps(status_data, ensure_ascii=False), now_str)
        text = format_academic_status_message(status_data, updated_at=now_str)
        if is_refresh:
            await callback.answer("✅ Данные обновлены!", show_alert=False)
    else:
        # Проверяем кэш из БД
        cached = await get_cached_academic_status(callback.from_user.id)
        if cached:
            status_json, cached_at = cached
            try:
                status_data = json.loads(status_json)
                text = format_academic_status_message(status_data, updated_at=cached_at)
                text += "\n\n⚠️ <i>Отображены сохранённые данные (портал временно недоступен).</i>"
            except Exception:
                text = f"{html_or_err}\n\n<i>Кэш академического статуса повреждён. Попробуйте позже.</i>"
        else:
            text = html_or_err

    kb = get_academic_status_keyboard()

    if is_refresh:
        # При нажатии "Обновить" удаляем старое сообщение и отправляем свежее
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        # При первом входе из меню пробуем изменить текст на месте
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except TelegramBadRequest as e:
            if "message is not modified" in str(e).lower():
                pass
            else:
                try:
                    await callback.message.delete()
                except Exception:
                    pass
                await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data == "menu_academic_status")
async def process_menu_academic_status(callback: CallbackQuery, state: FSMContext):
    """Раздел: Академический статус."""
    await _load_and_render_academic_status(callback, state, is_refresh=False)


@router.callback_query(F.data == "refresh_academic_status")
async def process_refresh_academic_status(callback: CallbackQuery, state: FSMContext):
    """Обновление раздела Академический статус."""
    await _load_and_render_academic_status(callback, state, is_refresh=True)
