from typing import List
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.department import Department
from app.models.user import UserRole
from app.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentResponse
from app.api.deps import RoleChecker

router = APIRouter(prefix="/departments", tags=["Departments"])
require_admin = RoleChecker([UserRole.ADMIN])


@router.get("/", response_model=List[DepartmentResponse])
def list_departments(db: Session = Depends(get_db)):
    """List all company departments."""
    return db.query(Department).all()


@router.post("/", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_department(data: DepartmentCreate, db: Session = Depends(get_db)):
    """Create a new department (Admin only)."""
    existing = db.query(Department).filter(
        (Department.name == data.name) | (Department.code == data.code)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department name or code already exists."
        )

    dept = Department(**data.model_dump())
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept
