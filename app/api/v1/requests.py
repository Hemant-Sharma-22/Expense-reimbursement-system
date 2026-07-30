from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.reimbursement_request import ReimbursementRequest, RequestStatus
from app.schemas.reimbursement_request import SubmitRequestSchema, ReimbursementRequestResponse
from app.services.expense_service import ExpenseService
from app.api.deps import get_current_user

router = APIRouter(prefix="/requests", tags=["Reimbursement Requests"])


@router.post("/submit", response_model=ReimbursementRequestResponse, status_code=status.HTTP_201_CREATED)
def submit_reimbursement_request(
    data: SubmitRequestSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submits a draft expense for reimbursement review.
    Runs the Duplicate Detection Engine to catch identical receipts, exact matching attributes, or time-window overlaps.
    """
    return ExpenseService.submit_for_reimbursement(
        db=db,
        expense_id=data.expense_id,
        employee=current_user
    )


@router.get("/my-requests", response_model=List[ReimbursementRequestResponse])
def get_my_reimbursement_requests(
    status: Optional[RequestStatus] = Query(None, description="Filter by request status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Tracks status of all reimbursement requests submitted by the logged-in employee."""
    query = db.query(ReimbursementRequest).filter(ReimbursementRequest.employee_id == current_user.id)
    if status:
        query = query.filter(ReimbursementRequest.status == status)
    return query.order_by(ReimbursementRequest.submission_date.desc()).all()
