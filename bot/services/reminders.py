import datetime as dt
import html

from bot.core.config import config
from bot.core.db import SessionLocal
from bot.repositories.task_repo import TaskRepo
from bot.services.task_service import TaskService
from bot.utils.presentation import MONTHS_GENITIVE, task_is_all_day

ALL_DAY_REMINDER_TIME = dt.time(9, 0)


def next_due(delta_min: int) -> tuple[dt.datetime, dt.datetime]:
    now_local = dt.datetime.now(config.LOCAL_TZ)
    target_local = now_local + dt.timedelta(minutes=delta_min)
    window_end_local = target_local + dt.timedelta(minutes=1)

    return (
        target_local.astimezone(dt.timezone.utc),
        window_end_local.astimezone(dt.timezone.utc),
    )


def _as_local(timestamp: dt.datetime) -> dt.datetime:
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=dt.timezone.utc)
    return timestamp.astimezone(config.LOCAL_TZ)


def _date_label(event_time: dt.datetime, now: dt.datetime) -> str:
    event_date = event_time.date()
    today = now.date()
    if event_date == today:
        return "Сегодня"
    if event_date == today + dt.timedelta(days=1):
        month = MONTHS_GENITIVE[event_time.month - 1]
        return f"Завтра, {event_time.day} {month}"
    return f"{event_time.day} {MONTHS_GENITIVE[event_time.month - 1]}"


def format_timed_reminder(
    plan,
    reminder_kind: str,
    *,
    now: dt.datetime | None = None,
) -> str:
    local_time = _as_local(plan.ts_utc)
    now_local = now or dt.datetime.now(config.LOCAL_TZ)
    if reminder_kind == "24h":
        icon = "🔔"
        time_left = "Через 24 часа"
    elif reminder_kind == "90m":
        icon = "⏰"
        time_left = "Через 1 час 30 минут"
    else:
        raise ValueError(f"Unknown reminder kind: {reminder_kind}")

    title = html.escape(plan.title)
    date_label = _date_label(local_time, now_local)
    return (
        f"{icon} <b>{title}</b>\n\n"
        f"<b>{time_left}</b>\n"
        f"📅 <b>{date_label}</b>\n"
        f"🕒 <b>{local_time:%H:%M}</b>"
    )


def format_all_day_reminder(plan) -> str:
    title = html.escape(plan.title)
    return f"📅 <b>{title}</b>\n\n<b>Сегодня · весь день</b>"


async def send_reminders(bot):
    with SessionLocal() as db_session:
        task_service = TaskService(TaskRepo(db_session))

        window_24h = next_due(24 * 60)
        plans_24h = [
            plan
            for plan in task_service.get_tasks_between(*window_24h)
            if not plan.reminded_24h and not task_is_all_day(plan)
        ]

        window_90m = next_due(90)
        plans_90m = [
            plan
            for plan in task_service.get_tasks_between(*window_90m)
            if not plan.reminded_90m and not task_is_all_day(plan)
        ]

        async def _notify(plan, reminder_kind: str):
            await bot.send_message(
                config.USER_ID,
                format_timed_reminder(plan, reminder_kind),
            )

        for plan in plans_24h:
            await _notify(plan, "24h")
            task_service.set_reminded(plan.id, reminded_24h=True)

        for plan in plans_90m:
            await _notify(plan, "90m")
            task_service.set_reminded(plan.id, reminded_90m=True)

        now_local = dt.datetime.now(config.LOCAL_TZ)
        if now_local.time() < ALL_DAY_REMINDER_TIME:
            return
        today = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        all_day_plans = [
            plan
            for plan in task_service.get_tasks_between(
                today.astimezone(dt.timezone.utc),
                (today + dt.timedelta(days=1)).astimezone(dt.timezone.utc),
            )
            if task_is_all_day(plan) and not plan.reminded_90m
        ]
        for plan in all_day_plans:
            await bot.send_message(
                config.USER_ID,
                format_all_day_reminder(plan),
            )
            task_service.set_reminded(plan.id, reminded_90m=True)
