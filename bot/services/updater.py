# bot/services/updater.py
import asyncio
import datetime as dt
import html

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from bot.core.config import config
from bot.core.db import SessionLocal
from bot.repositories.channel_post_repo import ChannelPostRepo
from bot.repositories.task_repo import TaskRepo
from bot.services.channel_post_service import (
    ChannelPostService,
    CreateChannelPostDTO,
)
from bot.services.task_service import TaskService
from bot.utils.logger import logger

TAGS = ("month", "week", "tomorrow", "today")
_update_lock = asyncio.Lock()
WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTH_RU = (
    "январь",
    "февраль",
    "март",
    "апрель",
    "май",
    "июнь",
    "июль",
    "август",
    "сентябрь",
    "октябрь",
    "ноябрь",
    "декабрь",
)


def _local_now():
    return dt.datetime.now(tz=config.LOCAL_TZ)


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
    return (
        start,
        end,
        start.astimezone(dt.timezone.utc),
        end.astimezone(dt.timezone.utc),
    )


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

        local = utc.astimezone(config.LOCAL_TZ)
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

        out.append(f"🕘 <b>{lead}</b> | {html.escape(p.title)}")
        if p.description:
            out.append(html.escape(p.description))
            out.append("")
    return "\n".join(out) or "—"


async def ensure_posts(bot: Bot):
    with SessionLocal() as db_session:
        channel_post_service = ChannelPostService(ChannelPostRepo(db_session))
        existing = channel_post_service.get_all_posts()

        for tag in TAGS:
            if tag in existing:
                continue
            msg = await bot.send_message(config.CHANNEL_ID, f"⏳ initializing {tag} …")
            dto = CreateChannelPostDTO(tag=tag, message_id=msg.message_id)
            channel_post_service.create_channel_post(dto)


async def update_posts(bot: Bot):
    async with _update_lock:
        await _update_posts(bot)


async def _update_posts(bot: Bot):
    await ensure_posts(bot)
    with SessionLocal() as db_session:
        task_service = TaskService(TaskRepo(db_session))
        channel_post_service = ChannelPostService(ChannelPostRepo(db_session))
        posts = channel_post_service.get_all_posts()

        for tag in TAGS:
            start_loc, _, start_utc, end_utc = _bounds(tag)

            plans = task_service.get_tasks_between(start_utc, end_utc)

            text = _header(tag, start_loc) + "\n\n" + _format_plans(plans, tag)
            try:
                await bot.edit_message_text(
                    chat_id=config.CHANNEL_ID,
                    message_id=posts[tag],
                    text=text,
                )
            except TelegramBadRequest as exc:
                if "message is not modified" in exc.message.lower():
                    logger.debug("Channel post %s is already current", tag)
                    continue
                logger.exception("Could not update channel post %s", tag)
                raise
