import datetime as dt

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.core.config import config
from bot.core.db import SessionLocal
from bot.handlers.states import AddEvent
from bot.keyboards.planner import (
    calendar_kb,
    cancel_kb,
    date_shortcuts_kb,
    task_actions_kb,
    time_kb,
)
from bot.repositories.task_repo import TaskRepo
from bot.services.dtos import CreateTaskDTO
from bot.services.task_service import TaskService
from bot.services.updater import try_update_posts
from bot.utils.presentation import task_card_text
from bot.utils.utils import local_schedule_to_utc, parse_time_input

router = Router()


async def _begin_add(
    message: types.Message,
    state: FSMContext,
    *,
    edit_message: bool = False,
) -> None:
    await state.clear()
    await state.set_state(AddEvent.title)
    text = "Как называется план?"
    markup = cancel_kb("add")
    if edit_message:
        await message.edit_text(text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)


@router.message(Command("add"))
@router.message(F.text == "➕ Новое событие")
async def start_add(msg: types.Message, state: FSMContext):
    await _begin_add(msg, state)


@router.callback_query(F.data == "add:start")
async def start_add_callback(cb: types.CallbackQuery, state: FSMContext):
    await _begin_add(cb.message, state, edit_message=True)
    await cb.answer()


@router.callback_query(F.data == "add:cancel")
async def cancel_add_callback(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("Добавление отменено.")
    await cb.answer()


@router.message(AddEvent.title, Command("cancel"))
@router.message(AddEvent.title, F.text.casefold() == "отмена")
@router.message(AddEvent.date, Command("cancel"))
@router.message(AddEvent.date, F.text.casefold() == "отмена")
@router.message(AddEvent.time, Command("cancel"))
@router.message(AddEvent.time, F.text.casefold() == "отмена")
@router.message(AddEvent.custom_time, Command("cancel"))
@router.message(AddEvent.custom_time, F.text.casefold() == "отмена")
async def cancel_add_message(msg: types.Message, state: FSMContext):
    await state.clear()
    await msg.answer("Добавление отменено.")


@router.message(
    AddEvent.title,
    ~F.text.startswith("/"),
    ~F.text.in_({"➕ Новое событие", "📋 Мои планы"}),
)
async def get_title(msg: types.Message, state: FSMContext):
    title = (msg.text or "").strip()
    if not title:
        await msg.answer(
            "Название не может быть пустым.",
            reply_markup=cancel_kb("add"),
        )
        return
    if len(title) > 120:
        await msg.answer(
            "Слишком длинное название — максимум 120 символов.",
            reply_markup=cancel_kb("add"),
        )
        return

    await state.update_data(title=title)
    await state.set_state(AddEvent.date)
    today = dt.datetime.now(config.LOCAL_TZ).date()
    await msg.answer(
        "На какую дату?",
        reply_markup=date_shortcuts_kb("add", today),
    )


@router.callback_query(F.data == "add:date:shortcuts")
async def add_date_shortcuts(cb: types.CallbackQuery):
    today = dt.datetime.now(config.LOCAL_TZ).date()
    await cb.message.edit_text(
        "На какую дату?",
        reply_markup=date_shortcuts_kb("add", today),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("add:date:nav:"))
async def add_calendar_nav(cb: types.CallbackQuery):
    try:
        year, month = map(int, cb.data.rsplit(":", 1)[1].split("-"))
        shown = dt.date(year, month, 1)
    except (TypeError, ValueError):
        await cb.answer("Не удалось открыть календарь.", show_alert=True)
        return

    await cb.message.edit_text(
        "Выбери дату:",
        reply_markup=calendar_kb("add", shown.year, shown.month),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("add:date:pick:"))
async def add_date_pick(cb: types.CallbackQuery, state: FSMContext):
    try:
        chosen = dt.date.fromisoformat(cb.data.rsplit(":", 1)[1])
    except (TypeError, ValueError):
        await cb.answer("Некорректная дата.", show_alert=True)
        return

    data = await state.get_data()
    if "title" not in data:
        await cb.answer("Добавление уже завершено. Начни заново.", show_alert=True)
        return

    await state.update_data(chosen_date=chosen.isoformat())
    await state.set_state(AddEvent.time)
    await cb.message.edit_text(
        f"Дата: <b>{chosen:%d.%m.%Y}</b>\nТеперь выбери время:",
        reply_markup=time_kb("add", back_callback="add:date:shortcuts"),
    )
    await cb.answer()


@router.callback_query(F.data == "add:time:custom")
async def add_custom_time_start(cb: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if "chosen_date" not in data:
        await cb.answer("Сначала выбери дату.", show_alert=True)
        return

    await state.set_state(AddEvent.custom_time)
    await cb.message.edit_text(
        "Напиши время. Можно: <code>22</code>, <code>2217</code>, "
        "<code>22 17</code> или <code>22:17</code>.",
        reply_markup=cancel_kb("add"),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("add:time:"))
async def add_time_pick(cb: types.CallbackQuery, state: FSMContext):
    value = cb.data.rsplit(":", 1)[1]
    if value in {"custom"}:
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
    await _save_event(
        cb.message,
        state,
        chosen_time=chosen_time,
        is_all_day=is_all_day,
        edit_message=True,
    )


@router.message(
    AddEvent.custom_time,
    ~F.text.startswith("/"),
    ~F.text.in_({"➕ Новое событие", "📋 Мои планы"}),
)
async def add_custom_time(msg: types.Message, state: FSMContext):
    chosen_time = parse_time_input(msg.text or "")
    if chosen_time is None:
        await msg.answer(
            "Не понял время. Примеры: <code>22</code>, <code>2217</code>, "
            "<code>22 17</code>, <code>22:17</code>.",
            reply_markup=cancel_kb("add"),
        )
        return

    await _save_event(
        msg,
        state,
        chosen_time=chosen_time,
        is_all_day=False,
    )


async def _save_event(
    message: types.Message,
    state: FSMContext,
    *,
    chosen_time: dt.time,
    is_all_day: bool,
    edit_message: bool = False,
) -> None:
    data = await state.get_data()
    try:
        chosen_date = dt.date.fromisoformat(data["chosen_date"])
        title = data["title"]
    except (KeyError, ValueError):
        await state.clear()
        await message.answer("Данные добавления устарели. Начни заново.")
        return

    timestamp = local_schedule_to_utc(chosen_date, chosen_time)
    with SessionLocal() as db_session:
        service = TaskService(TaskRepo(db_session))
        task = service.create(
            CreateTaskDTO(
                title=title,
                datetime=timestamp,
                description=None,
                is_all_day=is_all_day,
            )
        )

    await state.clear()
    channel_updated = await try_update_posts(message.bot)
    prefix = "✅ План добавлен"
    if not channel_updated:
        prefix += "\n⚠️ Канал обновится позже"
    text = task_card_text(task, prefix=prefix)
    markup = task_actions_kb(task.id)
    if edit_message:
        await message.edit_text(text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)
