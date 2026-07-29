import pytest
from pydantic import ValidationError

from bot.core.config import Config

VALID_SETTINGS = {
    "BOT_TOKEN": "123456789:abcdefghijklmnopqrstuvwxyzABCDE",
    "CHANNEL_ID": "-1001234567890",
    "USER_ID": 123456789,
}


def test_config_accepts_valid_settings():
    settings = Config(_env_file=None, **VALID_SETTINGS)

    assert settings.USER_ID == 123456789
    assert settings.CHANNEL_ID == "-1001234567890"
    assert str(settings.LOCAL_TZ) == "Europe/Moscow"
    assert "abcdefghijklmnopqrstuvwxyz" not in repr(settings.BOT_TOKEN)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("BOT_TOKEN", "stub"),
        ("CHANNEL_ID", "   "),
        ("USER_ID", 0),
        ("TIMEZONE", "Not/A_Timezone"),
    ],
)
def test_config_rejects_invalid_settings(field, value):
    values = {**VALID_SETTINGS, field: value}
    with pytest.raises(ValidationError):
        Config(_env_file=None, **values)
