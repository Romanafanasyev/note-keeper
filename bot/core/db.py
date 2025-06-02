# bot/core/db.py
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()
db_path = os.path.join(os.path.dirname(__file__), "../../data/plan.db")
engine = create_engine(f"sqlite:///{db_path}", echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


def init_db():
    Base.metadata.create_all(engine, checkfirst=True)
