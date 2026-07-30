import pytest
from datetime import date


def test_manager_approve_request(client, seed_base_data, employee_headers, manager_headers):
    cat_id = seed_base_data["cat_travel"].id
    exp_res = client.post(
        "/api/v1/expenses/",
        headers=employee_headers,
        data={
            "category_id": cat_id,
            "amount": 300.00,
            "currency": "USD",
            "expense_date": str(date.today()),
            "merchant": "Hilton Hotel"
        }
    )
    exp_id = exp_res.json()["id"]

    sub_res = client.post("/api/v1/requests/submit", headers=employee_headers, json={"expense_id": exp_id})
    req_id = sub_res.json()["id"]

    # Manager approves request
    review_res = client.post(
        f"/api/v1/manager/requests/{req_id}/review",
        headers=manager_headers,
        json={"action": "APPROVE", "comment": "Approved per hotel policy limit."}
    )
    assert review_res.status_code == 200
    rev_data = review_res.json()
    assert rev_data["status"] == "APPROVED"
    assert rev_data["manager_comment"] == "Approved per hotel policy limit."


def test_manager_reject_request(client, seed_base_data, employee_headers, manager_headers):
    cat_id = seed_base_data["cat_meals"].id
    exp_res = client.post(
        "/api/v1/expenses/",
        headers=employee_headers,
        data={
            "category_id": cat_id,
            "amount": 500.00,
            "currency": "USD",
            "expense_date": str(date.today()),
            "merchant": "Expensive Dining"
        }
    )
    exp_id = exp_res.json()["id"]

    sub_res = client.post("/api/v1/requests/submit", headers=employee_headers, json={"expense_id": exp_id})
    req_id = sub_res.json()["id"]

    # Manager rejects request
    review_res = client.post(
        f"/api/v1/manager/requests/{req_id}/review",
        headers=manager_headers,
        json={"action": "REJECT", "comment": "Over category maximum limit."}
    )
    assert review_res.status_code == 200
    assert review_res.json()["status"] == "REJECTED"


def test_department_summary(client, seed_base_data, manager_headers):
    dept_id = seed_base_data["dept"].id
    res = client.get(f"/api/v1/manager/department-summary/{dept_id}", headers=manager_headers)
    assert res.status_code == 200
    summary = res.json()
    assert summary["department_id"] == dept_id
    assert summary["department_name"] == "Engineering"
    assert "total_approved_amount" in summary
