# bot/core/db.py
import datetime as dt

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
    _migrate_all_day()


def _migrate_all_day(database_engine=engine) -> None:
    """Add the all-day flag and infer it for existing local-midnight tasks."""

    with database_engine.begin() as connection:
        columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(plans)").fetchall()
        }
        if "is_all_day" in columns:
            return

        connection.exec_driver_sql(
            "ALTER TABLE plans " "ADD COLUMN is_all_day BOOLEAN NOT NULL DEFAULT 0"
        )
        rows = connection.exec_driver_sql("SELECT id, ts_utc FROM plans").fetchall()
        all_day_ids = []
        for task_id, raw_timestamp in rows:
            timestamp = (
                raw_timestamp
                if isinstance(raw_timestamp, dt.datetime)
                else dt.datetime.fromisoformat(raw_timestamp)
            )
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=dt.timezone.utc)
            local = timestamp.astimezone(config.LOCAL_TZ)
            if local.time() == dt.time(0, 0):
                all_day_ids.append(task_id)

        for task_id in all_day_ids:
            connection.exec_driver_sql(
                "UPDATE plans SET is_all_day = 1 WHERE id = ?",
                (task_id,),
            )
