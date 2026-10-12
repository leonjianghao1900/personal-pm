from pydantic import BaseModel, ConfigDict, Field


class CostCategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    color: str = Field(default="#8e8e93", pattern="^#[0-9a-fA-F]{6}$")
    sort_order: int = 0


class CostCategoryCreate(CostCategoryBase):
    pass


class CostCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    color: str | None = Field(default=None, pattern="^#[0-9a-fA-F]{6}$")
    sort_order: int | None = None


class CostCategoryRead(CostCategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_builtin: bool
