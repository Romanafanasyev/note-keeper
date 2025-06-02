# bot/config.py
from dotenv import load_dotenv
import os
from zoneinfo import ZoneInfo

load_dotenv()

# Токен Телеграм-бота
BOT_TOKEN   = os.getenv("BOT_TOKEN")

# ID Канала, в котором будут публиковаться планы
CHANNEL_ID  = os.getenv("CHANNEL_ID")

# Часовой пояс
LOCAL_TZ = ZoneInfo("Europe/Moscow")

# ID Пользователя, которому будут приходить уведомления
USER_ID = os.getenv("USER_ID")
