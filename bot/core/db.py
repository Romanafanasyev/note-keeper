# bot/core/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from bot.core.config import config

Base = declarative_base()
engine = create_engine(f"sqlite:///{config.DB_PATH}", echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


def init_db():
    Base.metadata.create_all(engine, checkfirst=True)
