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

## Deployed AWS Architecture

The public demo is deployed on AWS Elastic Beanstalk in `ap-south-1`.

```text
Client Browser
        |
        v
Elastic Beanstalk public URL
        |
        v
Elastic Beanstalk environment: ca-agentic-ai-prod
        |
        v
EC2 instance: i-0c35f5212d41a1752
        |
        v
Docker container running FastAPI
        |
        +-- Amazon S3: uploaded client files
        +-- Amazon RDS PostgreSQL: audit events
        +-- OpenAI API: final response generation
```

Elastic Beanstalk is the deployment manager. It provisions and manages the EC2 server, deploys the Docker application bundle, monitors health, and exposes the public URL.

EC2 is the actual virtual server where the container runs. In this project, the EC2 instance should normally be treated as a managed part of Elastic Beanstalk. Direct EC2 actions, such as rebooting the instance, are used only for operational fixes like refreshing the SSM agent after IAM role changes.

The deployed URL is:

```text
http://ca-agentic-ai-prod.eba-uve6zn4c.ap-south-1.elasticbeanstalk.com/
```

The health endpoint is:

```text
http://ca-agentic-ai-prod.eba-uve6zn4c.ap-south-1.elasticbeanstalk.com/health
```

See `docs/AWS_DEPLOYMENT.md` for the deployment guide and `docs/AWS_DEPLOYMENT_WALKTHROUGH.md` for the detailed step-by-step explanation.

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

This is an important product and architecture point. The platform does not send the user input directly to OpenAI as the first step. The domain agent runs first, prepares a controlled internal result, retrieves relevant context, and only then asks OpenAI to produce the final professional response.

The intended flow is:

```text
User input
    -> Agent Orchestrator
    -> Selected specialist agent
    -> Internal structured analysis
    -> RAG context retrieval
    -> OpenAI final response generation
    -> Human-readable client response
```

When `LLM_PROVIDER=openai`, the service calls the configured OpenAI model from `OPENAI_MODEL`, currently `gpt-5.5` in `.env.example`. The OpenAI prompt receives:

- User query.
- Selected agent name.
- Structured internal agent result.
- Retrieved RAG context.
- Extracted source text excerpt.

The public analysis APIs do not return the internal JSON object. They return formatted human-readable plain text.

Internally, the backend may work with a structure like this:

```json
{
  "agent": "scn",
  "section": "73",
  "amount": 250000,
  "issue": "ITC mismatch"
}
```

The public API converts that into a client-readable response like this:

```text
The notice appears to relate to alleged wrongful availment of input tax credit of INR 250000 under Section 73 of the CGST Act.
```

When OpenAI mode is selected, the system must call OpenAI. It no longer silently falls back to the offline template. If the API key, package, quota, or OpenAI request fails, the API returns `502 LLM provider error`.

The API response includes diagnostic headers:

