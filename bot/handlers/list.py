# bot/handlers/list.py
from aiogram import Router, types, F
from aiogram.filters import Command
import datetime as dt
from datetime import timedelta
from sqlalchemy import select
from bot.core.db import SessionLocal
from bot.models.models import Plan
from bot.core.config import LOCAL_TZ
from bot.keyboards.keyboards import main_kb

router = Router()

def _range(tag: str):
    now = dt.datetime.now(LOCAL_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    if tag == "today":
        return now, now + timedelta(days=1)
    if tag == "week":
        start = now - timedelta(days=now.weekday())
        return start, start + timedelta(days=7)
    # month
    start = now.replace(day=1)
    end = (start + timedelta(days=32)).replace(day=1)
    return start, end

def _fmt_line(p: Plan) -> str:
    local = p.ts_utc.replace(tzinfo=dt.timezone.utc).astimezone(LOCAL_TZ)
    lead  = local.strftime("%d.%m %H:%M")
    return f"<code>#{p.id:03d}</code> | {lead} | <b>{p.title}</b>"

def build_list(tag: str) -> str:
    start, end = _range(tag)
    with SessionLocal() as db:
        rows = db.scalars(
            select(Plan).where(
                Plan.state == "scheduled",
                Plan.ts_utc.between(start.astimezone(dt.timezone.utc),
                                    end.astimezone(dt.timezone.utc))
            ).order_by(Plan.ts_utc)
        ).all()
    if not rows:
        return "Ничего нет."
    out = [_fmt_line(p) for p in rows]
    for p in rows:
        if p.description:
            out.append(f"  {p.description}")
    return "\n".join(out)

# /list day|week|month  (month = текущий)
@router.message(Command("list"))
async def cmd_list(msg: types.Message, command: Command):
    arg = (command.args or "").strip().lower()
    tag = {"day": "today", "today": "today",
           "week": "week", "month": "month"}.get(arg, "today")
    title = {"today": "Сегодня", "week": "Неделя", "month": "Месяц"}[tag]
    await msg.answer(f"<b>📋 {title}</b>\n\n{build_list(tag)}", reply_markup=main_kb())

# кнопка «📋 Мои планы» — показывает “сегодня + завтра”
@router.message(F.text == "📋 Мои планы")
async def my_plans(msg: types.Message):
    txt_today = build_list("today")
    txt_tom   = build_list("week")  # ближайшие задачи на неделю достаточно
    await msg.answer(f"<b>Сегодня</b>\n{txt_today}\n\n<b>Неделя</b>\n{txt_tom}",
                     reply_markup=main_kb())
