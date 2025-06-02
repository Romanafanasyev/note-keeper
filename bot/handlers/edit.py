# bot/handlers/edit.py
from aiogram import Router, types, F
from aiogram.filters import Command
import re
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from bot.core.db import SessionLocal
from bot.repositories.task_repo import TaskRepo
from bot.services.updater import update_posts
from bot.utils.utils import parse_user_datetime
from bot.keyboards.keyboards import main_kb

router = Router()

ID_RE = re.compile(r"#(\d{1,6})")

def extract_id(text: str | None) -> int | None:
    """Вернёт int ID, если в тексте есть #123."""
    if not text:
        return None
    m = ID_RE.search(text)
    return int(m.group(1)) if m else None


def parse_id_or_reply(msg: types.Message) -> int | None:
    """Получить ID либо из аргумента команды, либо из reply."""
    cmd, *args = msg.text.split(maxsplit=1)
    if args and args[0].isdigit():
        return int(args[0])

    if msg.reply_to_message:
        return extract_id(msg.reply_to_message.text)
    return None


@router.message(Command("del"))
async def cmd_del(msg: types.Message):
    pid = parse_id_or_reply(msg)
    if not pid:
        await msg.answer("Укажи ID: <code>/del 3</code> или ответь /del на сообщение со списком.")
        return

    with SessionLocal() as db_session:
        task_repo = TaskRepo(db_session)
        success = task_repo.mark_deleted(pid)

    if not success:
        await msg.answer("План не найден или уже удалён.")
        return

    await update_posts(msg.bot)
    await msg.answer("❌ План удалён.", reply_markup=main_kb())


class EditEvent(StatesGroup):
    choose_field = State()
    new_value    = State()

FIELDS = {"title": "Название", "datetime": "Дата/время", "description": "Описание"}

@router.message(Command("edit"))
async def cmd_edit_start(msg: types.Message, state: FSMContext):
    pid = parse_id_or_reply(msg)
    if not pid:
        await msg.answer("Укажи ID: <code>/edit 3</code> или ответь /edit на сообщение со списком.")
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
    pid   = data["pid"]
    field = data["field"]
    raw   = msg.text.strip()

    with SessionLocal() as db_session:
        task_repo = TaskRepo(db_session)
        plan = task_repo.get(pid)

        if not plan or plan.state == "deleted":
            await msg.answer("План не найден.")
            await state.clear()
            return

        if field == "title":
            plan.title = raw
        elif field == "description":
            plan.description = None if raw.lower() == "empty" else raw
        elif field == "datetime":
            dt_parsed = parse_user_datetime(raw)
            if not dt_parsed:
                await msg.answer("Не понял дату. Формат: <code>22.05 21:30</code>")
                return
            plan.ts_utc = dt_parsed
            plan.reminded_24h = False
            plan.reminded_90m = False

        task_repo.update(plan)

    await update_posts(msg.bot)
    await msg.answer("✅ Обновлено.", reply_markup=main_kb())
    await state.clear()
