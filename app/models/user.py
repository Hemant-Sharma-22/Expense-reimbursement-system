import enum
from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class UserRole(str, enum.Enum):
    EMPLOYEE = "EMPLOYEE"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.EMPLOYEE, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    department = relationship("Department", back_populates="users")
    expenses = relationship("Expense", back_populates="employee", cascade="all, delete-orphan")
    submitted_requests = relationship("ReimbursementRequest", foreign_keys="ReimbursementRequest.employee_id", back_populates="employee")
    reviewed_requests = relationship("ReimbursementRequest", foreign_keys="ReimbursementRequest.reviewer_id", back_populates="reviewer")
    audit_logs = relationship("AuditLog", back_populates="actor")
