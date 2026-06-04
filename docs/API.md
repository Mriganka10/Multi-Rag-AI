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
