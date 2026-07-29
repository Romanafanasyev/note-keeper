import datetime as dt

from bot.utils.utils import parse_time_input, parse_user_datetime


def test_parse_user_datetime_rejects_invalid_calendar_date():
    assert parse_user_datetime("31.02 10:00") is None


def test_parse_user_datetime_returns_utc():
    parsed = parse_user_datetime("01.01.2030 12:30")

    assert parsed == dt.datetime(2030, 1, 1, 9, 30, tzinfo=dt.timezone.utc)


def test_parse_time_input_accepts_short_strict_forms():
    expected = dt.time(22, 17)
    assert parse_time_input("2217") == expected
    assert parse_time_input("22 17") == expected
    assert parse_time_input("22:17") == expected
    assert parse_time_input("22") == dt.time(22, 0)


def test_parse_time_input_rejects_ambiguous_or_invalid_values():
    assert parse_time_input("завтра вечером") is None
    assert parse_time_input("24:00") is None
    assert parse_time_input("12:7") is None
