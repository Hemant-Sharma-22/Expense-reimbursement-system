from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional


class CategoryBase(BaseModel):
    name: str = Field(..., example="Travel")
    description: Optional[str] = Field(default=None, example="Flight, train, or taxi expenses")
    max_limit_amount: Optional[float] = Field(default=None, ge=0, example=1500.0)


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    max_limit_amount: Optional[float] = Field(default=None, ge=0)


class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
