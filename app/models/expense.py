import enum
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey, func, Date
from sqlalchemy.orm import relationship
from app.core.database import Base


class ExpenseStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    expense_date = Column(Date, nullable=False, index=True)
    merchant = Column(String(255), nullable=False, index=True)
    description = Column(String(500), nullable=True)
    
    # Receipt details
    receipt_filename = Column(String(255), nullable=True)
    receipt_url = Column(String(500), nullable=True)
    receipt_hash = Column(String(64), nullable=True, index=True)  # SHA-256 file content hash
    
    status = Column(Enum(ExpenseStatus), default=ExpenseStatus.DRAFT, nullable=False, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    employee = relationship("User", back_populates="expenses")
    category = relationship("Category", back_populates="expenses")
    reimbursement_request = relationship("ReimbursementRequest", back_populates="expense", uselist=False, cascade="all, delete-orphan")
