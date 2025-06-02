# bot/scheduler/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from bot.services.updater import update_posts
from bot.services.reminders import send_reminders
from bot.core.config import LOCAL_TZ

def setup_scheduler(bot):
    sched = AsyncIOScheduler(timezone=LOCAL_TZ)

    # ежедневный рефреш постов
    sched.add_job(update_posts,
                  CronTrigger(hour=0, minute=2),
                  args=[bot],
                  id="daily_refresh")

    # проверка напоминаний каждую минуту
    sched.add_job(send_reminders, "interval", minutes=1, args=[bot])

    sched.start()
    return sched
