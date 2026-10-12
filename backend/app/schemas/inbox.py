from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InboxBase(BaseModel):
    kind: str = Field("idea", pattern="^(interrupt|idea)$")
    title: str = Field(min_length=1, max_length=200)
    notes: str | None = None
    priority: str = Field("normal", max_length=20)
    due_at: datetime | None = None
    project_id: int | None = None


class InboxCreate(InboxBase):
    pass


class InboxUpdate(BaseModel):
    title: str | None = None
    notes: str | None = None
    priority: str | None = None
    due_at: datetime | None = None
    project_id: int | None = None
    status: str | None = Field(default=None, pattern="^(active|completed|archived)$")


class InboxPromote(BaseModel):
    project_id: int | None = None
    name: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class InboxRead(InboxBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    promoted_task_id: int | None
    created_at: datetime
    completed_at: datetime | None