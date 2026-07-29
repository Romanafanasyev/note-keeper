import datetime as dt
from types import SimpleNamespace

from bot.handlers import list as list_handler
from bot.services import updater
from bot.services.updater import TAGS, _format_plans, _legacy_post_mapping


def test_next_month_is_the_top_channel_section(monkeypatch):
    fixed_now = dt.datetime(
        2026,
        7,
        29,
        12,
        tzinfo=dt.timezone(dt.timedelta(hours=3)),
    )
    monkeypatch.setattr(updater, "_local_now", lambda: fixed_now)

    start, end, _, _ = updater._bounds("next_month")

    assert TAGS[0] == "next_month"
    assert start.date() == dt.date(2026, 8, 1)
    assert end.date() == dt.date(2026, 9, 1)
    assert "Август" in updater._header("next_month", start)


def test_legacy_channel_posts_are_reused_in_the_new_order():
    old_posts = {
        "month": 39,
        "week": 40,
        "tomorrow": 41,
        "today": 42,
    }

    assert _legacy_post_mapping(old_posts, 43) == {
        "next_month": 39,
        "month": 40,
        "week": 41,
        "tomorrow": 42,
        "today": 43,
    }


def test_week_filter_means_the_next_seven_days(monkeypatch):
    fixed_today = dt.datetime(
        2026,
        7,
        29,
        tzinfo=dt.timezone(dt.timedelta(hours=3)),
    )
    monkeypatch.setattr(list_handler, "_local_midnight", lambda: fixed_today)

    start, end = list_handler._filter_bounds("week")

    assert start == fixed_today
    assert end == fixed_today + dt.timedelta(days=7)


def test_all_day_channel_plan_has_no_fake_time():
    plan = SimpleNamespace(
        ts_utc=dt.datetime(2030, 1, 1, 21, 0, tzinfo=dt.timezone.utc),
        title="День рождения",
        description="legacy comment",
        is_all_day=True,
    )

    output = _format_plans([plan], tag="month")

    assert "весь день" in output
    assert "00:00" not in output
    assert "legacy comment" not in output
