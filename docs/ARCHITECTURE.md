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
        |
        v
OpenAI LLM Response Layer
        |
        v
Human-readable client response
```

## Runtime Components

### FastAPI Layer

Entry point: `app/main.py`

Responsibilities:

- Expose health and task endpoints.
- Accept text and file uploads.
- Return client-facing `text/plain` analysis reports for analysis endpoints.
- Return response headers that identify the LLM provider and model used.
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
- Attach the routing decision to the internal result.
- Retrieve agent-appropriate RAG context.
- Send the internal agent result, source text excerpt, and RAG context to the LLM response layer.

### Domain Agents

- `OCRAgent`: extracts text and parses transaction-like rows.
- `BankStatementAgent`: summarizes credits, debits, cash transactions, interest, EMI, and high-value transactions.
- `SCNAgent`: summarizes notices, identifies allegations and sections, retrieves context, and drafts a reply.
- `FinancialAnalysisAgent`: extracts metrics, computes ratios, detects conflicts, and flags anomaly indicators.
- `ITRAgent`: extracts draft return values and missing document checklist.

### Multi-RAG Layer

File: `app/rag/multi_rag.py`

The current implementation uses local text files and TF-IDF retrieval. It intentionally keeps the interface simple so it can later be replaced by Qdrant plus embeddings.

Approved learned content is loaded from tenant-scoped folders under `data/knowledge/learned/{tenant_id}/approved`. Pending learned notes are stored and audit logged, but they are not loaded back into retrieval.

### LLM Response Layer

File: `app/llm/service.py`

The final client-facing response is generated after the selected specialist agent has already run.

When `LLM_PROVIDER=openai`, the service calls the configured OpenAI model from `OPENAI_MODEL`, currently `gpt-4.1-mini` in `.env.example`. The OpenAI prompt receives:

- User query.
- Selected agent name.
- Structured internal agent result.
- Retrieved RAG context.
- Extracted source text excerpt.

The public analysis APIs do not return the internal JSON object. They return formatted human-readable plain text.

When OpenAI mode is selected, the system must call OpenAI. It no longer silently falls back to the offline template. If the API key, package, quota, or OpenAI request fails, the API returns `502 LLM provider error`.

The API response includes diagnostic headers:

```text
X-LLM-Provider: openai
X-LLM-Model: gpt-4.1-mini
X-LLM-Fallback: false
```

If `LLM_PROVIDER=offline`, the deterministic response builder is used for local testing only.

## Request Flow

1. User sends text or uploads a file.
2. File uploads are saved under `data/uploads`.
3. OCR agent extracts text from supported files.
4. Orchestrator selects the correct specialist agent.
5. Specialist agent performs deterministic domain analysis.
6. RAG context is retrieved for the selected agent and tenant.
7. OpenAI receives the internal analysis, RAG context, and source excerpt.
8. API returns the OpenAI-generated human-readable report as `text/plain`.

The internal `TaskResult` still contains `summary`, `data`, `contexts`, `artifacts`, `llm`, and `requires_human_review`, but that object is not exposed as the client-facing response.

## Production Architecture Direction

Recommended production upgrades:

- Replace local file storage with S3 or equivalent object storage.
- Replace TF-IDF retrieval with Qdrant vector search.
- Add OpenAI embeddings and reranking.
- Add PostgreSQL for clients, jobs, document metadata, review status, and audit trail.
- Add background workers for large document processing.
- Add human approval workflow before any tax filing or notice submission.
