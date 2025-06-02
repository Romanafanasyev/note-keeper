# bot/reminders.py

import datetime as dt
from bot.config import LOCAL_TZ, USER_ID
from bot.db import SessionLocal
from bot.models import Plan

# ──────────────────────────────────────────────
def next_due(delta_min: int) -> tuple[dt.datetime, dt.datetime]:
    """
    Возвращает окно (UTC) шириной 1 мин, заканчивающееся через delta_min
    от локального (МСК) 'сейчас'.
    """
    now_local = dt.datetime.now(LOCAL_TZ)
    target_local = now_local + dt.timedelta(minutes=delta_min)
    window_start_local = target_local
    window_end_local   = target_local + dt.timedelta(minutes=1)

    # конвертируем в UTC для сравнения с Plan.ts_utc
    return (
        window_start_local.astimezone(dt.timezone.utc),
        window_end_local.astimezone(dt.timezone.utc),
    )
# ──────────────────────────────────────────────

async def send_reminders(bot):
    with SessionLocal() as db:

        # ---- -24 ч ----------------------------------------------------------
        ws24, we24 = next_due(24 * 60)
        plans_24h = db.query(Plan).filter(
            Plan.state == "scheduled",
            Plan.ts_utc.between(ws24, we24),
            Plan.reminded_24h.is_(False)
        ).all()

        # ---- -90 мин --------------------------------------------------------
        ws90, we90 = next_due(90)
        plans_90m = db.query(Plan).filter(
            Plan.state == "scheduled",
            Plan.ts_utc.between(ws90, we90),
            Plan.reminded_90m.is_(False)
        ).all()

        # ---- отправляем -----------------------------------------------------
        users = [USER_ID]

        async def _notify(plan, time_left: str):
            local_time = plan.ts_utc.astimezone(LOCAL_TZ)
            for uid in users:
                await bot.send_message(
                    uid,
                    f"⏰ Через {time_left}:\n<b>{plan.title}</b>\n{local_time:%d.%m %H:%M}"
                )

        for p in plans_24h:
            await _notify(p, "24 часа")
            p.reminded_24h = True

        for p in plans_90m:
            await _notify(p, "90 минут")
            p.reminded_90m = True

        db.commit()
