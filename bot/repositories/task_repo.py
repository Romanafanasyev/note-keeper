# bot/repositories/task_repo.py
from sqlalchemy.orm import Session
from datetime import datetime
from bot.repositories.base_repo import BaseRepo
from bot.models.models import Plan
from typing import List

class TaskRepo(BaseRepo[Plan]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Plan)

    def get_scheduled_between(self, start: datetime, end: datetime) -> List[Plan]:
        return (
            self.session.query(Plan)
            .filter(
                Plan.state == "scheduled",
                Plan.ts_utc.between(start, end)
            )
            .order_by(Plan.ts_utc)
            .all()
        )

    def mark_deleted(self, task_id: int) -> bool:
        task = self.get(task_id)
        if task and task.state != "deleted":
            task.state = "deleted"
            self.session.commit()
            return True
        return False
