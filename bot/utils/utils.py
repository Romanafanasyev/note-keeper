# bot/utils/utils.py
import datetime as dt
import re

from aiogram import types

from bot.core.config import LOCAL_TZ

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
    now = dt.datetime.now()
    year = int(year) if year else now.year
    hour = int(hour) if hour else 0
    minute = int(minute) if minute else 0

    local_dt = dt.datetime(year, int(month), int(day), hour, minute, tzinfo=LOCAL_TZ)
    return local_dt.astimezone(dt.timezone.utc)


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
