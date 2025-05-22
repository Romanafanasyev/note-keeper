# bot/config.py
from dotenv import load_dotenv
import os, pathlib
from zoneinfo import ZoneInfo

load_dotenv()

BOT_TOKEN   = os.getenv("BOT_TOKEN")
CHANNEL_ID  = os.getenv("CHANNEL_ID")
TZ_OFFSET   = int(os.getenv("TZ_OFFSET", 0))
LOCAL_TZ = ZoneInfo("Europe/Moscow")

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
DB_PATH  = BASE_DIR / "plan.db"

USER_ID = os.getenv("USER_ID")
