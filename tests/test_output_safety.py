import datetime as dt
from types import SimpleNamespace

from bot.core.config import config
from bot.services.updater import _format_plans


def test_channel_output_escapes_task_html():
    future = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)
    plan = SimpleNamespace(
        ts_utc=future,
        title="<b>not markup</b>",
        description="<a href='bad'>description</a>",
    )

    output = _format_plans([plan], tag="month")

    assert "<b>not markup</b>" not in output
    assert "&lt;b&gt;not markup&lt;/b&gt;" in output
    assert "&lt;a href=&#x27;bad&#x27;&gt;description&lt;/a&gt;" in output
    assert str(config.LOCAL_TZ) == "Europe/Moscow"
