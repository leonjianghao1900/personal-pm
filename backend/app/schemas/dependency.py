from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DependencyCreate(BaseModel):
    predecessor_id: int
    dep_type: str = Field(default="FS", max_length=10)


class DependencyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    predecessor_id: int
    successor_id: int
    dep_type: str
    created_at: datetime
