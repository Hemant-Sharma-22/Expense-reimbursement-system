import pytest
from datetime import date


def test_audit_logs_recorded_and_retrieved(client, seed_base_data, employee_headers, manager_headers):
    # 1. Employee creates an expense
    cat_id = seed_base_data["cat_travel"].id
    exp = client.post(
        "/api/v1/expenses/",
        headers=employee_headers,
        data={
            "category_id": cat_id,
            "amount": 90.00,
            "currency": "USD",
            "expense_date": str(date.today()),
            "merchant": "Train Ticket"
        }
    ).json()

    # 2. Employee submits request
    req = client.post("/api/v1/requests/submit", headers=employee_headers, json={"expense_id": exp["id"]}).json()

    # 3. Manager approves request
    client.post(
        f"/api/v1/manager/requests/{req['id']}/review",
        headers=manager_headers,
        json={"action": "APPROVE", "comment": "Valid commute expense."}
    )

    # 4. Query audit logs as manager
    audit_res = client.get("/api/v1/audit-logs/", headers=manager_headers)
    assert audit_res.status_code == 200
    data = audit_res.json()
    assert data["total"] >= 3

    actions = [item["action"] for item in data["items"]]
    assert "CREATE" in actions
    assert "SUBMIT" in actions
    assert "APPROVE" in actions


def test_employee_cannot_access_audit_logs(client, employee_headers):
    res = client.get("/api/v1/audit-logs/", headers=employee_headers)
    assert res.status_code == 403
