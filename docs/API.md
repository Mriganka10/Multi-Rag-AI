# API Reference

Base URL for local development:

```text
http://127.0.0.1:8000
```

## Health Check

```http
GET /health
```

Example:

```bash
curl http://127.0.0.1:8000/health
```

Response:

```json
{
  "status": "ok",
  "environment": "local"
}
```

## Analyze Text

```http
POST /api/v1/tasks/analyze-text
```

Use this endpoint when the document text is already available.

Request body:

```json
{
  "query": "Analyze this GST show cause notice",
  "text": "Show Cause Notice under section 73...",
  "tenant_id": "demo-client",
  "learning_consent": true,
  "approve_learning": false,
  "output_formats": ["pdf", "docx", "xlsx"]
}
```

For multiline text, use one of these valid JSON formats.

Option 1: escaped newline characters inside one string:

```json
{
  "query": "Analyze this bank statement",
  "text": "2026-04-03 Cash Deposit 0 150000 400000\n2026-04-07 Vendor Payment 85000 0 315000"
}
```

Option 2: array of lines. This is easiest in Swagger UI:

```json
{
  "query": "Analyze this bank statement",
  "text": [
    "2026-04-03 Cash Deposit 0 150000 400000",
    "2026-04-07 Vendor Payment 85000 0 315000",
    "2026-04-11 Interest Credit 0 3500 318500",
    "2026-04-15 Loan EMI 45000 0 273500",
    "2026-04-20 High Value Receipt 0 250000 523500"
  ],
  "tenant_id": "demo-client",
  "learning_consent": true,
  "approve_learning": false
}
```

Do not paste raw line breaks inside a JSON string. That is invalid JSON and will produce a 422 validation error.

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tasks/analyze-text \
  -H "Content-Type: application/json" \
  -d '{"query":"Analyze this GST show cause notice","text":"Show Cause Notice under section 73. It is alleged that input tax credit of INR 250000 was wrongly availed."}'
```

Response:

```text
Analysis Report

Summary
...

Key Observations
- ...

Recommended Next Steps
- ...

Review Caveat
Please review this output with a qualified CA before taking action.
```

Response headers:

```text
X-LLM-Provider: openai
X-LLM-Model: gpt-5.5
X-LLM-Fallback: false
```

These headers confirm whether the final response came from OpenAI or from offline local mode.

To request a generated response document, either mention the format in the query or provide
`output_formats`. Supported values are `pdf`, `docx`, and `xlsx`.

```json
{
  "query": "Analyze this notice and provide the response as PDF and Word",
  "text": "Show Cause Notice under section 73...",
  "output_formats": ["pdf", "docx"]
}
```

When documents are generated, the plain-text response contains authenticated download paths and
the `X-Generated-Artifacts` response header contains a Base64 URL-encoded JSON manifest used by
the web UI.

## Analyze File

```http
POST /api/v1/tasks/analyze-file
```

Use this endpoint for PDFs, images, text files, or CSV files.

Form fields:

- `query`: user instruction
- `file`: uploaded file
- `tenant_id`: client or engagement identifier for tenant-scoped RAG learning
- `learning_consent`: `true` only when the client/engagement opted into learning
- `approve_learning`: `true` only after CA approval; approved notes become retrievable RAG context
- `output_formats`: optional comma-separated formats such as `pdf,docx,xlsx`

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tasks/analyze-file \
  -F "query=Convert this bank statement to Excel and analyze it" \
  -F "tenant_id=demo-client" \
  -F "learning_consent=true" \
  -F "approve_learning=false" \
  -F "output_formats=pdf,docx" \
  -F "file=@examples/sample_bank_statement.txt"
```

When a requested response document is generated, it is stored under the signed-in tenant. In AWS,
the encrypted artifact is uploaded to the private S3 bucket and its metadata is registered in
PostgreSQL. Downloads require a valid session for the same tenant.

Natural-language format detection is also supported:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tasks/analyze-file \
  -F "query=Analyze this notice and provide a PDF response" \
  -F "file=@examples/sample_scn.txt"
```

The response headers still identify the final response provider and model:

```text
X-LLM-Provider: openai
X-LLM-Model: gpt-5.5
X-LLM-Fallback: false
X-Generated-Artifacts: <base64url artifact manifest>
```

## Download Generated Artifact

```http
GET /api/v1/artifacts/{artifact_id}/download
```

This endpoint requires the same authenticated browser session or API cookie that created the
analysis. A client receives `404` when the artifact belongs to another tenant.

Bank statement upload samples:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tasks/analyze-file \
  -F "query=Analyze this bank statement" \
  -F "file=@examples/sample_bank_statement.pdf"
```

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tasks/analyze-file \
  -F "query=Analyze this bank statement" \
  -F "file=@examples/sample_bank_statement.xlsx"
```

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tasks/analyze-file \
  -F "query=Analyze this bank statement" \
  -F "file=@examples/sample_bank_statement.xls"
```

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tasks/analyze-file \
  -F "query=Analyze this bank statement" \
  -F "file=@examples/sample_bank_statement.csv"
```

Other sample file tests:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tasks/analyze-file \
  -F "query=Analyze this GST show cause notice and draft a reply" \
  -F "file=@examples/sample_scn.txt"
```

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tasks/analyze-file \
  -F "query=Analyze financial statement ratios and anomalies" \
  -F "file=@examples/sample_financial_statement.txt"
```

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tasks/analyze-file \
  -F "query=Prepare draft ITR data from these inputs" \
  -F "file=@examples/sample_itr_inputs.txt"
```

## RAG Search

```http
GET /api/v1/rag/search?query=section%2073&collections=gst
```

Example:

```bash
curl "http://127.0.0.1:8000/api/v1/rag/search?query=section%2073&collections=gst"
```

Response:

```json
{
  "contexts": [
    {
      "collection": "gst",
      "score": 0.4333,
      "text": "Section 73 of the GST law...",
      "source": "data/knowledge/gst.txt"
    }
  ]
}
```

## Client Response Contract

The analysis endpoints return `text/plain`, not the internal developer JSON envelope. Generated
document links are appended under `Generated Documents`, while the web UI renders dedicated
download buttons.

The internal structured result is still used by the orchestrator for agent routing, RAG context retrieval,
artifact creation, audit logs, and learning controls.

If `LLM_PROVIDER=openai`, OpenAI must be called. The app no longer silently falls back to the offline response builder. If the OpenAI package, API key, quota, or request fails, the endpoint returns:

```text
502 LLM provider error
```

## RAG Learning Controls

Learning is controlled by three request fields:

- `tenant_id`: keeps learned knowledge scoped to one client or engagement.
- `learning_consent`: must be `true` before anything is saved for learning.
- `approve_learning`: must be `true` before the saved note becomes retrievable RAG context.

If `learning_consent=true` and `approve_learning=false`, the note is stored under a pending folder and audit logged, but future RAG retrieval will not use it.

If both are `true`, the note is stored under the tenant's approved folder and can be retrieved in future prompts for that same tenant.

In AWS, inspect persistent learning metadata with:

```sql
select learning_id, tenant_id, status, agent, storage_location,
       approved_by, qdrant_collection, qdrant_point_id,
       indexing_status, indexing_error, created_at, approved_at
from rag_learning_records
order by created_at desc;
```
