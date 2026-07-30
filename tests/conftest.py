import pytest
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_password_hash, create_access_token
from app.models.department import Department
from app.models.category import Category
from app.models.user import User, UserRole
from app.main import app

# StaticPool maintains a single shared connection for SQLite in-memory database across threads in testing
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Provides a clean in-memory database session for each test function."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Provides a TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seed_base_data(db_session):
    """Seeds base departments, categories, and users for testing."""
    dept = Department(name="Engineering", code="ENG", budget=50000.0)
    db_session.add(dept)
    db_session.commit()

    cat_travel = Category(name="Travel", description="Flight and taxi", max_limit_amount=1000.0)
    cat_meals = Category(name="Meals", description="Food & drinks", max_limit_amount=100.0)
    db_session.add_all([cat_travel, cat_meals])
    db_session.commit()

    employee = User(
        email="emp@company.com",
        full_name="Test Employee",
        hashed_password=get_password_hash("password123"),
        role=UserRole.EMPLOYEE,
        department_id=dept.id
    )

    manager = User(
        email="mgr@company.com",
        full_name="Test Manager",
        hashed_password=get_password_hash("password123"),
        role=UserRole.MANAGER,
        department_id=dept.id
    )

    admin = User(
        email="admin@company.com",
        full_name="Test Admin",
        hashed_password=get_password_hash("password123"),
        role=UserRole.ADMIN,
        department_id=dept.id
    )

    db_session.add_all([employee, manager, admin])
    db_session.commit()

    return {
        "dept": dept,
        "cat_travel": cat_travel,
        "cat_meals": cat_meals,
        "employee": employee,
        "manager": manager,
        "admin": admin
    }


@pytest.fixture
def employee_headers(seed_base_data):
    emp = seed_base_data["employee"]
    token = create_access_token(subject=emp.id, role=emp.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def manager_headers(seed_base_data):
    mgr = seed_base_data["manager"]
    token = create_access_token(subject=mgr.id, role=mgr.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(seed_base_data):
    adm = seed_base_data["admin"]
    token = create_access_token(subject=adm.id, role=adm.role.value)
    return {"Authorization": f"Bearer {token}"}
