import datetime as dt
from types import SimpleNamespace

from bot.core.config import config
from bot.services.reminders import (
    format_all_day_reminder,
    format_timed_reminder,
)


def _plan(title: str, local_time: dt.datetime):
    return SimpleNamespace(
        title=title,
        ts_utc=local_time.astimezone(dt.timezone.utc),
    )


def test_formats_24_hour_reminder():
    now = dt.datetime(2026, 7, 29, 18, 0, tzinfo=config.LOCAL_TZ)
    plan = _plan(
        "Приём <у врача>",
        dt.datetime(2026, 7, 30, 18, 0, tzinfo=config.LOCAL_TZ),
    )

    assert format_timed_reminder(plan, "24h", now=now) == (
        "🔔 <b>Приём &lt;у врача&gt;</b>\n\n"
        "<b>Через 24 часа</b>\n"
        "📅 <b>Завтра, 30 июля</b>\n"
        "🕒 <b>18:00</b>"
    )


def test_formats_90_minute_reminder():
    now = dt.datetime(2026, 7, 29, 16, 30, tzinfo=config.LOCAL_TZ)
    plan = _plan(
        "Приём у врача",
        dt.datetime(2026, 7, 29, 18, 0, tzinfo=config.LOCAL_TZ),
    )

    assert format_timed_reminder(plan, "90m", now=now) == (
        "⏰ <b>Приём у врача</b>\n\n"
        "<b>Через 1 час 30 минут</b>\n"
        "📅 <b>Сегодня</b>\n"
        "🕒 <b>18:00</b>"
    )


def test_formats_all_day_reminder():
    plan = SimpleNamespace(title="День рождения Маши")

    assert format_all_day_reminder(plan) == (
        "📅 <b>День рождения Маши</b>\n\n" "<b>Сегодня · весь день</b>"
    )
