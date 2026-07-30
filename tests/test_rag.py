import pytest
from app.services.rag_service import RAGService


def test_rag_meal_policy_query(client):
    response = client.post(
        "/api/v1/policy-assistant/query",
        json={"query": "What is the daily meal allowance limit?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["grounded"] is True
    assert "$75.00 USD" in data["answer"]
    assert len(data["citations"]) > 0
    assert data["citations"][0]["document_name"] == "Expense Policy"


def test_rag_flight_policy_query(client):
    response = client.post(
        "/api/v1/policy-assistant/query",
        json={"query": "Can I book business class for international flights?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["grounded"] is True
    assert "8 hours" in data["answer"]
    assert any(c["document_name"] == "Travel Policy" for c in data["citations"])


def test_rag_fallback_missing_information(client):
    response = client.post(
        "/api/v1/policy-assistant/query",
        json={"query": "What is the corporate policy on bring your pet to work?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["grounded"] is False
    assert "Sufficient information could not be found" in data["answer"]
    assert len(data["citations"]) == 0


def test_rag_metadata_filtering(client):
    response = client.post(
        "/api/v1/policy-assistant/query",
        json={
            "query": "What are the rules for hotel room rates?",
            "document_filter": "Travel Policy"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["grounded"] is True
    for citation in data["citations"]:
        assert citation["document_name"] == "Travel Policy"


def test_list_indexed_documents(client):
    response = client.get("/api/v1/policy-assistant/documents")
    assert response.status_code == 200
    data = response.json()
    assert data["indexed_documents_count"] >= 4
    doc_names = [d["document_name"] for d in data["documents"]]
    assert "Expense Policy" in doc_names
    assert "Travel Policy" in doc_names
    assert "Finance Policy" in doc_names
    assert "Employee Handbook" in doc_names
