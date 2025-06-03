# bot/core/config.py
from pathlib import Path
from typing import ClassVar
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    # Токен Телеграм-бота
    BOT_TOKEN: str

    # ID Канала, в котором будут публиковаться планы
    CHANNEL_ID: str

    # ID Пользователя, которому будут приходить уведомления
    USER_ID: int

    # Часовой пояс
    LOCAL_TZ: ClassVar[ZoneInfo] = ZoneInfo("Europe/Moscow")

    @property
    def BASE_DIR(self) -> Path:
        return Path(__file__).resolve().parent.parent.parent

    @property
    def DB_PATH(self) -> Path:
        return self.BASE_DIR / "data" / "plan.db"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


config = Config()
