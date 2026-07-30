from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import date, datetime
from typing import Optional, List
from app.models.expense import ExpenseStatus
from app.schemas.category import CategoryResponse
from app.schemas.user import UserResponse


class ExpenseBase(BaseModel):
    category_id: int
    amount: float = Field(..., gt=0, example=120.50)
    currency: str = Field(default="USD", max_length=3, example="USD")
    expense_date: date = Field(..., example="2026-07-28")
    merchant: str = Field(..., min_length=1, max_length=255, example="Delta Airlines")
    description: Optional[str] = Field(default=None, max_length=500, example="Flight ticket for tech conference")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Expense amount must be strictly greater than zero")
        return round(v, 2)


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    category_id: Optional[int] = None
    amount: Optional[float] = Field(default=None, gt=0)
    currency: Optional[str] = Field(default=None, max_length=3)
    expense_date: Optional[date] = None
    merchant: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=500)


class ExpenseResponse(ExpenseBase):
    id: int
    employee_id: int
    status: ExpenseStatus
    receipt_filename: Optional[str] = None
    receipt_url: Optional[str] = None
    receipt_hash: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    category: Optional[CategoryResponse] = None
    employee: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)


class ExpenseFilterParams(BaseModel):
    status: Optional[ExpenseStatus] = None
    category_id: Optional[int] = None
    department_id: Optional[int] = None
    employee_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    search_query: Optional[str] = None
