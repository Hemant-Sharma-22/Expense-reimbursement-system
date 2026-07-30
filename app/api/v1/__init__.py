from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.departments import router as departments_router
from app.api.v1.categories import router as categories_router
from app.api.v1.expenses import router as expenses_router
from app.api.v1.requests import router as requests_router
from app.api.v1.manager import router as manager_router
from app.api.v1.audit import router as audit_router
from app.api.v1.policy_assistant import router as policy_assistant_router

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router)
api_v1_router.include_router(departments_router)
api_v1_router.include_router(categories_router)
api_v1_router.include_router(expenses_router)
api_v1_router.include_router(requests_router)
api_v1_router.include_router(manager_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(policy_assistant_router)
