# bot/core/config.py
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    BOT_TOKEN: SecretStr

    CHANNEL_ID: str

    USER_ID: int = Field(gt=0)

    TIMEZONE: str = "Europe/Moscow"

    @field_validator("BOT_TOKEN")
    @classmethod
    def validate_bot_token(cls, value: SecretStr) -> SecretStr:
        token = value.get_secret_value()
        bot_id, separator, secret = token.partition(":")
        if not separator or not bot_id.isdigit() or len(secret) < 30:
            raise ValueError("BOT_TOKEN has an invalid Telegram token format")
        return value

    @field_validator("CHANNEL_ID")
    @classmethod
    def validate_channel_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("CHANNEL_ID must not be empty")
        return value.strip()

    @field_validator("TIMEZONE")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unknown timezone: {value}") from exc
        return value

    @property
    def LOCAL_TZ(self) -> ZoneInfo:
        return ZoneInfo(self.TIMEZONE)

    @property
    def BASE_DIR(self) -> Path:
        return Path(__file__).resolve().parent.parent.parent

    @property
    def DB_PATH(self) -> Path:
        return self.BASE_DIR / "data" / "plan.db"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


config = Config()
