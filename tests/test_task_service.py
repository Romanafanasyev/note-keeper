import datetime as dt
import zoneinfo

import pytest

from bot.models.models import Plan, State
from bot.repositories.task_repo import TaskRepo
from bot.services.task_service import TaskService, CreateTaskDTO, EditTaskDTO
from tests.utils import get_test_session

TZ = zoneinfo.ZoneInfo("Europe/Moscow")

@pytest.fixture
def task_service():
    session = get_test_session()
    repo = TaskRepo(session)
    return TaskService(repo)

def test_create_task(task_service):
    now = dt.datetime.now(tz=TZ)
    dto = CreateTaskDTO(
        title="Test",
        datetime=now,
        description="abc"
    )
    task = task_service.create(dto)
    assert task.id is not None
    assert task.title == "Test"
    assert task.description == "abc"
    assert task.state == State.scheduled

def test_edit_title(task_service):
    now = dt.datetime.now(tz=TZ)
    dto = CreateTaskDTO(title="Orig", datetime=now, description=None)
    task = task_service.create(dto)

    dto = EditTaskDTO(task_id=task.id, field="title", new_value="Changed")
    updated = task_service.edit_task(dto)
    assert updated.title == "Changed"

def test_edit_description(task_service):
    now = dt.datetime.now(tz=TZ)
    dto = CreateTaskDTO(title="Orig", datetime=now, description="desc")
    task = task_service.create(dto)

    dto = EditTaskDTO(task_id=task.id, field="description", new_value="New desc")
    updated = task_service.edit_task(dto)
    assert updated.description == "New desc"

def test_edit_datetime(task_service):
    now = dt.datetime.now(tz=TZ)
    dto = CreateTaskDTO(title="Orig", datetime=now, description=None)
    task = task_service.create(dto)

    new_dt = now + dt.timedelta(hours=1)
    dto = EditTaskDTO(task_id=task.id, field="datetime", new_value=new_dt.isoformat())
    updated = task_service.edit_task(dto)

    # ✅ Сравниваем с new_dt, а не с task.ts_utc (они — один объект)
    assert updated.ts_utc == new_dt.replace(tzinfo=None)
    assert updated.reminded_24h is False
    assert updated.reminded_90m is False


def test_edit_invalid_field(task_service):
    now = dt.datetime.now(tz=TZ)
    dto = CreateTaskDTO(title="Orig", datetime=now, description=None)
    task = task_service.create(dto)

    dto = EditTaskDTO(task_id=task.id, field="wrong", new_value="123")
    with pytest.raises(ValueError):
        task_service.edit_task(dto)
