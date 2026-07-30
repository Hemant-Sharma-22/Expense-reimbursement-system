from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional


class DepartmentBase(BaseModel):
    name: str = Field(..., example="Engineering")
    code: str = Field(..., example="ENG")
    budget: float = Field(default=0.0, ge=0, example=50000.0)


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    budget: Optional[float] = Field(default=None, ge=0)


class DepartmentResponse(DepartmentBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
