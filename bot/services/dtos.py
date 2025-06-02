# bot/services/dtos.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CreateTaskDTO(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    datetime: datetime
    description: Optional[str] = None


class EditTaskDTO(BaseModel):
    task_id: int
    field: str
    new_value: str


class CreateChannelPostDTO(BaseModel):
    tag: str
    message_id: int
