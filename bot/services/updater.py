import asyncio
import datetime as dt
import html

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from bot.core.config import config
from bot.core.db import SessionLocal
from bot.models.models import ChannelPost
from bot.repositories.channel_post_repo import ChannelPostRepo
from bot.repositories.task_repo import TaskRepo
from bot.services.channel_post_service import ChannelPostService
from bot.services.task_service import TaskService
from bot.utils.logger import logger
from bot.utils.presentation import task_is_all_day

# Telegram displays older messages above newer ones, so this order is intentional.
TAGS = ("next_month", "month", "week", "tomorrow", "today")
LEGACY_TAGS = ("month", "week", "tomorrow", "today")
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
MAX_PLANS_TEXT = 3_700


def _local_now():
    return dt.datetime.now(tz=config.LOCAL_TZ)


def _bounds(tag: str):
    today = _local_now().replace(hour=0, minute=0, second=0, microsecond=0)
    current_month = today.replace(day=1)
    next_month = (current_month + dt.timedelta(days=32)).replace(day=1)

    if tag == "today":
        start, end = today, today + dt.timedelta(days=1)
    elif tag == "tomorrow":
        start, end = today + dt.timedelta(days=1), today + dt.timedelta(days=2)
    elif tag == "week":
        start = today - dt.timedelta(days=today.weekday())
        end = start + dt.timedelta(days=7)
    elif tag == "next_month":
        start = next_month
        end = (next_month + dt.timedelta(days=32)).replace(day=1)
    else:
        start, end = current_month, next_month
    return (
        start,
        end,
        start.astimezone(dt.timezone.utc),
        end.astimezone(dt.timezone.utc),
    )


def _header(tag: str, start: dt.datetime):
    day = start.day
    month = MONTH_RU[start.month - 1].capitalize()
    if tag == "week":
        return "<b>📌 Планы на Неделю</b>\n"
    if tag == "today":
        return f"<b>📌 Планы на Сегодня — {day:02d} {month}</b>\n"
    if tag in {"month", "next_month"}:
        return f"<b>📌 Планы на {month}</b>\n"
    if tag == "tomorrow":
        return f"<b>📌 Планы на Завтра — {day:02d} {month}</b>\n"
    return f"<b>📅 {month} {start.year}</b>\n"


def _format_plans(rows, tag="month"):
    today = _local_now().replace(hour=0, minute=0, second=0, microsecond=0)
    lines = []
    visible = []
    for plan in rows:
        utc = plan.ts_utc
        if utc.tzinfo is None:
            utc = utc.replace(tzinfo=dt.timezone.utc)

        local = utc.astimezone(config.LOCAL_TZ)
        if local < today:
            continue
        visible.append((plan, local))

    omitted = 0
    for index, (plan, local) in enumerate(visible):
        weekday = WEEKDAYS[local.weekday()]
        date_str = f"{local.day:02d}.{local.month:02d}"

        if tag == "today":
            lead = "Весь день" if task_is_all_day(plan) else local.strftime("%H:%M")
        else:
            lead = f"{weekday} • {date_str}"
            if task_is_all_day(plan):
                lead += " • весь день"
            else:
                lead += f" • {local:%H:%M}"

        line = f"🕘 <b>{lead}</b> | {html.escape(plan.title)}"
        candidate = "\n".join([*lines, line])
        if len(candidate) > MAX_PLANS_TEXT:
            omitted = len(visible) - index
            break
        lines.append(line)

    if omitted:
        lines.append(f"… и ещё {omitted}")
    return "\n".join(lines) or "—"


def _replace_post_records(post_ids: dict[str, int]) -> None:
    with SessionLocal() as db_session:
        db_session.query(ChannelPost).delete()
        db_session.add_all(
            [ChannelPost(tag=tag, message_id=post_ids[tag]) for tag in TAGS]
        )
        db_session.commit()


def _legacy_post_mapping(
    old_posts: dict[str, int],
    new_today_message_id: int,
) -> dict[str, int]:
    """Shift the four old posts up and append one new bottom post."""

    return {
        "next_month": old_posts["month"],
        "month": old_posts["week"],
        "week": old_posts["tomorrow"],
        "tomorrow": old_posts["today"],
        "today": new_today_message_id,
    }


async def _migrate_legacy_posts(bot: Bot, old_posts: dict[str, int]) -> None:
    message = await bot.send_message(
        config.CHANNEL_ID,
        "⏳ Обновляю раздел «today»…",
    )
    try:
        _replace_post_records(_legacy_post_mapping(old_posts, message.message_id))
    except Exception:
        try:
            await bot.delete_message(config.CHANNEL_ID, message.message_id)
        except TelegramBadRequest:
            pass
        raise
    logger.info("Legacy channel posts migrated by appending one section")


async def _rebuild_posts(bot: Bot, old_posts: dict[str, int]) -> None:
    new_posts: dict[str, int] = {}
    try:
        for tag in TAGS:
            message = await bot.send_message(
                config.CHANNEL_ID,
                f"⏳ Обновляю раздел «{tag}»…",
            )
            new_posts[tag] = message.message_id
        _replace_post_records(new_posts)
    except Exception:
        for message_id in new_posts.values():
            try:
                await bot.delete_message(config.CHANNEL_ID, message_id)
            except TelegramBadRequest:
                pass
        raise

    for message_id in set(old_posts.values()):
        try:
            await bot.delete_message(config.CHANNEL_ID, message_id)
        except TelegramBadRequest:
            logger.warning("Could not delete obsolete channel post %s", message_id)

    logger.info("Channel post set rebuilt with %s sections", len(TAGS))


async def ensure_posts(bot: Bot):
    with SessionLocal() as db_session:
        existing = ChannelPostService(ChannelPostRepo(db_session)).get_all_posts()

    if all(tag in existing for tag in TAGS):
        return
    if "next_month" not in existing and all(tag in existing for tag in LEGACY_TAGS):
        await _migrate_legacy_posts(bot, existing)
        return
    await _rebuild_posts(bot, existing)


async def update_posts(bot: Bot):
    async with _update_lock:
        await _update_posts(bot)


async def try_update_posts(bot: Bot) -> bool:
    """Refresh the channel without hiding a successfully saved task from the user."""

    try:
        await update_posts(bot)
    except Exception:
        logger.exception("Deferred channel refresh after task mutation")
        return False
    return True


async def _update_posts(bot: Bot):
    await ensure_posts(bot)
    with SessionLocal() as db_session:
        task_service = TaskService(TaskRepo(db_session))
        posts = ChannelPostService(ChannelPostRepo(db_session)).get_all_posts()

        for tag in TAGS:
            start_local, _, start_utc, end_utc = _bounds(tag)
            plans = task_service.get_tasks_between(start_utc, end_utc)
            text = _header(tag, start_local) + "\n\n" + _format_plans(plans, tag)
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
