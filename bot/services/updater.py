# bot/services/updater.py

import datetime as dt
from aiogram import Bot
from sqlalchemy import select
from bot.core.db import SessionLocal
from bot.models.models import Plan, ChannelPost
from bot.core.config import CHANNEL_ID
import logging
from bot.core.config import LOCAL_TZ

TAGS = ("month", "week", "tomorrow", "today")
WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTH_RU = (
    "январь", "февраль", "март", "апрель", "май", "июнь",
    "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"
)

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
        end = start + dt.timedelta(days=7)
    else:  # month
        start = now.replace(day=1)
        end = (start + dt.timedelta(days=32)).replace(day=1)
    return start, end, start.astimezone(dt.timezone.utc), end.astimezone(dt.timezone.utc)

def _header(tag: str, start: dt.datetime):
    d, m = start.day, MONTH_RU[start.month - 1].capitalize()
    if tag == "week":
        return "<b>📌 Планы на Неделю</b>\n"
    if tag == "today":
        return f"<b>📌 Планы на Сегодня - {d:02d} {m}</b>\n"
    if tag == "month":
        return f"<b>📌 Планы на {m}</b>\n"
    if tag == "tomorrow":
        return f"<b>📌 Планы на Завтра - {d:02d} {m}</b>\n"
    return f"<b>📅 {m} {start.year}</b>\n"

def _format_plans(rows, tag="month"):
    now = _local_now().replace(hour=0, minute=0, second=0, microsecond=0)
    out = []
    for p in rows:
        utc = p.ts_utc
        if utc.tzinfo is None:
            utc = utc.replace(tzinfo=dt.timezone.utc)

        local = utc.astimezone(LOCAL_TZ)
        if local < now:
            continue

        weekday = WEEKDAYS[local.weekday()]
        date_str = f"{local.day:02d}.{local.month:02d}"

        if tag == "today":
            lead = local.strftime("%H:%M")
        else:
            lead = f"{weekday} • {date_str}"
            if local.time() != dt.time(0, 0):
                lead += f" • {local.strftime('%H:%M')}"

        out.append(f"🕘 <b>{lead}</b> | {p.title}")
        if p.description:
            out.append(p.description)
            out.append("")
    return "\n".join(out) or "—"

async def ensure_posts(bot: Bot):
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
                    Plan.ts_utc >= min(start_utc, _local_now().astimezone(dt.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)),
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
