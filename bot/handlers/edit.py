# bot/handlers/edit.py
from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.core.db import SessionLocal
from bot.keyboards.keyboards import main_kb
from bot.repositories.task_repo import TaskRepo
from bot.services.dtos import EditTaskDTO
from bot.services.task_service import TaskService
from bot.services.updater import update_posts
from bot.utils.utils import parse_id_or_reply, parse_user_datetime

router = Router()


class EditEvent(StatesGroup):
    choose_field = State()
    new_value = State()


FIELDS = {
    "title": "Название",
    "datetime": "Дата/время",
    "description": "Описание",
}


@router.message(Command("del"))
async def cmd_del(msg: types.Message):
    pid = parse_id_or_reply(msg)
    if not pid:
        await msg.answer(
            "Укажи ID: <code>/del 3</code> " "или ответь /del на сообщение со списком."
        )
        return

    with SessionLocal() as db_session:
        service = TaskService(TaskRepo(db_session))
        success = service.delete_task(pid)

    if not success:
        await msg.answer("План не найден или уже удалён.")
        return

    await update_posts(msg.bot)
    await msg.answer("❌ План удалён.", reply_markup=main_kb())


@router.message(Command("edit"))
async def cmd_edit_start(msg: types.Message, state: FSMContext):
    pid = parse_id_or_reply(msg)
    if not pid:
        await msg.answer(
            "Укажи ID: <code>/edit 3</code> "
            "или ответь /edit на сообщение со списком."
        )
        return

    await state.update_data(pid=pid)
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=v, callback_data=f"ef:{k}")]
            for k, v in FIELDS.items()
        ]
    )
    await msg.answer("Что изменить?", reply_markup=kb)
    await state.set_state(EditEvent.choose_field)


@router.callback_query(F.data.startswith("ef:"))
async def choose_field(cb: types.CallbackQuery, state: FSMContext):
    field = cb.data.split(":", 1)[1]
    await state.update_data(field=field)
    await state.set_state(EditEvent.new_value)

    prompt = "Новое значение:"
    if field == "datetime":
        prompt = "Новая дата/время в формате <code>22.05 21:30</code>:"
    await cb.message.edit_text(prompt)
    await cb.answer()


@router.message(EditEvent.new_value)
async def save_new_value(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    raw = msg.text.strip()

    if data["field"] == "datetime":
        dt_parsed = parse_user_datetime(raw)
        if not dt_parsed:
            await msg.answer("Не понял дату. Формат: <code>22.05 21:30</code>")
            return
        raw = dt_parsed.isoformat()

    dto = EditTaskDTO(task_id=data["pid"], field=data["field"], new_value=raw)

    with SessionLocal() as db_session:
        service = TaskService(TaskRepo(db_session))
        try:
            service.edit_task(dto)
        except ValueError as e:
            await msg.answer(str(e))
            return

    await update_posts(msg.bot)
    await msg.answer("✅ Обновлено.", reply_markup=main_kb())
    await state.clear()
