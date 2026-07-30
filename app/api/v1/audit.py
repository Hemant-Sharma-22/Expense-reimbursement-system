from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import UserRole
from app.schemas.audit_log import AuditLogResponse
from app.api.deps import RoleChecker

router = APIRouter(prefix="/audit-logs", tags=["Audit Trail"])
require_manager_or_admin = RoleChecker([UserRole.MANAGER, UserRole.ADMIN])


@router.get("/", response_model=dict, dependencies=[Depends(require_manager_or_admin)])
def list_audit_logs(
    entity_type: Optional[str] = Query(None, description="Filter by entity type (e.g. EXPENSE, REIMBURSEMENT_REQUEST, USER)"),
    entity_id: Optional[int] = Query(None, description="Filter by entity ID"),
    action: Optional[str] = Query(None, description="Filter by action (e.g. CREATE, SUBMIT, APPROVE, REJECT)"),
    actor_id: Optional[int] = Query(None, description="Filter by actor user ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Search and query complete audit trail logs for state changes and user actions.
    Restricted to Managers and Administrators.
    """
    query = db.query(AuditLog)

    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type.upper())
    if entity_id:
        query = query.filter(AuditLog.entity_id == entity_id)
    if action:
        query = query.filter(AuditLog.action == action.upper())
    if actor_id:
        query = query.filter(AuditLog.actor_id == actor_id)

    total_count = query.count()
    skip = (page - 1) * page_size
    items = query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(page_size).all()

    return {
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "items": [AuditLogResponse.model_validate(item) for item in items]
    }
