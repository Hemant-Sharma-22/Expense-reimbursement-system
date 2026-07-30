import pytest
from datetime import date


def test_submit_reimbursement_request(client, seed_base_data, employee_headers):
    cat_id = seed_base_data["cat_travel"].id
    exp_res = client.post(
        "/api/v1/expenses/",
        headers=employee_headers,
        data={
            "category_id": cat_id,
            "amount": 250.00,
            "currency": "USD",
            "expense_date": str(date.today()),
            "merchant": "United Airlines"
        }
    )
    exp_id = exp_res.json()["id"]

    submit_res = client.post(
        "/api/v1/requests/submit",
        headers=employee_headers,
        json={"expense_id": exp_id}
    )
    assert submit_res.status_code == 201
    req_data = submit_res.json()
    assert req_data["expense_id"] == exp_id
    assert req_data["status"] == "PENDING"
    assert req_data["is_suspected_duplicate"] is False


def test_cannot_submit_already_submitted_expense(client, seed_base_data, employee_headers):
    cat_id = seed_base_data["cat_travel"].id
    exp_res = client.post(
        "/api/v1/expenses/",
        headers=employee_headers,
        data={
            "category_id": cat_id,
            "amount": 250.00,
            "currency": "USD",
            "expense_date": str(date.today()),
            "merchant": "United Airlines"
        }
    )
    exp_id = exp_res.json()["id"]

    client.post("/api/v1/requests/submit", headers=employee_headers, json={"expense_id": exp_id})

    res_second = client.post("/api/v1/requests/submit", headers=employee_headers, json={"expense_id": exp_id})
    assert res_second.status_code == 422
    assert "already submitted" in res_second.json()["detail"]
