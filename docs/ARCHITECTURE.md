# Architecture

## High-Level Design

```text
Client / UI / API Consumer
        |
        v
FastAPI Application
        |
        v
Agent Orchestrator
        |
        +-- OCR Agent
        +-- Bank Statement Agent
        +-- SCN Agent
        +-- Financial Analysis Agent
        +-- ITR Draft Agent
        |
        v
Multi-RAG Retriever
        |
        +-- GST Knowledge
        +-- Income Tax Knowledge
        +-- Accounting Standards Knowledge
        +-- Future Case Law Knowledge
        +-- Future Notifications Knowledge
```

## Runtime Components

### FastAPI Layer

Entry point: `app/main.py`

Responsibilities:

- Expose health and task endpoints.
- Accept text and file uploads.
- Return typed JSON responses.
- Keep the backend UI-agnostic.

### API Routes

File: `app/api/routes.py`

Endpoints:

- `GET /health`
- `POST /api/v1/tasks/analyze-text`
- `POST /api/v1/tasks/analyze-file`
- `GET /api/v1/rag/search`

### Agent Orchestrator

File: `app/agents/orchestrator.py`

Responsibilities:

- Inspect query and extracted text.
- Decide the best agent for the task.
- Run the selected specialist agent.
- Attach the routing decision to the response.

### Domain Agents

- `OCRAgent`: extracts text and parses transaction-like rows.
- `BankStatementAgent`: summarizes credits, debits, cash transactions, interest, EMI, and high-value transactions.
- `SCNAgent`: summarizes notices, identifies allegations and sections, retrieves context, and drafts a reply.
- `FinancialAnalysisAgent`: extracts metrics, computes ratios, detects conflicts, and flags anomaly indicators.
- `ITRAgent`: extracts draft return values and missing document checklist.

### Multi-RAG Layer

File: `app/rag/multi_rag.py`

The current implementation uses local text files and TF-IDF retrieval. It intentionally keeps the interface simple so it can later be replaced by Qdrant plus embeddings.

## Request Flow

1. User sends text or uploads a file.
2. File uploads are saved under `data/uploads`.
3. OCR agent extracts text from supported files.
4. Orchestrator selects the correct specialist agent.
5. Specialist agent performs analysis and optionally calls Multi-RAG.
6. Response returns structured JSON with `summary`, `data`, `contexts`, `artifacts`, and `requires_human_review`.

## Production Architecture Direction

Recommended production upgrades:

- Replace local file storage with S3 or equivalent object storage.
- Replace TF-IDF retrieval with Qdrant vector search.
- Add OpenAI embeddings and reranking.
- Add PostgreSQL for clients, jobs, document metadata, review status, and audit trail.
- Add background workers for large document processing.
- Add human approval workflow before any tax filing or notice submission.
