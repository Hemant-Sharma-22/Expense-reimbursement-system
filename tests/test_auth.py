import pytest
from app.models.user import UserRole


def test_register_user(client, db_session):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@company.com",
            "password": "Password123!",
            "full_name": "New User",
            "role": "EMPLOYEE"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@company.com"
    assert data["full_name"] == "New User"
    assert data["role"] == "EMPLOYEE"
    assert "id" in data


def test_login_success(client, seed_base_data):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "emp@company.com",
            "password": "password123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "emp@company.com"


def test_login_invalid_credentials(client, seed_base_data):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "emp@company.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    assert "detail" in response.json()


def test_get_current_user_me(client, employee_headers):
    response = client.get("/api/v1/auth/me", headers=employee_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "emp@company.com"
