from bot.core.config import config
from bot.scheduler.scheduler import daily_refresh_trigger


def test_daily_refresh_uses_configured_timezone():
    trigger = daily_refresh_trigger()

    assert trigger.timezone == config.LOCAL_TZ
