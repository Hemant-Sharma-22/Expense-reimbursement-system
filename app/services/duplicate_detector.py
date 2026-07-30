from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Tuple, Optional
from app.models.expense import Expense, ExpenseStatus
from app.core.config import settings


class DuplicateDetectorService:
    @staticmethod
    def check_duplicate_receipt_hash(db: Session, receipt_hash: str, exclude_expense_id: Optional[int] = None) -> Optional[Expense]:
        """Checks if a receipt with identical SHA-256 hash has already been uploaded."""
        if not receipt_hash:
            return None
        query = db.query(Expense).filter(
            Expense.receipt_hash == receipt_hash,
            Expense.status != ExpenseStatus.CANCELLED
        )
        if exclude_expense_id:
            query = query.filter(Expense.id != exclude_expense_id)
        return query.first()

    @staticmethod
    def check_duplicate_expense_request(db: Session, expense: Expense) -> Tuple[bool, Optional[str]]:
        """
        Evaluates potential duplicate reimbursement submissions.
        Returns (is_duplicate: bool, reason: str).
        """
        # Rule 1: Check receipt file hash if present
        if expense.receipt_hash:
            existing_receipt = db.query(Expense).filter(
                Expense.receipt_hash == expense.receipt_hash,
                Expense.id != expense.id,
                Expense.status.in_([ExpenseStatus.SUBMITTED, ExpenseStatus.APPROVED])
            ).first()
            if existing_receipt:
                return True, f"Identical receipt file uploaded previously in Expense #{existing_receipt.id}"

        # Rule 2: Check exact matching attributes (same employee, merchant, amount, expense_date)
        exact_match = db.query(Expense).filter(
            Expense.employee_id == expense.employee_id,
            Expense.amount == expense.amount,
            Expense.merchant.ilike(expense.merchant),
            Expense.expense_date == expense.expense_date,
            Expense.id != expense.id,
            Expense.status.in_([ExpenseStatus.SUBMITTED, ExpenseStatus.APPROVED])
        ).first()

        if exact_match:
            return True, f"Identical expense (Merchant: {exact_match.merchant}, Amount: ${exact_match.amount}, Date: {exact_match.expense_date}) already submitted in Expense #{exact_match.id}"

        # Rule 3: Check window match (same employee, same amount, date within window)
        start_window = expense.expense_date - timedelta(days=settings.DUPLICATE_TIME_WINDOW_DAYS)
        end_window = expense.expense_date + timedelta(days=settings.DUPLICATE_TIME_WINDOW_DAYS)

        window_match = db.query(Expense).filter(
            Expense.employee_id == expense.employee_id,
            Expense.amount == expense.amount,
            Expense.expense_date >= start_window,
            Expense.expense_date <= end_window,
            Expense.id != expense.id,
            Expense.status.in_([ExpenseStatus.SUBMITTED, ExpenseStatus.APPROVED])
        ).first()

        if window_match:
            return True, f"Potential duplicate found within {settings.DUPLICATE_TIME_WINDOW_DAYS} days (Amount: ${window_match.amount}, Date: {window_match.expense_date}) in Expense #{window_match.id}"

        return False, None
