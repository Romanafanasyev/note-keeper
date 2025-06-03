# bot/services/task_service.py
from datetime import datetime
from typing import List

from bot.models.models import Plan, State
from bot.repositories.task_repo import TaskRepo
from bot.services.dtos import CreateTaskDTO, EditTaskDTO


class TaskService:
    def __init__(self, repo: TaskRepo):
        self.repo = repo

    def create(self, dto: CreateTaskDTO) -> Plan:
        task = Plan(
            title=dto.title,
            ts_utc=dto.datetime,
            description=dto.description,
            state=State.scheduled,
        )
        return self.repo.create(task)

    def edit_task(self, dto: EditTaskDTO) -> Plan:
        task = self.repo.get(dto.task_id)
        if not task or task.state == State.deleted:
            raise ValueError("Task not found or deleted.")

        if dto.field == "title":
            task.title = dto.new_value
        elif dto.field == "description":
            task.description = dto.new_value or None
        elif dto.field == "datetime":
            task.ts_utc = datetime.fromisoformat(dto.new_value)
            task.reminded_24h = False
            task.reminded_90m = False
        else:
            raise ValueError("Invalid field specified.")

        return self.repo.update(task)

    def delete_task(self, task_id: int) -> bool:
        return self.repo.mark_deleted(task_id)

    def get_tasks_between(self, start: datetime, end: datetime) -> List[Plan]:
        return self.repo.get_scheduled_between(start, end)

    def set_reminded(
        self,
        task_id: int,
        reminded_24h: bool = None,
        reminded_90m: bool = None,
    ):
        task = self.repo.get(task_id)
        if not task:
            raise ValueError("Task not found.")
        if reminded_24h is not None:
            task.reminded_24h = reminded_24h
        if reminded_90m is not None:
            task.reminded_90m = reminded_90m
        return self.repo.update(task)