```text
X-LLM-Provider: openai
X-LLM-Model: gpt-5.5
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
8. The export service detects requested PDF, Word, or Excel formats.
9. Requested response documents are generated and stored under the signed-in tenant.
10. API returns the OpenAI-generated report as `text/plain` with authenticated artifact links.

The internal `TaskResult` still contains `summary`, `data`, `contexts`, `artifacts`, `llm`, and `requires_human_review`, but that object is not exposed as the client-facing response.

## Generated Response Documents

`app/artifacts/service.py` converts the final client-facing response into:

- PDF using ReportLab.
- Word `.docx` using python-docx.
- Excel `.xlsx` using openpyxl.

Formats can be selected explicitly in the UI/API or detected from phrases such as `provide a PDF`,
`export to Word`, or `give this in Excel`.

Generated files use a UUID artifact identifier and tenant-specific path. In AWS:

- The file is encrypted and stored under the tenant's S3 artifact prefix.
- Artifact metadata is stored in the PostgreSQL `generated_artifacts` table.
- `GET /api/v1/artifacts/{artifact_id}/download` verifies the signed-in tenant before streaming it.
- Another tenant receives `404`, preventing artifact enumeration or cross-client access.

### Step 5: Deterministic Domain Analysis

The selected specialist agent performs fixed Python-based analysis before OpenAI is called. Deterministic means the agent uses code rules, regular expressions, calculations, parsers, and known business logic. The same input should generally produce the same internal result.

For an SCN input such as:

```text
Show Cause Notice under section 73 of the CGST Act.
It is alleged that input tax credit of INR 250000 was wrongly availed due to mismatch between GSTR-2B and GSTR-3B.
```

The SCN agent can extract:

```text
Agent: scn
Section: 73
Amount: INR 250000
Issue: ITC mismatch between GSTR-2B and GSTR-3B
Output type: draft reply required
```

For a bank statement input such as:

```text
Cash Deposit 150000
Vendor Payment 85000
Interest Credit 3500
```

The bank statement agent can calculate:

```text
Total credits
Total debits
Cash deposits
Interest income
High-value transactions
Loan or EMI entries
```

This prevents the system from behaving like a plain chatbot. The agent first prepares a structured domain result, and OpenAI is used later to explain that result professionally.

### Step 6: RAG Context for Agent and Tenant

RAG means Retrieval-Augmented Generation. After the agent is selected, the system searches the relevant knowledge base and attaches useful background context.

If the selected agent is `scn`, the system retrieves notice, GST, Income Tax, or legal response context depending on the content. For example, an SCN under Section 73 of the CGST Act may retrieve context explaining that Section 73 deals with tax not paid, short paid, or wrongly availed ITC in non-fraud cases.

Tenant means a client, firm, workspace, or engagement boundary. In production, learned knowledge for one client must not leak into another client. That is why learned RAG material is stored under tenant-specific paths and only approved content is loaded back into retrieval.

Example:

```text
Tenant A approved learned notes
Tenant B approved learned notes
Tenant C approved learned notes
```

When Tenant A asks a question, the system should retrieve Tenant A knowledge plus common approved legal/accounting knowledge, not Tenant B confidential material.

### Step 7: OpenAI Prompt Inputs

OpenAI receives a controlled prompt assembled by the backend. It does not receive only the raw user text. The prompt includes:

1. User query: what the user asked.
2. Selected agent name: for example `scn`, `bank_statement`, `financial`, `itr`, or `ocr`.
3. Structured internal agent result: the extracted values, calculations, flags, and draft observations.
4. Retrieved RAG context: relevant legal, tax, accounting, or learned context.
5. Extracted source text excerpt: a limited excerpt from the uploaded file or pasted text.

For an SCN, the effective OpenAI input is conceptually:

```text
User query:
Analyze this GST show cause notice and draft a reply.

Selected agent:
scn

Internal structured result:
Section 73 detected.
Amount INR 250000 detected.
Issue: ITC mismatch.
Draft response required.

RAG context:
CGST Section 73 context.
ITC reconciliation context.

Source excerpt:
Original notice text excerpt.
```

OpenAI then converts the controlled internal result and retrieved knowledge into a polished, human-readable response.

### Verifying OpenAI Usage

The easiest way to confirm whether OpenAI was used is to inspect the response headers. Successful OpenAI responses include:

```text
X-LLM-Provider: openai
X-LLM-Model: gpt-5.5
X-LLM-Fallback: false
```

In Swagger UI, these headers may not always be obvious. They are easier to inspect with Postman, a browser network tab, or `curl -i`:

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/tasks/analyze-text \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Analyze this GST show cause notice and draft a reply",
    "text": "Show Cause Notice under section 73 of the CGST Act. It is alleged that input tax credit of INR 250000 was wrongly availed due to mismatch between GSTR-2B and GSTR-3B."
  }'
```

If `LLM_PROVIDER=openai` is set and OpenAI fails, the API returns `502 LLM provider error`. This is intentional because silent fallback would make it difficult to know whether OpenAI was actually used.

## Production Architecture Direction

Recommended production upgrades:

- Replace local file storage with S3 or equivalent object storage.
- Replace TF-IDF retrieval with Qdrant vector search.
- Add OpenAI embeddings and reranking.
- Add PostgreSQL for clients, jobs, document metadata, review status, and audit trail.
- Add background workers for large document processing.
- Add human approval workflow before any tax filing or notice submission.

## Persistent RAG Learning

The deployed learning pipeline separates responsibilities:

- **S3:** encrypted source of record for pending and approved learned responses.
- **PostgreSQL:** `rag_learning_records` approval, integrity, storage, and indexing metadata.
- **Qdrant:** embeddings for approved records only, isolated by tenant collection.

S3 hierarchy:

```text
<S3_PREFIX>/tenants/<tenant-id>/rag/pending/<learning-id>.txt
<S3_PREFIX>/tenants/<tenant-id>/rag/approved/<learning-id>.txt
```

Qdrant collection:

```text
<QDRANT_COLLECTION_PREFIX>_learned_<tenant-id>
```

Pending material is never indexed. If Qdrant is not configured, S3 and PostgreSQL persistence
still succeeds and the metadata records `indexing_status=not_configured`.
