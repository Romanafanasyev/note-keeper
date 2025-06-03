# tests/test_task_repo.py
import datetime as dt
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bot.models.models import Base, Plan, State
from bot.repositories.task_repo import TaskRepo

TZ = ZoneInfo("Europe/Moscow")


def get_test_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    return TestingSessionLocal()


def test_create_and_get():
    session = get_test_session()
    repo = TaskRepo(session)

    now = dt.datetime.now(tz=TZ)
    task = Plan(
        title="test",
        ts_utc=now.astimezone(dt.timezone.utc).replace(tzinfo=None),
    )

    created = repo.create(task)
    assert created.id is not None

    loaded = repo.get(created.id)
    assert loaded.title == "test"
    assert loaded.ts_utc == task.ts_utc


def test_get_scheduled_between():
    session = get_test_session()
    repo = TaskRepo(session)

    now = dt.datetime.now(tz=TZ)
    repo.create(Plan(title="a", ts_utc=now))
    repo.create(Plan(title="b", ts_utc=now + dt.timedelta(hours=1)))
    repo.create(Plan(title="c", ts_utc=now + dt.timedelta(days=1)))

    results = repo.get_scheduled_between(now, now + dt.timedelta(hours=2))
    assert len(results) == 2
    assert results[0].title == "a"
    assert results[1].title == "b"


def test_mark_deleted():
    session = get_test_session()
    repo = TaskRepo(session)
    now = dt.datetime.now(tz=TZ)

    task = repo.create(Plan(title="to delete", ts_utc=now))
    assert task.state == State.scheduled

    deleted = repo.mark_deleted(task.id)
    assert deleted is True

    again = repo.mark_deleted(task.id)
    assert again is False
