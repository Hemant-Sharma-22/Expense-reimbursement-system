from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.reimbursement_request import ReimbursementRequest, RequestStatus
from app.models.expense import Expense, ExpenseStatus
from app.models.user import User, UserRole
from app.models.department import Department
from app.models.category import Category
from app.schemas.analytics import DepartmentSummaryResponse, CategoryBreakdownItem
from app.services.audit_service import AuditService
from app.core.exceptions import ResourceNotFoundException, PermissionDeniedException, InvalidStateTransitionException


class ManagerService:
    @staticmethod
    def review_request(
        db: Session,
        request_id: int,
        reviewer: User,
        action: str,
        comment: Optional[str] = None
    ) -> ReimbursementRequest:
        """
        Approve or Reject a pending reimbursement request.
        Updates request status and expense status, records decision date and comment.
        """
        if reviewer.role not in [UserRole.MANAGER, UserRole.ADMIN]:
            raise PermissionDeniedException("Only managers or administrators can review reimbursement requests.")

        req = db.query(ReimbursementRequest).filter(ReimbursementRequest.id == request_id).first()
        if not req:
            raise ResourceNotFoundException("Reimbursement Request")

        if req.status != RequestStatus.PENDING:
            raise InvalidStateTransitionException(
                f"Reimbursement request is already {req.status.value} and cannot be modified."
            )

        expense = db.query(Expense).filter(Expense.id == req.expense_id).first()
        if not expense:
            raise ResourceNotFoundException("Associated Expense")

        action_upper = action.upper()
        if action_upper not in ["APPROVE", "REJECT"]:
            raise InvalidStateTransitionException("Action must be either 'APPROVE' or 'REJECT'.")

        now = datetime.now(timezone.utc)
        req.reviewer_id = reviewer.id
        req.decision_date = now
        req.manager_comment = comment

        if action_upper == "APPROVE":
            req.status = RequestStatus.APPROVED
            expense.status = ExpenseStatus.APPROVED
        else:
            req.status = RequestStatus.REJECTED
            expense.status = ExpenseStatus.REJECTED

        expense.updated_at = now
        req.updated_at = now

        db.commit()
        db.refresh(req)
        db.refresh(expense)

        # Record audit log
        AuditService.log_action(
            db=db,
            entity_type="REIMBURSEMENT_REQUEST",
            entity_id=req.id,
            action=action_upper,
            actor=reviewer,
            details={
                "expense_id": expense.id,
                "amount": expense.amount,
                "status": req.status.value,
                "comment": comment
            }
        )

        return req

    @staticmethod
    def get_department_summary(db: Session, department_id: int) -> DepartmentSummaryResponse:
        """
        Generates analytics summary for a department including budget, total requested/approved/pending amounts,
        and category breakdowns.
        """
        department = db.query(Department).filter(Department.id == department_id).first()
        if not department:
            raise ResourceNotFoundException("Department")

        # Query all requests belonging to employees in this department
        dept_expenses = db.query(Expense).join(User, Expense.employee_id == User.id)\
                          .filter(User.department_id == department_id).all()

        total_requested = sum(e.amount for e in dept_expenses if e.status in [ExpenseStatus.SUBMITTED, ExpenseStatus.APPROVED, ExpenseStatus.REJECTED])
        total_approved = sum(e.amount for e in dept_expenses if e.status == ExpenseStatus.APPROVED)
        total_pending = sum(e.amount for e in dept_expenses if e.status == ExpenseStatus.SUBMITTED)
        total_rejected = sum(e.amount for e in dept_expenses if e.status == ExpenseStatus.REJECTED)

        approved_count = sum(1 for e in dept_expenses if e.status == ExpenseStatus.APPROVED)
        pending_count = sum(1 for e in dept_expenses if e.status == ExpenseStatus.SUBMITTED)
        rejected_count = sum(1 for e in dept_expenses if e.status == ExpenseStatus.REJECTED)

        # Category breakdown calculation
        categories = db.query(Category).all()
        category_map = {c.id: {"name": c.name, "amount": 0.0, "count": 0} for c in categories}

        for e in dept_expenses:
            if e.category_id in category_map and e.status in [ExpenseStatus.SUBMITTED, ExpenseStatus.APPROVED]:
                category_map[e.category_id]["amount"] += e.amount
                category_map[e.category_id]["count"] += 1

        breakdown = [
            CategoryBreakdownItem(
                category_id=cat_id,
                category_name=data["name"],
                total_amount=round(data["amount"], 2),
                request_count=data["count"]
            )
            for cat_id, data in category_map.items()
            if data["count"] > 0
        ]

        return DepartmentSummaryResponse(
            department_id=department.id,
            department_name=department.name,
            total_budget=department.budget,
            total_requested_amount=round(total_requested, 2),
            total_approved_amount=round(total_approved, 2),
            total_pending_amount=round(total_pending, 2),
            total_rejected_amount=round(total_rejected, 2),
            approved_requests_count=approved_count,
            pending_requests_count=pending_count,
            rejected_requests_count=rejected_count,
            category_breakdown=breakdown
        )
