# bot/services/reminders.py
import datetime as dt

from bot.core.config import LOCAL_TZ, USER_ID
from bot.core.db import SessionLocal
from bot.repositories.task_repo import TaskRepo
from bot.services.task_service import TaskService


def next_due(delta_min: int) -> tuple[dt.datetime, dt.datetime]:
    now_local = dt.datetime.now(LOCAL_TZ)
    target_local = now_local + dt.timedelta(minutes=delta_min)
    window_start_local = target_local
    window_end_local = target_local + dt.timedelta(minutes=1)

    return (
        window_start_local.astimezone(dt.timezone.utc),
        window_end_local.astimezone(dt.timezone.utc),
    )


async def send_reminders(bot):
    with SessionLocal() as db_session:
        task_service = TaskService(TaskRepo(db_session))

        ws24, we24 = next_due(24 * 60)
        plans_24h = [
            p for p in task_service.get_tasks_between(ws24, we24) if not p.reminded_24h
        ]

        ws90, we90 = next_due(90)
        plans_90m = [
            p for p in task_service.get_tasks_between(ws90, we90) if not p.reminded_90m
        ]

        users = [USER_ID]

        async def _notify(plan, time_left: str):
            local_time = plan.ts_utc.astimezone(LOCAL_TZ)
            for uid in users:
                await bot.send_message(
                    uid,
                    f"⏰ Через {time_left}:\n<b>{plan.title}</b>\n{local_time:%d.%m %H:%M}",
                )

        for p in plans_24h:
            await _notify(p, "24 часа")
            task_service.set_reminded(p.id, reminded_24h=True)

        for p in plans_90m:
            await _notify(p, "90 минут")
            task_service.set_reminded(p.id, reminded_90m=True)
