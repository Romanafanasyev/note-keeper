# bot/utils/logger.py
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_PATH.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_PATH / "bot.log"

logger = logging.getLogger("planbot")
logger.setLevel(logging.INFO)

file_handler = RotatingFileHandler(
    LOG_FILE, maxBytes=5_000_000, backupCount=3
)
formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
