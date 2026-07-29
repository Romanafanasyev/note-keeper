import datetime as dt

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.core.config import config
from bot.core.db import SessionLocal
from bot.handlers.states import EditEvent
from bot.keyboards.planner import (
    calendar_kb,
    cancel_kb,
    date_shortcuts_kb,
    task_actions_kb,
    time_kb,
)
from bot.repositories.task_repo import TaskRepo
from bot.services.task_service import TaskService
from bot.services.updater import try_update_posts
from bot.utils.presentation import task_card_text, task_local_datetime
from bot.utils.utils import (
    local_schedule_to_utc,
    parse_id_or_reply,
    parse_time_input,
)

router = Router()


def _parse_action(data: str) -> tuple[int, str, int]:
    _, _, raw_id, list_filter, raw_page = data.split(":", 4)
    return int(raw_id), list_filter, int(raw_page)


def _load_task(task_id: int):
    with SessionLocal() as db_session:
        return TaskService(TaskRepo(db_session)).get_task(task_id)


async def _show_task(
    message: types.Message,
    task_id: int,
    list_filter: str,
    page: int,
    *,
    prefix: str = "",
    edit_message: bool,
) -> None:
    task = _load_task(task_id)
    if task is None:
        text = "Этот план уже удалён."
        markup = None
    else:
        text = task_card_text(task, prefix=prefix)
        markup = task_actions_kb(
            task.id,
            list_filter=list_filter,
            page=page,
        )

    if edit_message:
        await message.edit_text(text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)


async def _store_context(
    state: FSMContext,
    task_id: int,
    list_filter: str,
    page: int,
) -> None:
    await state.clear()
    await state.update_data(
        task_id=task_id,
        list_filter=list_filter,
        page=page,
    )


@router.message(Command("edit"))
async def cmd_edit(msg: types.Message):
    task_id = parse_id_or_reply(msg)
    if not task_id:
        await msg.answer(
            "Открой «📋 Мои планы» и выбери нужный план. "
            "Либо укажи ID: <code>/edit 3</code>."
        )
        return
    await _show_task(
        msg,
        task_id,
        "all",
        0,
        edit_message=False,
    )


@router.message(Command("del"))
async def cmd_delete(msg: types.Message):
    task_id = parse_id_or_reply(msg)
    if not task_id:
        await msg.answer(
            "Открой «📋 Мои планы» и выбери нужный план. "
            "Либо укажи ID: <code>/del 3</code>."
        )
        return
    task = _load_task(task_id)
    if task is None:
        await msg.answer("План не найден или уже удалён.")
        return
    markup = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Да, удалить",
                    callback_data=f"task:delete_yes:{task_id}:all:0",
                ),
                types.InlineKeyboardButton(
                    text="Нет",
                    callback_data=f"task:view:{task_id}:all:0",
                ),
            ]
        ]
    )
    await msg.answer(
        task_card_text(task, prefix="Точно удалить?"),
        reply_markup=markup,
    )


@router.callback_query(F.data.startswith("task:title:"))
async def edit_title_start(cb: types.CallbackQuery, state: FSMContext):
    try:
        task_id, list_filter, page = _parse_action(cb.data)
    except (AttributeError, TypeError, ValueError):
        await cb.answer("Некорректная кнопка.", show_alert=True)
        return
    if _load_task(task_id) is None:
        await cb.answer("План уже удалён.", show_alert=True)
        return

    await _store_context(state, task_id, list_filter, page)
    await state.set_state(EditEvent.title)
    await cb.message.edit_text(
        "Напиши новое название:",
        reply_markup=cancel_kb("edit"),
    )
    await cb.answer()


