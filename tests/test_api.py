from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_text_endpoint() -> None:
    response = client.post(
        "/api/v1/tasks/analyze-text",
        json={
            "query": "Analyze bank statement",
            "text": "2026-04-03 Cash Deposit 0 150000 400000",
        },
    )

    assert response.status_code == 200
    assert response.json()["agent"] == "bank_statement"

