# bot/db.py
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine
from bot.config import DB_PATH

Base = declarative_base()
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

def init_db():
    Base.metadata.create_all(engine, checkfirst=True)

