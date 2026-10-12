from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    parent_id: int | None = None
    status: str = "todo"
    priority: str = "normal"
    start_date: date | None = None
    end_date: date | None = None
    progress: int = Field(0, ge=0, le=100)
    is_milestone: bool = False
    sort_order: int = 0


class TaskCreate(TaskBase):
    project_id: int | None = None


class TaskUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    parent_id: int | None = None
    status: str | None = None
    priority: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    progress: int | None = Field(None, ge=0, le=100)
    is_milestone: bool | None = None
    sort_order: int | None = None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: object) -> object:
        if value is None:
            raise ValueError("name cannot be null")
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("name cannot be empty")
        return value


class TaskMove(BaseModel):
    """拖拽改日期"""
    start_date: date
    end_date: date


class TaskRead(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime
