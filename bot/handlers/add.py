# bot/handlers/add.py
from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.core.db import SessionLocal
from bot.keyboards.keyboards import main_kb
from bot.repositories.task_repo import TaskRepo
from bot.services.dtos import CreateTaskDTO
from bot.services.task_service import TaskService
from bot.services.updater import update_posts
from bot.utils.utils import parse_user_datetime

router = Router()


class AddEvent(StatesGroup):
    title = State()
    datetime = State()
    description = State()


@router.message(F.text == "➕ Новое событие")
async def start_add(msg: types.Message, state: FSMContext):
    await state.set_state(AddEvent.title)
    await msg.answer("Введи <b>название события</b>:")


@router.message(AddEvent.title)
async def get_title(msg: types.Message, state: FSMContext):
    await state.update_data(title=msg.text.strip())
    await state.set_state(AddEvent.datetime)
    await msg.answer(
        "Теперь дату и время (DD.MM HH:MM). Например: <code>22.05 21:30</code>"
    )


@router.message(AddEvent.datetime)
async def get_datetime(msg: types.Message, state: FSMContext):
    dt_parsed = parse_user_datetime(msg.text)
    if not dt_parsed:
        await msg.answer(
            "Не понял дату. Формат: <code>22.05 21:30</code> или <code>22.05</code>"
        )
        return
    await state.update_data(ts_utc=dt_parsed)
    await state.set_state(AddEvent.description)

    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True, keyboard=[[types.KeyboardButton(text="empty")]]
    )
    await msg.answer(
        "Описание? Можешь написать текст или нажать <b>empty</b>.", reply_markup=kb
    )


@router.message(AddEvent.description, F.text.casefold() == "empty")
async def empty_description(msg: types.Message, state: FSMContext):
    await save_event_and_finish(msg, state, description=None)


@router.message(AddEvent.description)
async def get_description(msg: types.Message, state: FSMContext):
    await save_event_and_finish(msg, state, description=msg.text.strip())


async def save_event_and_finish(msg, state, description):
    data = await state.get_data()

    dto = CreateTaskDTO(
        title=data["title"], datetime=data["ts_utc"], description=description
    )

    with SessionLocal() as db_session:
        service = TaskService(TaskRepo(db_session))
        service.create_task(dto)

    await update_posts(msg.bot)
    await msg.answer("✅ Событие добавлено!", reply_markup=main_kb())
    await state.clear()
