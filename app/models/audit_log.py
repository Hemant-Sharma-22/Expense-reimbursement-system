from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(50), nullable=False, index=True)  # e.g., "EXPENSE", "REIMBURSEMENT_REQUEST", "USER"
    entity_id = Column(Integer, nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)      # e.g., "CREATE", "UPDATE", "SUBMIT", "APPROVE", "REJECT", "DELETE"
    
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    actor_role = Column(String(20), nullable=True)
    
    details = Column(JSON, nullable=True)                       # JSON snapshot of state change, IP, user-agent, etc.
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    actor = relationship("User", back_populates="audit_logs")
