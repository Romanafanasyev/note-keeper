# bot/services/dtos.py
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class CreateTaskDTO(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    datetime: datetime
    description: Optional[str] = Field(default=None, max_length=1_000)


class EditTaskDTO(BaseModel):
    task_id: int = Field(gt=0)
    field: Literal["title", "datetime", "description"]
    new_value: str = Field(max_length=1_000)

    @model_validator(mode="after")
    def validate_title(self):
        if self.field == "title":
            if not self.new_value.strip():
                raise ValueError("Title must not be empty.")
            if len(self.new_value) > 120:
                raise ValueError("Title must not exceed 120 characters.")
        return self


class CreateChannelPostDTO(BaseModel):
    tag: str
    message_id: int
