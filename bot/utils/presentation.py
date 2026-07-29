import datetime as dt
import html

from bot.core.config import config

MONTHS_GENITIVE = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)

MONTHS_NOMINATIVE = (
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


def task_local_datetime(task) -> dt.datetime:
    timestamp = task.ts_utc
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=dt.timezone.utc)
    return timestamp.astimezone(config.LOCAL_TZ)


def task_is_all_day(task) -> bool:
    value = getattr(task, "is_all_day", None)
    if value is not None:
        return bool(value)
    return task_local_datetime(task).time() == dt.time(0, 0)


def format_task_schedule(task) -> str:
    local = task_local_datetime(task)
    date = f"{local.day} {MONTHS_GENITIVE[local.month - 1]}"
    if task_is_all_day(task):
        return f"{date}, весь день"
    return f"{date}, {local:%H:%M}"


def task_card_text(task, *, prefix: str = "") -> str:
    heading = f"{prefix}\n\n" if prefix else ""
    return (
        f"{heading}<b>{html.escape(task.title)}</b>\n"
        f"📅 {format_task_schedule(task)}\n"
        f"<code>#{task.id}</code>"
    )


def task_button_text(task, *, max_length: int = 58) -> str:
    local = task_local_datetime(task)
    if task_is_all_day(task):
        lead = f"{local:%d.%m} · весь день"
    else:
        lead = f"{local:%d.%m %H:%M}"
    text = f"{lead} · {task.title}"
    if len(text) > max_length:
        return text[: max_length - 1].rstrip() + "…"
    return text
