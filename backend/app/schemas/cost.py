from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CostBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: str = Field("other", max_length=20)
    amount: float = Field(gt=0)
    description: str | None = None
    spent_at: date
    task_id: int | None = None

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


class CostCreate(CostBase):
    project_id: int


class CostUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    category: str | None = Field(default=None, max_length=20)
    amount: float | None = Field(default=None, gt=0)
    description: str | None = None
    spent_at: date | None = None
    task_id: int | None = None
    project_id: int | None = None

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


class CostRead(CostBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    created_at: datetime
