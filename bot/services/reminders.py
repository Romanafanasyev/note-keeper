# bot/services/reminders.py
import datetime as dt

from bot.core.config import LOCAL_TZ, USER_ID
from bot.core.db import SessionLocal
from bot.repositories.task_repo import TaskRepo


def next_due(delta_min: int) -> tuple[dt.datetime, dt.datetime]:
    """
    Возвращает окно (UTC) шириной 1 мин, заканчивающееся через delta_min
    от локального (МСК) 'сейчас'.
    """
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
        task_repo = TaskRepo(db_session)

        ws24, we24 = next_due(24 * 60)
        plans_24h = task_repo.get_scheduled_between(ws24, we24)
        plans_24h = [p for p in plans_24h if not p.reminded_24h]

        ws90, we90 = next_due(90)
        plans_90m = task_repo.get_scheduled_between(ws90, we90)
        plans_90m = [p for p in plans_90m if not p.reminded_90m]

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
            p.reminded_24h = True
            task_repo.update(p)

        for p in plans_90m:
            await _notify(p, "90 минут")
            p.reminded_90m = True
            task_repo.update(p)
