import io
from unittest.mock import patch

from bot import health

TOKEN = "123456789:abcdefghijklmnopqrstuvwxyzABCDE"


def test_healthcheck_accepts_valid_telegram_response(monkeypatch, capsys):
    monkeypatch.setenv("BOT_TOKEN", TOKEN)
    response = io.BytesIO(b'{"ok": true, "result": {"id": 123456789}}')

    with patch("bot.health.urlopen", return_value=response):
        assert health.main() == 0

    assert capsys.readouterr().out.strip() == "ok"


def test_healthcheck_never_prints_token(monkeypatch, capsys):
    monkeypatch.setenv("BOT_TOKEN", TOKEN)

    with patch("bot.health.urlopen", side_effect=RuntimeError(TOKEN)):
        assert health.main() == 1

    output = capsys.readouterr()
    assert TOKEN not in output.err
    assert output.err.strip() == "healthcheck failed: RuntimeError"
