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


def test_analyze_text_accepts_list_of_lines() -> None:
    response = client.post(
        "/api/v1/tasks/analyze-text",
        json={
            "query": "Analyze this bank statement",
            "text": [
                "2026-04-03 Cash Deposit 0 150000 400000",
                "2026-04-07 Vendor Payment 85000 0 315000",
                "2026-04-11 Interest Credit 0 3500 318500",
                "2026-04-15 Loan EMI 45000 0 273500",
                "2026-04-20 High Value Receipt 0 250000 523500",
            ],
        },
    )

    payload = response.json()

    assert response.status_code == 200
    assert payload["agent"] == "bank_statement"
    assert payload["client_response"]
    assert payload["llm"]["provider"] == "offline"
    assert payload["learned_context_path"]
    assert payload["data"]["transaction_count"] == 5
    assert payload["data"]["total_credits"] == 403500


def test_invalid_multiline_json_returns_helpful_message() -> None:
    response = client.post(
        "/api/v1/tasks/analyze-text",
        content='{"query":"Analyze bank statement","text":"line one\nline two"}',
        headers={"Content-Type": "application/json"},
    )

    payload = response.json()

    assert response.status_code == 422
    assert "Invalid JSON body" in payload["message"]
    assert isinstance(payload["valid_example"]["text"], list)


def test_analyze_file_endpoint_with_bank_sample() -> None:
    with open("examples/sample_bank_statement.txt", "rb") as sample_file:
        response = client.post(
            "/api/v1/tasks/analyze-file",
            data={"query": "Convert this bank statement to Excel and analyze it"},
            files={"file": ("sample_bank_statement.txt", sample_file, "text/plain")},
        )

    payload = response.json()

    assert response.status_code == 200
    assert payload["agent"] == "bank_statement"
    assert "excel" in payload["artifacts"]


def test_analyze_file_endpoint_with_bank_pdf_sample() -> None:
    with open("examples/sample_bank_statement.pdf", "rb") as sample_file:
        response = client.post(
            "/api/v1/tasks/analyze-file",
            data={"query": "Analyze this bank statement"},
            files={"file": ("sample_bank_statement.pdf", sample_file, "application/pdf")},
        )

    payload = response.json()

    assert response.status_code == 200
    assert payload["agent"] == "bank_statement"
    assert payload["data"]["transaction_count"] >= 5
    assert payload["client_response"]


def test_analyze_file_endpoint_with_bank_xlsx_sample() -> None:
    with open("examples/sample_bank_statement.xlsx", "rb") as sample_file:
        response = client.post(
            "/api/v1/tasks/analyze-file",
            data={"query": "Analyze this bank statement"},
            files={
                "file": (
                    "sample_bank_statement.xlsx",
                    sample_file,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

    payload = response.json()

    assert response.status_code == 200
    assert payload["agent"] == "bank_statement"
    assert payload["data"]["transaction_count"] >= 5


def test_analyze_file_endpoint_with_bank_xls_sample() -> None:
    with open("examples/sample_bank_statement.xls", "rb") as sample_file:
        response = client.post(
            "/api/v1/tasks/analyze-file",
            data={"query": "Analyze this bank statement"},
            files={"file": ("sample_bank_statement.xls", sample_file, "application/vnd.ms-excel")},
        )

    payload = response.json()

    assert response.status_code == 200
    assert payload["agent"] == "bank_statement"
    assert payload["data"]["transaction_count"] >= 5


def test_analyze_file_endpoint_with_bank_csv_sample() -> None:
    with open("examples/sample_bank_statement.csv", "rb") as sample_file:
        response = client.post(
            "/api/v1/tasks/analyze-file",
            data={"query": "Analyze this bank statement"},
            files={"file": ("sample_bank_statement.csv", sample_file, "text/csv")},
        )

    payload = response.json()

    assert response.status_code == 200
    assert payload["agent"] == "bank_statement"
    assert payload["data"]["transaction_count"] >= 5
