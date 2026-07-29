import datetime as dt
import html

from bot.core.config import config
from bot.core.db import SessionLocal
from bot.repositories.task_repo import TaskRepo
from bot.services.task_service import TaskService
from bot.utils.presentation import task_is_all_day

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

        async def _notify(plan, time_left: str):
            local_time = _as_local(plan.ts_utc)
            await bot.send_message(
                config.USER_ID,
                f"⏰ Через {time_left}:\n<b>{html.escape(plan.title)}</b>\n"
                f"{local_time:%d.%m %H:%M}",
            )

        for plan in plans_24h:
            await _notify(plan, "24 часа")
            task_service.set_reminded(plan.id, reminded_24h=True)

        for plan in plans_90m:
            await _notify(plan, "90 минут")
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
                f"📅 Сегодня:\n<b>{html.escape(plan.title)}</b>",
            )
            task_service.set_reminded(plan.id, reminded_90m=True)
