# bot/updater.py
import datetime as dt
from aiogram import Bot
from sqlalchemy import select
from bot.db import SessionLocal
from bot.models import Plan, ChannelPost
from bot.config import CHANNEL_ID
import logging
from bot.config import LOCAL_TZ

TAGS = ("month", "week", "tomorrow", "today")

def _local_now():
    return dt.datetime.now(tz=LOCAL_TZ)

def _bounds(tag: str):
    now = _local_now().replace(hour=0, minute=0, second=0, microsecond=0)
    if tag == "today":
        start, end = now, now + dt.timedelta(days=1)
    elif tag == "tomorrow":
        start, end = now + dt.timedelta(days=1), now + dt.timedelta(days=2)
    elif tag == "week":
        start = now - dt.timedelta(days=now.weekday())
        end   = start + dt.timedelta(days=7)
    else:  # month
        start = now.replace(day=1)
        # следующий месяц
        end = (start + dt.timedelta(days=32)).replace(day=1)
    return start, end, start.astimezone(dt.timezone.utc), end.astimezone(dt.timezone.utc)

# bot/updater.py  — замени _header() и _format_plans()

MONTH_RU = (
    "января","февраля","марта","апреля","мая","июня",
    "июля","августа","сентября","октября","ноября","декабря"
)

def _header(tag: str, start: dt.datetime):
    d, m = start.day, MONTH_RU[start.month-1]
    if tag == "week":
        return "<b>📌 Планы на Неделю</b>\n"
    if tag == "today":
        return f"<b>📌 Планы на Сегодня - {d:02d} {m.title()}</b>\n"
    if tag == "month":
        return "<b>📌 Планы на Месяц</b>\n"
    if tag == "tomorrow":
        return f"<b>📌 Планы на Завтра - {d:02d} {m.title()}</b>\n"

    return f"<b>📅 {m.title()} {start.year}</b>\n"

def _fmt_date(dt_local: dt.datetime):
    return f"{dt_local.day:02d} {MONTH_RU[dt_local.month-1].title()}"

def _format_plans(rows, tag="month"):
    out = []
    for p in rows:
        utc = p.ts_utc
        if utc.tzinfo is None:
            utc = utc.replace(tzinfo=dt.timezone.utc)

        local = utc.astimezone(LOCAL_TZ)
        if tag in ["today", "tomorrow"]:
            lead = local.strftime("%H:%M")
        else:
            lead = _fmt_date(local)

        bullet = "🕘"  # единый значок
        out.append(f"{bullet} <b>{lead}</b> | {p.title}")
        if p.description:
            out.append(p.description)
            out.append("")  # пустая строка-разделитель
    return "\n".join(out) or "—"

async def ensure_posts(bot: Bot):
    """Создать 4 поста в канале, если их ещё нет."""
    with SessionLocal() as db:
        existing = {row.tag: row.message_id for row in db.scalars(select(ChannelPost)).all()}
        for tag in TAGS:
            if tag in existing:
                continue
            msg = await bot.send_message(CHANNEL_ID, f"⏳ initializing {tag} …")
            db.add(ChannelPost(tag=tag, message_id=msg.message_id))
        db.commit()

async def update_posts(bot: Bot):
    await ensure_posts(bot)
    with SessionLocal() as db:
        posts = {row.tag: row.message_id for row in db.scalars(select(ChannelPost)).all()}
        for tag in TAGS:
            start_loc, end_loc, start_utc, end_utc = _bounds(tag)
            plans = db.scalars(
                select(Plan).where(
                    Plan.state == "scheduled",
                    Plan.ts_utc >= start_utc,
                    Plan.ts_utc < end_utc
                ).order_by(Plan.ts_utc)
            ).all()

            text = _header(tag, start_loc) + "\n\n" + _format_plans(plans, tag)
            try:
                await bot.edit_message_text(
                    chat_id=CHANNEL_ID,
                    message_id=posts[tag],
                    text=text
                )
            except Exception as e:
                logging.critical(f"Ошибка во время редактирования сообщ: {e}")