@router.message(EditEvent.title, Command("cancel"))
@router.message(EditEvent.title, F.text.casefold() == "отмена")
@router.message(EditEvent.date, Command("cancel"))
@router.message(EditEvent.date, F.text.casefold() == "отмена")
@router.message(EditEvent.time, Command("cancel"))
@router.message(EditEvent.time, F.text.casefold() == "отмена")
@router.message(EditEvent.custom_time, Command("cancel"))
@router.message(EditEvent.custom_time, F.text.casefold() == "отмена")
async def cancel_edit_message(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    await _show_task(
        msg,
        data.get("task_id", 0),
        data.get("list_filter", "all"),
        data.get("page", 0),
        prefix="Изменение отменено",
        edit_message=False,
    )


@router.callback_query(F.data == "edit:cancel")
async def cancel_edit_callback(cb: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    await _show_task(
        cb.message,
        data.get("task_id", 0),
        data.get("list_filter", "all"),
        data.get("page", 0),
        prefix="Изменение отменено",
        edit_message=True,
    )
    await cb.answer()


@router.message(
    EditEvent.title,
    ~F.text.startswith("/"),
    ~F.text.in_({"➕ Новое событие", "📋 Мои планы"}),
)
async def edit_title_save(msg: types.Message, state: FSMContext):
    title = (msg.text or "").strip()
    if not title or len(title) > 120:
        await msg.answer(
            "Название должно содержать от 1 до 120 символов.",
            reply_markup=cancel_kb("edit"),
        )
        return

    data = await state.get_data()
    with SessionLocal() as db_session:
        try:
            TaskService(TaskRepo(db_session)).update_title(
                data["task_id"],
                title,
            )
        except (KeyError, ValueError):
            await state.clear()
            await msg.answer("Не удалось найти план.")
            return

    await state.clear()
    channel_updated = await try_update_posts(msg.bot)
    prefix = "✅ Название изменено"
    if not channel_updated:
        prefix += "\n⚠️ Канал обновится позже"
    await _show_task(
        msg,
        data["task_id"],
        data["list_filter"],
        data["page"],
        prefix=prefix,
        edit_message=False,
    )


@router.callback_query(F.data.startswith("task:date:"))
async def edit_date_start(cb: types.CallbackQuery, state: FSMContext):
    try:
        task_id, list_filter, page = _parse_action(cb.data)
    except (AttributeError, TypeError, ValueError):
        await cb.answer("Некорректная кнопка.", show_alert=True)
        return
    if _load_task(task_id) is None:
        await cb.answer("План уже удалён.", show_alert=True)
        return

    await _store_context(state, task_id, list_filter, page)
    await state.set_state(EditEvent.date)
    today = dt.datetime.now(config.LOCAL_TZ).date()
    await cb.message.edit_text(
        "Выбери новую дату:",
        reply_markup=date_shortcuts_kb("edit", today),
    )
    await cb.answer()


@router.callback_query(F.data == "edit:date:shortcuts")
async def edit_date_shortcuts(cb: types.CallbackQuery):
    today = dt.datetime.now(config.LOCAL_TZ).date()
    await cb.message.edit_text(
        "Выбери новую дату:",
        reply_markup=date_shortcuts_kb("edit", today),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("edit:date:nav:"))
async def edit_calendar_nav(cb: types.CallbackQuery):
    try:
        year, month = map(int, cb.data.rsplit(":", 1)[1].split("-"))
        shown = dt.date(year, month, 1)
    except (TypeError, ValueError):
        await cb.answer("Не удалось открыть календарь.", show_alert=True)
        return

    await cb.message.edit_text(
        "Выбери новую дату:",
        reply_markup=calendar_kb("edit", shown.year, shown.month),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("edit:date:pick:"))
async def edit_date_pick(cb: types.CallbackQuery, state: FSMContext):
    try:
        chosen_date = dt.date.fromisoformat(cb.data.rsplit(":", 1)[1])
    except (TypeError, ValueError):
        await cb.answer("Некорректная дата.", show_alert=True)
        return

    data = await state.get_data()
    task = _load_task(data.get("task_id", 0))
    if task is None:
        await state.clear()
        await cb.answer("План уже удалён.", show_alert=True)
        return

    local = task_local_datetime(task)
    timestamp = local_schedule_to_utc(chosen_date, local.time())
    with SessionLocal() as db_session:
        TaskService(TaskRepo(db_session)).update_schedule(
            task.id,
            timestamp,
            is_all_day=bool(task.is_all_day),
        )

    await state.clear()
    channel_updated = await try_update_posts(cb.bot)
    prefix = "✅ Дата изменена"
    if not channel_updated:
        prefix += "\n⚠️ Канал обновится позже"
    await _show_task(
        cb.message,
        task.id,
        data.get("list_filter", "all"),
        data.get("page", 0),
        prefix=prefix,
        edit_message=True,
    )
    await cb.answer()


@router.callback_query(F.data.startswith("task:time:"))
async def edit_time_start(cb: types.CallbackQuery, state: FSMContext):
    try:
        task_id, list_filter, page = _parse_action(cb.data)
    except (AttributeError, TypeError, ValueError):
        await cb.answer("Некорректная кнопка.", show_alert=True)
        return
    if _load_task(task_id) is None:
        await cb.answer("План уже удалён.", show_alert=True)
        return

    await _store_context(state, task_id, list_filter, page)
    await state.set_state(EditEvent.time)
    await cb.message.edit_text(
        "Выбери новое время:",
        reply_markup=time_kb(
            "edit",
            back_callback=f"task:view:{task_id}:{list_filter}:{page}",
        ),
    )
    await cb.answer()


@router.callback_query(F.data == "edit:time:custom")
async def edit_custom_time_start(cb: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if "task_id" not in data:
        await cb.answer("Изменение уже завершено.", show_alert=True)
        return

    await state.set_state(EditEvent.custom_time)
    await cb.message.edit_text(
        "Напиши время. Можно: <code>22</code>, <code>2217</code>, "
        "<code>22 17</code> или <code>22:17</code>.",
        reply_markup=cancel_kb("edit"),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("edit:time:"))
async def edit_time_pick(cb: types.CallbackQuery, state: FSMContext):
    value = cb.data.rsplit(":", 1)[1]
    if value == "custom":
        return
    if value == "all":
        chosen_time = dt.time(0, 0)
        is_all_day = True
    else:
        chosen_time = parse_time_input(value)
        is_all_day = False
        if chosen_time is None:
            await cb.answer("Некорректное время.", show_alert=True)
            return

    await cb.answer()
    await _save_time(
        cb.message,
        state,
        chosen_time,
        is_all_day=is_all_day,
        edit_message=True,
    )


@router.message(
    EditEvent.custom_time,
    ~F.text.startswith("/"),
    ~F.text.in_({"➕ Новое событие", "📋 Мои планы"}),
)
async def edit_custom_time(msg: types.Message, state: FSMContext):
    chosen_time = parse_time_input(msg.text or "")
    if chosen_time is None:
        await msg.answer(
            "Не понял время. Примеры: <code>22</code>, <code>2217</code>, "
            "<code>22 17</code>, <code>22:17</code>.",
            reply_markup=cancel_kb("edit"),
        )
        return
    await _save_time(
        msg,
        state,
        chosen_time,
        is_all_day=False,
        edit_message=False,
    )


async def _save_time(
    message: types.Message,
    state: FSMContext,
    chosen_time: dt.time,
    *,
    is_all_day: bool,
    edit_message: bool,
) -> None:
    data = await state.get_data()
    task = _load_task(data.get("task_id", 0))
    if task is None:
        await state.clear()
        await message.answer("План уже удалён.")
        return

    chosen_date = task_local_datetime(task).date()
    timestamp = local_schedule_to_utc(chosen_date, chosen_time)
    with SessionLocal() as db_session:
        TaskService(TaskRepo(db_session)).update_schedule(
            task.id,
            timestamp,
            is_all_day=is_all_day,
        )

    await state.clear()
    channel_updated = await try_update_posts(message.bot)
    prefix = "✅ Время изменено"
    if not channel_updated:
        prefix += "\n⚠️ Канал обновится позже"
    await _show_task(
        message,
        task.id,
        data.get("list_filter", "all"),
        data.get("page", 0),
        prefix=prefix,
        edit_message=edit_message,
    )


@router.callback_query(F.data.startswith("task:delete:"))
async def delete_confirm(cb: types.CallbackQuery):
    try:
        task_id, list_filter, page = _parse_action(cb.data)
    except (AttributeError, TypeError, ValueError):
        await cb.answer("Некорректная кнопка.", show_alert=True)
        return
    task = _load_task(task_id)
    if task is None:
        await cb.answer("План уже удалён.", show_alert=True)
        return

    markup = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Да, удалить",
                    callback_data=(f"task:delete_yes:{task_id}:{list_filter}:{page}"),
                ),
                types.InlineKeyboardButton(
                    text="Нет",
                    callback_data=f"task:view:{task_id}:{list_filter}:{page}",
                ),
            ]
        ]
    )
    await cb.message.edit_text(
        task_card_text(task, prefix="Точно удалить?"),
        reply_markup=markup,
    )
    await cb.answer()


@router.callback_query(F.data.startswith("task:delete_yes:"))
async def delete_task(cb: types.CallbackQuery):
    try:
        _, _, raw_id, list_filter, raw_page = cb.data.split(":", 4)
        task_id = int(raw_id)
        page = int(raw_page)
    except (AttributeError, TypeError, ValueError):
        await cb.answer("Некорректная кнопка.", show_alert=True)
        return

    with SessionLocal() as db_session:
        deleted = TaskService(TaskRepo(db_session)).delete_task(task_id)
    if not deleted:
        await cb.answer("План уже удалён.", show_alert=True)
    else:
        channel_updated = await try_update_posts(cb.bot)
        if not channel_updated:
            await cb.message.answer("⚠️ План удалён, но канал обновится позже.")
        await cb.answer("План удалён.")

    from bot.handlers.list import edit_or_send_list

    await edit_or_send_list(
        cb.message,
        list_filter,
        page,
        edit_message=True,
    )
