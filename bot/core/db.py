# bot/core/db.py
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from bot.core.config import config

Base = declarative_base()
engine = create_engine(
    f"sqlite:///{config.DB_PATH}",
    connect_args={"timeout": 30},
    echo=False,
    future=True,
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


@event.listens_for(engine, "connect")
def configure_sqlite(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def init_db():
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine, checkfirst=True)
