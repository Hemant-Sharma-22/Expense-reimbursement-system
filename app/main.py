import os
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import Base, engine
from app.api.v1 import api_v1_router
from app.core.exceptions import (
    DuplicateExpenseException,
    InvalidStateTransitionException,
    PermissionDeniedException,
    ResourceNotFoundException
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure database tables exist
    Base.metadata.create_all(bind=engine)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    yield
    # Shutdown logic (if needed)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""
## Enterprise Expense Reimbursement System Backend API

Production-ready backend API built with **FastAPI**, **SQLAlchemy ORM**, **SQLite**, and **Pydantic**.

### Key Features:
* 🔐 **OAuth2 & Role-Based Access Control**: Employee, Manager, and Admin roles.
* 🧾 **Expense Management**: Create, update, delete, categorize expenses & upload receipt files.
* 🛡️ **Duplicate Request Prevention Engine**: SHA-256 receipt hashing & multi-attribute time-window match checking.
* 📑 **Reimbursement Workflow**: Submit requests, manager approvals/rejections with comments.
* 📊 **Department Analytics**: Real-time spending metrics & category breakdown reports.
* 📜 **Complete Audit Trail**: Immutable logging of all state transitions and system actions.
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static File Storage Mount for Receipt File Previews & Web UI Frontend
if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/app", StaticFiles(directory=static_dir, html=True), name="static")



# Custom Exception Handlers
@app.exception_handler(ResourceNotFoundException)
async def resource_not_found_handler(request: Request, exc: ResourceNotFoundException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(PermissionDeniedException)
async def permission_denied_handler(request: Request, exc: PermissionDeniedException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(InvalidStateTransitionException)
async def state_transition_handler(request: Request, exc: InvalidStateTransitionException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(DuplicateExpenseException)
async def duplicate_expense_handler(request: Request, exc: DuplicateExpenseException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# Root endpoint
@app.get("/", tags=["Health Check"])
def root():
    return {
        "status": "online",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "ui": "/app",
        "docs": "/docs",
        "redoc": "/redoc"
    }



# Include API V1 Router
app.include_router(api_v1_router, prefix=settings.API_V1_STR)
