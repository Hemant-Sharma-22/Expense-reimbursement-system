from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional
from app.models.reimbursement_request import RequestStatus
from app.schemas.expense import ExpenseResponse
from app.schemas.user import UserResponse


class SubmitRequestSchema(BaseModel):
    expense_id: int = Field(..., description="ID of draft expense to submit for reimbursement")


class ReviewRequestSchema(BaseModel):
    action: str = Field(..., example="APPROVE", description="Action to take: 'APPROVE' or 'REJECT'")
    comment: Optional[str] = Field(default=None, max_length=500, example="Approved as per quarterly travel policy.")


class ReimbursementRequestResponse(BaseModel):
    id: int
    expense_id: int
    employee_id: int
    status: RequestStatus
    submission_date: datetime
    reviewer_id: Optional[int] = None
    decision_date: Optional[datetime] = None
    manager_comment: Optional[str] = None
    is_suspected_duplicate: bool
    duplicate_reason: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    expense: Optional[ExpenseResponse] = None
    employee: Optional[UserResponse] = None
    reviewer: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)
