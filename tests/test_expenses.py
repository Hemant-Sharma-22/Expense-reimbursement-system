import io
import pytest
from datetime import date, timedelta


def test_create_expense_draft(client, seed_base_data, employee_headers):
    cat_id = seed_base_data["cat_travel"].id
    response = client.post(
        "/api/v1/expenses/",
        headers=employee_headers,
        data={
            "category_id": cat_id,
            "amount": 150.00,
            "currency": "USD",
            "expense_date": str(date.today()),
            "merchant": "Uber",
            "description": "Taxi ride to airport"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["amount"] == 150.00
    assert data["merchant"] == "Uber"
    assert data["status"] == "DRAFT"
    assert data["employee_id"] == seed_base_data["employee"].id


def test_create_expense_with_receipt(client, seed_base_data, employee_headers):
    cat_id = seed_base_data["cat_meals"].id
    file_content = b"Simulated receipt file image bytes content"
    file_tuple = ("receipt.png", io.BytesIO(file_content), "image/png")

    response = client.post(
        "/api/v1/expenses/",
        headers=employee_headers,
        data={
            "category_id": cat_id,
            "amount": 45.00,
            "currency": "USD",
            "expense_date": str(date.today()),
            "merchant": "Starbucks",
            "description": "Coffee meeting"
        },
        files={"receipt_file": file_tuple}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["receipt_url"] is not None
    assert data["receipt_hash"] is not None


def test_update_expense(client, seed_base_data, employee_headers):
    cat_id = seed_base_data["cat_travel"].id
    res = client.post(
        "/api/v1/expenses/",
        headers=employee_headers,
        data={
            "category_id": cat_id,
            "amount": 100.00,
            "currency": "USD",
            "expense_date": str(date.today()),
            "merchant": "Lyft"
        }
    )
    exp_id = res.json()["id"]

    update_res = client.put(
        f"/api/v1/expenses/{exp_id}",
        headers=employee_headers,
        json={"amount": 125.50, "merchant": "Lyft Premium"}
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["amount"] == 125.50
    assert updated_data["merchant"] == "Lyft Premium"


def test_delete_expense_draft(client, seed_base_data, employee_headers):
    cat_id = seed_base_data["cat_travel"].id
    res = client.post(
        "/api/v1/expenses/",
        headers=employee_headers,
        data={
            "category_id": cat_id,
            "amount": 50.00,
            "currency": "USD",
            "expense_date": str(date.today()),
            "merchant": "Test Merchant"
        }
    )
    exp_id = res.json()["id"]

    del_res = client.delete(f"/api/v1/expenses/{exp_id}", headers=employee_headers)
    assert del_res.status_code == 204

    get_res = client.get(f"/api/v1/expenses/{exp_id}", headers=employee_headers)
    assert get_res.status_code == 404
