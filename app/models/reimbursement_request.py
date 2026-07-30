import enum
from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime, Boolean, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class RequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ReimbursementRequest(Base):
    __tablename__ = "reimbursement_requests"

    id = Column(Integer, primary_key=True, index=True)
    expense_id = Column(Integer, ForeignKey("expenses.id"), unique=True, nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    status = Column(Enum(RequestStatus), default=RequestStatus.PENDING, nullable=False, index=True)
    submission_date = Column(DateTime(timezone=True), server_default=func.now())
    
    # Review details
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    decision_date = Column(DateTime(timezone=True), nullable=True)
    manager_comment = Column(String(500), nullable=True)
    
    # Duplicate flag / detection metadata
    is_suspected_duplicate = Column(Boolean, default=False, nullable=False)
    duplicate_reason = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    expense = relationship("Expense", back_populates="reimbursement_request")
    employee = relationship("User", foreign_keys=[employee_id], back_populates="submitted_requests")
    reviewer = relationship("User", foreign_keys=[reviewer_id], back_populates="reviewed_requests")
