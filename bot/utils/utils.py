# bot/utils/utils.py
import datetime as dt
import re

from aiogram import types

from bot.core.config import config

DATE_RE = re.compile(r"(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?(?:\s+(\d{1,2}):(\d{2}))?")
ID_RE = re.compile(r"#(\d{1,6})")


def parse_user_datetime(text: str) -> dt.datetime | None:
    """
    Принимает строки вида:
      22.05 21:30
      22.05.2025
      22.05
    Возвращает datetime в UTC.
    """
    m = DATE_RE.fullmatch(text.strip())
    if not m:
        return None

    day, month, year, hour, minute = m.groups()
    now = dt.datetime.now(config.LOCAL_TZ)
    year = int(year) if year else now.year
    hour = int(hour) if hour else 0
    minute = int(minute) if minute else 0

    try:
        local_dt = dt.datetime(
            year, int(month), int(day), hour, minute, tzinfo=config.LOCAL_TZ
        )
    except ValueError:
        return None
    return local_dt.astimezone(dt.timezone.utc)


def parse_time_input(text: str) -> dt.time | None:
    """Parse strict, unambiguous time forms: 22, 2217, 22 17, 22:17."""

    raw = text.strip()
    hour: int
    minute: int

    if re.fullmatch(r"\d{1,2}", raw):
        hour, minute = int(raw), 0
    elif re.fullmatch(r"\d{3,4}", raw):
        hour, minute = int(raw[:-2]), int(raw[-2:])
    else:
        match = re.fullmatch(r"(\d{1,2})[:\s](\d{2})", raw)
        if not match:
            return None
        hour, minute = map(int, match.groups())

    if hour > 23 or minute > 59:
        return None
    return dt.time(hour, minute)


def local_schedule_to_utc(date: dt.date, time: dt.time) -> dt.datetime:
    local = dt.datetime.combine(date, time, tzinfo=config.LOCAL_TZ)
    return local.astimezone(dt.timezone.utc)


def extract_id(text: str | None) -> int | None:
    """Вернёт int ID, если в тексте есть #123."""
    if not text:
        return None
    m = ID_RE.search(text)
    return int(m.group(1)) if m else None


def parse_id_or_reply(msg: types.Message) -> int | None:
    """Получить ID либо из аргумента команды, либо из reply."""
    cmd, *args = msg.text.split(maxsplit=1)
    if args and args[0].isdigit():
        return int(args[0])

    if msg.reply_to_message:
        return extract_id(msg.reply_to_message.text)
    return None
