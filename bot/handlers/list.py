import datetime as dt
import math

from aiogram import F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext

from bot.core.config import config
from bot.core.db import SessionLocal
from bot.keyboards.planner import task_actions_kb, task_rows
from bot.repositories.task_repo import TaskRepo
from bot.services.task_service import TaskService
from bot.utils.presentation import (
    MONTHS_GENITIVE,
    MONTHS_NOMINATIVE,
    task_card_text,
)

router = Router()
PAGE_SIZE = 8
VALID_FILTERS = {"all", "today", "week", "month", "next"}
FILTER_ALIASES = {
    "all": "all",
    "today": "today",
    "week": "week",
    "month": "month",
    "next": "next",
}


def _local_midnight() -> dt.datetime:
    return dt.datetime.now(config.LOCAL_TZ).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )


def _filter_bounds(list_filter: str) -> tuple[dt.datetime, dt.datetime] | None:
    today = _local_midnight()
    if list_filter == "all":
        return None
    if list_filter == "today":
        return today, today + dt.timedelta(days=1)
    if list_filter == "week":
        return today, today + dt.timedelta(days=7)

    current_month = today.replace(day=1)
    next_month = (current_month + dt.timedelta(days=32)).replace(day=1)
    if list_filter == "month":
        return today, next_month
    following_month = (next_month + dt.timedelta(days=32)).replace(day=1)
    return next_month, following_month


def _list_title(list_filter: str) -> str:
    today = _local_midnight()
    if list_filter == "today":
        return "Планы на сегодня"
    if list_filter == "week":
        return "Планы на ближайшие 7 дней"
    if list_filter == "month":
        month = MONTHS_GENITIVE[today.month - 1]
        return f"Планы до конца {month}"
    if list_filter == "next":
        next_month = (today.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
        month = MONTHS_NOMINATIVE[next_month.month - 1].capitalize()
        return f"Планы на {month}"
    return "Все будущие планы"


def get_filtered_tasks(list_filter: str):
    bounds = _filter_bounds(list_filter)
    with SessionLocal() as db_session:
        service = TaskService(TaskRepo(db_session))
        if bounds is None:
            start = _local_midnight().astimezone(dt.timezone.utc)
            return service.get_upcoming_tasks(start)
        start, end = bounds
        return service.get_tasks_between(
            start.astimezone(dt.timezone.utc),
            end.astimezone(dt.timezone.utc),
        )


def build_list_view(
    list_filter: str,
    page: int,
) -> tuple[str, types.InlineKeyboardMarkup]:
    if list_filter not in VALID_FILTERS:
        list_filter = "all"

    tasks = get_filtered_tasks(list_filter)
    total_pages = max(1, math.ceil(len(tasks) / PAGE_SIZE))
    page = min(max(page, 0), total_pages - 1)
    page_tasks = tasks[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]

    text = f"<b>{_list_title(list_filter)}</b>"
    if page_tasks:
        text += "\n\nНажми на план, чтобы открыть или изменить его."
    else:
        text += "\n\nПока ничего нет."

    rows = task_rows(page_tasks, list_filter, page)
    rows.extend(
        [
            [
                types.InlineKeyboardButton(
                    text="Сегодня",
                    callback_data="list:today:0",
                ),
                types.InlineKeyboardButton(
                    text="7 дней",
                    callback_data="list:week:0",
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="Этот месяц",
                    callback_data="list:month:0",
                ),
                types.InlineKeyboardButton(
                    text="Следующий",
                    callback_data="list:next:0",
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="Все будущие",
                    callback_data="list:all:0",
                )
            ],
        ]
    )
    if total_pages > 1:
        rows.append(
            [
                types.InlineKeyboardButton(
                    text="←",
                    callback_data=f"list:{list_filter}:{max(0, page - 1)}",
                ),
                types.InlineKeyboardButton(
                    text=f"{page + 1}/{total_pages}",
                    callback_data="noop",
                ),
                types.InlineKeyboardButton(
                    text="→",
                    callback_data=(
                        f"list:{list_filter}:{min(total_pages - 1, page + 1)}"
                    ),
                ),
            ]
        )
    rows.append(
        [
            types.InlineKeyboardButton(
                text="➕ Добавить план",
                callback_data="add:start",
            )
        ]
    )
    return text, types.InlineKeyboardMarkup(inline_keyboard=rows)


async def edit_or_send_list(
    message: types.Message,
    list_filter: str,
    page: int,
    *,
    edit_message: bool,
) -> None:
    text, markup = build_list_view(list_filter, page)
    if not edit_message:
        await message.answer(text, reply_markup=markup)
        return

    try:
        await message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as exc:
        if "message is not modified" not in exc.message.lower():
            raise


@router.message(Command("list"))
async def cmd_list(
    msg: types.Message,
    command: CommandObject,
    state: FSMContext,
):
    await state.clear()
    requested = (command.args or "").strip().lower()
    list_filter = FILTER_ALIASES.get(requested, "all")
    await edit_or_send_list(msg, list_filter, 0, edit_message=False)


@router.message(F.text == "📋 Мои планы")
async def my_plans(msg: types.Message, state: FSMContext):
    await state.clear()
    await edit_or_send_list(msg, "all", 0, edit_message=False)


@router.callback_query(F.data.startswith("list:"))
async def list_callback(cb: types.CallbackQuery, state: FSMContext):
    try:
        _, list_filter, raw_page = cb.data.split(":", 2)
        page = int(raw_page)
    except (AttributeError, TypeError, ValueError):
        await cb.answer("Некорректная кнопка.", show_alert=True)
        return

    await state.clear()
    await edit_or_send_list(
        cb.message,
        list_filter,
        page,
        edit_message=True,
    )
    await cb.answer()


@router.callback_query(F.data.startswith("task:view:"))
async def task_view(cb: types.CallbackQuery, state: FSMContext):
    try:
        _, _, raw_id, list_filter, raw_page = cb.data.split(":", 4)
        task_id = int(raw_id)
        page = int(raw_page)
    except (AttributeError, TypeError, ValueError):
        await cb.answer("Некорректная кнопка.", show_alert=True)
        return

    await state.clear()
    with SessionLocal() as db_session:
        task = TaskService(TaskRepo(db_session)).get_task(task_id)

    if task is None:
        await cb.answer("Этот план уже удалён.", show_alert=True)
        await edit_or_send_list(
            cb.message,
            list_filter,
            page,
            edit_message=True,
        )
        return

    await cb.message.edit_text(
        task_card_text(task),
        reply_markup=task_actions_kb(
            task.id,
            list_filter=list_filter,
            page=page,
        ),
    )
    await cb.answer()


@router.callback_query(F.data == "noop")
async def noop_callback(cb: types.CallbackQuery):
    await cb.answer()
