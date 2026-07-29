import datetime as dt

from bot.utils.utils import parse_user_datetime


def test_parse_user_datetime_rejects_invalid_calendar_date():
    assert parse_user_datetime("31.02 10:00") is None


def test_parse_user_datetime_returns_utc():
    parsed = parse_user_datetime("01.01.2030 12:30")

    assert parsed == dt.datetime(2030, 1, 1, 9, 30, tzinfo=dt.timezone.utc)
