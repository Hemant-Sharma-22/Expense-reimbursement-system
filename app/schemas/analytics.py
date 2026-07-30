from pydantic import BaseModel
from typing import Dict, List, Optional


class CategoryBreakdownItem(BaseModel):
    category_id: int
    category_name: str
    total_amount: float
    request_count: int


class DepartmentSummaryResponse(BaseModel):
    department_id: int
    department_name: str
    total_budget: float
    total_requested_amount: float
    total_approved_amount: float
    total_pending_amount: float
    total_rejected_amount: float
    approved_requests_count: int
    pending_requests_count: int
    rejected_requests_count: int
    category_breakdown: List[CategoryBreakdownItem]
