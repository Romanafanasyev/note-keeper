# bot/scheduler/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot.core.config import config
from bot.services.reminders import send_reminders
from bot.services.updater import update_posts
from bot.utils.logger import logger


def setup_scheduler(bot):
    sched = AsyncIOScheduler(
        timezone=config.LOCAL_TZ,
        job_defaults={
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 120,
        },
    )

    logger.info("Initializing scheduler...")

    sched.add_job(
        update_posts,
        CronTrigger(hour=0, minute=2),
        args=[bot],
        id="daily_refresh",
        replace_existing=True,
    )

    sched.add_job(
        send_reminders,
        "interval",
        minutes=1,
        args=[bot],
        id="reminders",
        replace_existing=True,
    )

    sched.start()
    logger.info("Scheduler started.")
    return sched
