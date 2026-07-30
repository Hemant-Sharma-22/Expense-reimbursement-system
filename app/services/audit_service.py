from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from app.models.audit_log import AuditLog
from app.models.user import User


class AuditService:
    @staticmethod
    def log_action(
        db: Session,
        entity_type: str,
        entity_id: int,
        action: str,
        actor: Optional[User] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """Records an audit trail log entry into the database."""
        audit_entry = AuditLog(
            entity_type=entity_type.upper(),
            entity_id=entity_id,
            action=action.upper(),
            actor_id=actor.id if actor else None,
            actor_role=actor.role.value if actor else None,
            details=details or {}
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(audit_entry)
        return audit_entry
