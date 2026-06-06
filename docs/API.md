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
  "text": "Show Cause Notice under section 73..."
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
  ]
}
```

Do not paste raw line breaks inside a JSON string. That is invalid JSON and will produce a 422 validation error.

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tasks/analyze-text \
  -H "Content-Type: application/json" \
  -d '{"query":"Analyze this GST show cause notice","text":"Show Cause Notice under section 73. It is alleged that input tax credit of INR 250000 was wrongly availed."}'
```

Response shape:

```json
{
  "agent": "scn",
  "summary": "SCN reviewed and draft response prepared for CA review.",
  "data": {},
  "contexts": [],
  "artifacts": {},
  "requires_human_review": true
}
```

## Analyze File

```http
POST /api/v1/tasks/analyze-file
```

Use this endpoint for PDFs, images, text files, or CSV files.

Form fields:

- `query`: user instruction
- `file`: uploaded file

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tasks/analyze-file \
  -F "query=Convert this bank statement to Excel and analyze it" \
  -F "file=@examples/sample_bank_statement.txt"
```

When transaction rows are detected, the API writes an Excel artifact under `data/outputs` and returns the artifact path.

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

## Response Fields

### `agent`

The specialist agent selected by the orchestrator.

Possible values:

- `ocr`
- `bank_statement`
- `scn`
- `financial`
- `itr`
- `general`

### `summary`

Short human-readable result summary.

### `data`

Structured agent-specific result payload.

### `contexts`

Retrieved RAG context used by the agent.

### `artifacts`

Generated files, such as Excel output paths.

### `requires_human_review`

Boolean flag. High-risk CA workflows should remain `true` until a qualified professional approves the output.
