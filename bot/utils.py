# bot/utils.py
import re, datetime as dt
from bot.config import LOCAL_TZ

DATE_RE = re.compile(r"(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?(?:\s+(\d{1,2}):(\d{2}))?")

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
