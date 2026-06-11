from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_web_app_serves_chat_interface() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "CA Agentic AI RAG" in response.text
    assert "Attach file" in response.text


def test_analyze_text_endpoint() -> None:
    response = client.post(
        "/api/v1/tasks/analyze-text",
        json={
            "query": "Analyze bank statement",
            "text": "2026-04-03 Cash Deposit 0 150000 400000",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert response.headers["x-llm-provider"] == "offline"
    assert response.headers["x-llm-fallback"] == "false"
    assert "Analysis Report" in response.text
    assert "bank_statement" in response.text


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

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "Analysis Report" in response.text
    assert "Key Observations" in response.text
    assert "bank_statement" in response.text


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

    assert response.status_code == 200
    assert "Analysis Report" in response.text
    assert "bank_statement" in response.text


def test_analyze_file_endpoint_with_bank_pdf_sample() -> None:
    with open("examples/sample_bank_statement.pdf", "rb") as sample_file:
        response = client.post(
            "/api/v1/tasks/analyze-file",
            data={"query": "Analyze this bank statement"},
            files={"file": ("sample_bank_statement.pdf", sample_file, "application/pdf")},
        )

    assert response.status_code == 200
    assert "Analysis Report" in response.text
    assert "bank_statement" in response.text


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

    assert response.status_code == 200
    assert "Analysis Report" in response.text
    assert "bank_statement" in response.text


def test_analyze_file_endpoint_with_bank_xls_sample() -> None:
    with open("examples/sample_bank_statement.xls", "rb") as sample_file:
        response = client.post(
            "/api/v1/tasks/analyze-file",
            data={"query": "Analyze this bank statement"},
            files={"file": ("sample_bank_statement.xls", sample_file, "application/vnd.ms-excel")},
        )

    assert response.status_code == 200
    assert "Analysis Report" in response.text
    assert "bank_statement" in response.text


def test_analyze_file_endpoint_with_bank_csv_sample() -> None:
    with open("examples/sample_bank_statement.csv", "rb") as sample_file:
        response = client.post(
            "/api/v1/tasks/analyze-file",
            data={"query": "Analyze this bank statement"},
            files={"file": ("sample_bank_statement.csv", sample_file, "text/csv")},
        )

    assert response.status_code == 200
    assert "Analysis Report" in response.text
    assert "bank_statement" in response.text


def test_learning_requires_consent_and_ca_approval() -> None:
    from app.agents.orchestrator import AgentOrchestrator
    from app.models.schemas import LearningOptions

    tenant_id = f"tenant-{uuid4().hex}"
    orchestrator = AgentOrchestrator()
    result = orchestrator.analyze_text(
        query="Analyze this bank statement",
        text="2026-04-03 Cash Deposit 0 150000 400000",
        learning_options=LearningOptions(
            tenant_id=tenant_id,
            learning_consent=True,
            approve_learning=False,
        ),
    )

    assert result.learned_context_path
    assert "/pending/" in result.learned_context_path
    assert not orchestrator.rag.retrieve(
        query="Cash Deposit",
        collections=[f"learned_{tenant_id}"],
    )

    approved = orchestrator.analyze_text(
        query="Analyze this bank statement",
        text="2026-04-03 Cash Deposit 0 150000 400000",
        learning_options=LearningOptions(
            tenant_id=tenant_id,
            learning_consent=True,
            approve_learning=True,
        ),
    )

    assert approved.learned_context_path
    assert "/approved/" in approved.learned_context_path
    assert orchestrator.rag.retrieve(
        query="Cash Deposit",
        collections=[f"learned_{tenant_id}"],
    )
