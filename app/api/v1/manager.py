from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.reimbursement_request import ReimbursementRequest, RequestStatus
from app.schemas.reimbursement_request import ReviewRequestSchema, ReimbursementRequestResponse
from app.schemas.analytics import DepartmentSummaryResponse
from app.services.manager_service import ManagerService
from app.api.deps import RoleChecker, get_current_user

router = APIRouter(prefix="/manager", tags=["Manager Operations"])
require_manager_role = RoleChecker([UserRole.MANAGER, UserRole.ADMIN])


@router.get("/pending-requests", response_model=List[ReimbursementRequestResponse], dependencies=[Depends(require_manager_role)])
def get_pending_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns pending reimbursement requests for employees in the manager's department.
    Admins see all pending requests.
    """
    query = db.query(ReimbursementRequest).filter(ReimbursementRequest.status == RequestStatus.PENDING)
    if current_user.role == UserRole.MANAGER and current_user.department_id:
        query = query.join(User, ReimbursementRequest.employee_id == User.id)\
                     .filter(User.department_id == current_user.department_id)
    return query.order_by(ReimbursementRequest.submission_date.asc()).all()


@router.post("/requests/{request_id}/review", response_model=ReimbursementRequestResponse, dependencies=[Depends(require_manager_role)])
def review_reimbursement_request(
    request_id: int,
    payload: ReviewRequestSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Approve or Reject a reimbursement request with optional manager comment.
    Automatically updates the underlying expense status and audit log.
    """
    return ManagerService.review_request(
        db=db,
        request_id=request_id,
        reviewer=current_user,
        action=payload.action,
        comment=payload.comment
    )


@router.get("/approved-reimbursements", response_model=List[ReimbursementRequestResponse], dependencies=[Depends(require_manager_role)])
def get_approved_reimbursements(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists historical approved reimbursement requests."""
    query = db.query(ReimbursementRequest).filter(ReimbursementRequest.status == RequestStatus.APPROVED)
    if current_user.role == UserRole.MANAGER and current_user.department_id:
        query = query.join(User, ReimbursementRequest.employee_id == User.id)\
                     .filter(User.department_id == current_user.department_id)
    return query.order_by(ReimbursementRequest.decision_date.desc()).all()


@router.get("/department-summary/{department_id}", response_model=DepartmentSummaryResponse, dependencies=[Depends(require_manager_role)])
def get_department_summary(
    department_id: int,
    db: Session = Depends(get_db)
):
    """
    Returns department reimbursement metrics: budget, requested, approved, pending, rejected, and category breakdowns.
    """
    return ManagerService.get_department_summary(db=db, department_id=department_id)
