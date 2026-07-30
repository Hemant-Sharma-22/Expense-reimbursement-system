import os
import hashlib
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from fastapi import UploadFile, HTTPException, status

from app.models.expense import Expense, ExpenseStatus
from app.models.reimbursement_request import ReimbursementRequest, RequestStatus
from app.models.category import Category
from app.models.user import User, UserRole
from app.schemas.expense import ExpenseCreate, ExpenseUpdate, ExpenseFilterParams
from app.services.duplicate_detector import DuplicateDetectorService
from app.services.audit_service import AuditService
from app.core.exceptions import ResourceNotFoundException, PermissionDeniedException, InvalidStateTransitionException, DuplicateExpenseException
from app.core.config import settings


class ExpenseService:
    @staticmethod
    def save_receipt_file(file: UploadFile) -> Tuple[str, str, str]:
        """
        Saves uploaded file to disk and computes SHA-256 hash of its content.
        Returns: (relative_url, filename, sha256_hash)
        """
        extension = file.filename.split(".")[-1].lower() if "." in file.filename else ""
        if extension not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '.{extension}'. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )

        content = file.file.read()
        file.file.seek(0)

        if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum threshold of {settings.MAX_UPLOAD_SIZE_MB} MB"
            )

        sha256_hash = hashlib.sha256(content).hexdigest()
        unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
        file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

        with open(file_path, "wb") as f:
            f.write(content)

        relative_url = f"/uploads/{unique_filename}"
        return relative_url, unique_filename, sha256_hash

    @staticmethod
    def create_expense(db: Session, employee: User, data: ExpenseCreate, receipt_file: Optional[UploadFile] = None) -> Expense:
        """Creates a new expense record in DRAFT status."""
        category = db.query(Category).filter(Category.id == data.category_id).first()
        if not category:
            raise ResourceNotFoundException("Category")

        # Category maximum limit warning/validation check
        if category.max_limit_amount and data.amount > category.max_limit_amount:
            # Note: We allow drafting expenses over category limit, but set detail log / warning
            pass

        receipt_url, receipt_filename, receipt_hash = None, None, None
        if receipt_file:
            receipt_url, receipt_filename, receipt_hash = ExpenseService.save_receipt_file(receipt_file)

        expense = Expense(
            employee_id=employee.id,
            category_id=data.category_id,
            amount=data.amount,
            currency=data.currency,
            expense_date=data.expense_date,
            merchant=data.merchant,
            description=data.description,
            receipt_url=receipt_url,
            receipt_filename=receipt_filename,
            receipt_hash=receipt_hash,
            status=ExpenseStatus.DRAFT
        )

        db.add(expense)
        db.commit()
        db.refresh(expense)

        # Audit log creation
        AuditService.log_action(
            db=db,
            entity_type="EXPENSE",
            entity_id=expense.id,
            action="CREATE",
            actor=employee,
            details={
                "amount": expense.amount,
                "merchant": expense.merchant,
                "category_id": expense.category_id,
                "status": expense.status.value,
                "receipt_uploaded": bool(receipt_file)
            }
        )

        return expense

    @staticmethod
    def update_expense(
        db: Session,
        expense_id: int,
        user: User,
        data: ExpenseUpdate,
        receipt_file: Optional[UploadFile] = None
    ) -> Expense:
        """Updates a draft or rejected expense."""
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        if not expense:
            raise ResourceNotFoundException("Expense")

        if expense.employee_id != user.id and user.role != UserRole.ADMIN:
            raise PermissionDeniedException("You can only modify your own expenses.")

        if expense.status not in [ExpenseStatus.DRAFT, ExpenseStatus.REJECTED]:
            raise InvalidStateTransitionException(
                f"Expense cannot be edited in current status '{expense.status.value}'."
            )

        old_values = {
            "amount": expense.amount,
            "merchant": expense.merchant,
            "category_id": expense.category_id,
            "status": expense.status.value
        }

        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(expense, key, value)

        if receipt_file:
            receipt_url, receipt_filename, receipt_hash = ExpenseService.save_receipt_file(receipt_file)
            expense.receipt_url = receipt_url
            expense.receipt_filename = receipt_filename
            expense.receipt_hash = receipt_hash

        # If expense was previously rejected, editing resets status back to DRAFT
        if expense.status == ExpenseStatus.REJECTED:
            expense.status = ExpenseStatus.DRAFT

        expense.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(expense)

        AuditService.log_action(
            db=db,
            entity_type="EXPENSE",
            entity_id=expense.id,
            action="UPDATE",
            actor=user,
            details={"old": old_values, "new": update_dict}
        )

        return expense

    @staticmethod
    def delete_expense(db: Session, expense_id: int, user: User) -> None:
        """Deletes a draft expense."""
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        if not expense:
            raise ResourceNotFoundException("Expense")

        if expense.employee_id != user.id and user.role != UserRole.ADMIN:
            raise PermissionDeniedException("You can only delete your own expenses.")

        if expense.status not in [ExpenseStatus.DRAFT, ExpenseStatus.CANCELLED]:
            raise InvalidStateTransitionException(
                f"Cannot delete expense in status '{expense.status.value}'."
            )

        AuditService.log_action(
            db=db,
            entity_type="EXPENSE",
            entity_id=expense.id,
            action="DELETE",
            actor=user,
            details={"merchant": expense.merchant, "amount": expense.amount}
        )

        db.delete(expense)
        db.commit()

    @staticmethod
    def submit_for_reimbursement(db: Session, expense_id: int, employee: User) -> ReimbursementRequest:
        """
        Submits an expense for reimbursement.
        Runs duplicate detection. Raises DuplicateExpenseException or flags request.
        """
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        if not expense:
            raise ResourceNotFoundException("Expense")

        if expense.employee_id != employee.id:
            raise PermissionDeniedException("You can only submit your own expenses.")

        if expense.status not in [ExpenseStatus.DRAFT, ExpenseStatus.REJECTED]:
            raise InvalidStateTransitionException(
                f"Expense is already submitted or processed (Current status: '{expense.status.value}')."
            )

        # Execute Duplicate Detection Engine
        is_duplicate, duplicate_reason = DuplicateDetectorService.check_duplicate_expense_request(db, expense)

        # Update expense status
        expense.status = ExpenseStatus.SUBMITTED
        expense.updated_at = datetime.now(timezone.utc)

        # Check existing request or create new request
        existing_req = db.query(ReimbursementRequest).filter(ReimbursementRequest.expense_id == expense.id).first()
        if existing_req:
            req = existing_req
            req.status = RequestStatus.PENDING
            req.submission_date = datetime.now(timezone.utc)
            req.is_suspected_duplicate = is_duplicate
            req.duplicate_reason = duplicate_reason
            req.reviewer_id = None
            req.decision_date = None
            req.manager_comment = None
        else:
            req = ReimbursementRequest(
                expense_id=expense.id,
                employee_id=employee.id,
                status=RequestStatus.PENDING,
                submission_date=datetime.now(timezone.utc),
                is_suspected_duplicate=is_duplicate,
                duplicate_reason=duplicate_reason
            )
            db.add(req)

        db.commit()
        db.refresh(req)
        db.refresh(expense)

        AuditService.log_action(
            db=db,
            entity_type="REIMBURSEMENT_REQUEST",
            entity_id=req.id,
            action="SUBMIT",
            actor=employee,
            details={
                "expense_id": expense.id,
                "amount": expense.amount,
                "is_suspected_duplicate": is_duplicate,
                "duplicate_reason": duplicate_reason
            }
        )

        return req

    @staticmethod
    def get_expenses(
        db: Session,
        current_user: User,
        params: ExpenseFilterParams,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[Expense], int]:
        """
        Queries expenses with rich filtering, searching, and pagination.
        Employees view their own expenses. Managers and Admins can view department or all expenses.
        """
        query = db.query(Expense)

        # Scope filter by Role
        if current_user.role == UserRole.EMPLOYEE:
            query = query.filter(Expense.employee_id == current_user.id)
        elif current_user.role == UserRole.MANAGER and current_user.department_id:
            # Manager sees expenses from employees in their department
            query = query.join(User, Expense.employee_id == User.id)\
                         .filter(User.department_id == current_user.department_id)

        # Apply search parameters
        if params.status:
            query = query.filter(Expense.status == params.status)
        if params.category_id:
            query = query.filter(Expense.category_id == params.category_id)
        if params.employee_id:
            query = query.filter(Expense.employee_id == params.employee_id)
        if params.start_date:
            query = query.filter(Expense.expense_date >= params.start_date)
        if params.end_date:
            query = query.filter(Expense.expense_date <= params.end_date)
        if params.min_amount is not None:
            query = query.filter(Expense.amount >= params.min_amount)
        if params.max_amount is not None:
            query = query.filter(Expense.amount <= params.max_amount)
        if params.search_query:
            search_pattern = f"%{params.search_query}%"
            query = query.filter(
                or_(
                    Expense.merchant.ilike(search_pattern),
                    Expense.description.ilike(search_pattern)
                )
            )

        total_count = query.count()
        results = query.order_by(Expense.created_at.desc()).offset(skip).limit(limit).all()
        return results, total_count
