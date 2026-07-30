from typing import List
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.category import Category
from app.models.user import UserRole
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse
from app.api.deps import RoleChecker

router = APIRouter(prefix="/categories", tags=["Categories"])
require_admin_or_manager = RoleChecker([UserRole.ADMIN, UserRole.MANAGER])


@router.get("/", response_model=List[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    """List all expense categories with policy threshold limits."""
    return db.query(Category).all()


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin_or_manager)])
def create_category(data: CategoryCreate, db: Session = Depends(get_db)):
    """Create a new expense category (Manager/Admin only)."""
    existing = db.query(Category).filter(Category.name == data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists."
        )

    cat = Category(**data.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat
