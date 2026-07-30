import io
import pytest
from datetime import date


def test_duplicate_receipt_file_detection(client, seed_base_data, employee_headers):
    cat_id = seed_base_data["cat_travel"].id
    content = b"Identical Receipt Content 12345"
    file_tuple = ("receipt.png", io.BytesIO(content), "image/png")

    # Create & submit Expense 1 with receipt
    exp1 = client.post(
        "/api/v1/expenses/",
        headers=employee_headers,
        data={
            "category_id": cat_id,
            "amount": 100.00,
            "currency": "USD",
            "expense_date": str(date.today()),
            "merchant": "Taxi A"
        },
        files={"receipt_file": ("receipt.png", io.BytesIO(content), "image/png")}
    ).json()

    client.post("/api/v1/requests/submit", headers=employee_headers, json={"expense_id": exp1["id"]})

    # Create & submit Expense 2 with same receipt content
    exp2 = client.post(
        "/api/v1/expenses/",
        headers=employee_headers,
        data={
            "category_id": cat_id,
            "amount": 200.00,
            "currency": "USD",
            "expense_date": str(date.today()),
            "merchant": "Taxi B"
        },
        files={"receipt_file": ("receipt.png", io.BytesIO(content), "image/png")}
    ).json()

    req2_res = client.post("/api/v1/requests/submit", headers=employee_headers, json={"expense_id": exp2["id"]})
    assert req2_res.status_code == 201
    req2_data = req2_res.json()
    assert req2_data["is_suspected_duplicate"] is True
    assert "Identical receipt file" in req2_data["duplicate_reason"]


def test_duplicate_attribute_match_detection(client, seed_base_data, employee_headers):
    cat_id = seed_base_data["cat_meals"].id
    today_str = str(date.today())

    # Submit first expense
    exp1 = client.post(
        "/api/v1/expenses/",
        headers=employee_headers,
        data={
            "category_id": cat_id,
            "amount": 75.00,
            "currency": "USD",
            "expense_date": today_str,
            "merchant": "Cafe Rio"
        }
    ).json()

    client.post("/api/v1/requests/submit", headers=employee_headers, json={"expense_id": exp1["id"]})

    # Submit second identical expense
    exp2 = client.post(
        "/api/v1/expenses/",
        headers=employee_headers,
        data={
            "category_id": cat_id,
            "amount": 75.00,
            "currency": "USD",
            "expense_date": today_str,
            "merchant": "Cafe Rio"
        }
    ).json()

    req2 = client.post("/api/v1/requests/submit", headers=employee_headers, json={"expense_id": exp2["id"]}).json()
    assert req2["is_suspected_duplicate"] is True
    assert "Identical expense" in req2["duplicate_reason"]
