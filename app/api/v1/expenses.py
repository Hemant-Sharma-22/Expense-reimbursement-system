from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, status, File, UploadFile, Query, Form, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.expense import Expense, ExpenseStatus
from app.schemas.expense import ExpenseCreate, ExpenseUpdate, ExpenseResponse, ExpenseFilterParams
from app.services.expense_service import ExpenseService
from app.api.deps import get_current_user

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.post("/", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(
    category_id: int = Form(...),
    amount: float = Form(...),
    currency: str = Form("USD"),
    expense_date: date = Form(...),
    merchant: str = Form(...),
    description: Optional[str] = Form(None),
    receipt_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Creates a new expense record in DRAFT status.
    Supports multipart/form-data with optional receipt image/PDF file upload.
    """
    expense_data = ExpenseCreate(
        category_id=category_id,
        amount=amount,
        currency=currency,
        expense_date=expense_date,
        merchant=merchant,
        description=description
    )
    return ExpenseService.create_expense(
        db=db,
        employee=current_user,
        data=expense_data,
        receipt_file=receipt_file
    )


@router.post("/{expense_id}/receipt", response_model=ExpenseResponse)
def upload_receipt(
    expense_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload or replace receipt image/PDF for an existing draft expense."""
    return ExpenseService.update_expense(
        db=db,
        expense_id=expense_id,
        user=current_user,
        data=ExpenseUpdate(),
        receipt_file=file
    )


@router.get("/", response_model=dict)
def list_expenses(
    status: Optional[ExpenseStatus] = Query(None, description="Filter by status"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
    start_date: Optional[date] = Query(None, description="Filter from expense date"),
    end_date: Optional[date] = Query(None, description="Filter to expense date"),
    min_amount: Optional[float] = Query(None, description="Minimum amount"),
    max_amount: Optional[float] = Query(None, description="Maximum amount"),
    search_query: Optional[str] = Query(None, description="Search in merchant and description"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Queries, filters, and searches expenses with pagination.
    Employees view their own expenses; Managers view department expenses.
    """
    params = ExpenseFilterParams(
        status=status,
        category_id=category_id,
        department_id=department_id,
        employee_id=employee_id,
        start_date=start_date,
        end_date=end_date,
        min_amount=min_amount,
        max_amount=max_amount,
        search_query=search_query
    )
    skip = (page - 1) * page_size
    expenses, total = ExpenseService.get_expenses(db=db, current_user=current_user, params=params, skip=skip, limit=page_size)
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [ExpenseResponse.model_validate(e) for e in expenses]
    }


@router.get("/{expense_id}", response_model=ExpenseResponse)
def get_expense(
    expense_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Gets details of a specific expense."""
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found.")
    
    if current_user.role == UserRole.EMPLOYEE and expense.employee_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        
    return expense


@router.put("/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    expense_id: int,
    data: ExpenseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates an expense draft or rejected expense."""
    return ExpenseService.update_expense(db=db, expense_id=expense_id, user=current_user, data=data)


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a draft expense."""
    ExpenseService.delete_expense(db=db, expense_id=expense_id, user=current_user)
    return None
