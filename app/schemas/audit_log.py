from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Dict, Any
from app.schemas.user import UserResponse


class AuditLogResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    action: str
    actor_id: Optional[int] = None
    actor_role: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime
    
    actor: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)
