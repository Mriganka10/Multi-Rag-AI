# LLM Responses and RAG Learning

## Overview

The platform now supports an LLM response layer on top of the existing specialist agents.

The flow is:

```text
User Prompt / Uploaded File
        |
        v
Agent Orchestrator
        |
        v
Specialist Agent Internal Analysis
        |
        v
Relevant RAG Context Retrieval
        |
        v
LLM / Offline Response Builder
        |
        v
Client-readable plain text response
        |
        v
Learned response stored under data/knowledge/learned
```

## Response Modes

### OpenAI Mode

Default mode:

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4.1-mini
```

This calls OpenAI for the final client-readable response for both text prompts and file uploads.

Install cloud dependencies:

```bash
python -m pip install -e ".[dev,cloud]"
```

Then restart the API:

```bash
python -m uvicorn app.main:app --reload
```

### Offline Fallback

If `LLM_PROVIDER=offline`, or if OpenAI mode is configured without a key during local development,
the app uses a deterministic plain-text response builder. This keeps local tests and demos runnable,
but production should provide `OPENAI_API_KEY`.

Offline mode:

```text
LLM_PROVIDER=offline
```

## API Response Shape

The analysis APIs return human-readable plain text, not the internal JSON result.

Example response:

```text
Analysis Report

Summary
The uploaded bank statement has been reviewed for transaction movement and risk indicators.

Key Observations
- Cash deposits and high-value receipts need review.
- Interest credits may need reconciliation with reported income.

Recommended Next Steps
- Reconcile high-value credits with invoices or supporting documents.
- Review the output with a qualified CA before filing or responding.
```

The internal `TaskResult` object remains inside the Python application for routing, artifacts,
RAG context, audit logging, and tests.

## RAG Learning

Learning is opt-in and approval-gated.

Request controls:

- `tenant_id`: scopes learned notes to a client or engagement.
- `learning_consent`: saves a learning note only when true.
- `approve_learning`: makes that note retrievable only when true.

Pending notes:

```text
data/knowledge/learned/{tenant_id}/pending
```

Approved notes:

```text
data/knowledge/learned/{tenant_id}/approved
```

Only approved notes are loaded back into the retriever.

For production, this must be controlled carefully because client documents and generated outputs may contain confidential information.

Recommended production controls:

- Make learning opt-in per client or engagement.
- Store learned material in a tenant-specific collection.
- Add CA approval before learned content becomes reusable knowledge.
- Keep audit logs for what was learned and who approved it.
- Avoid storing sensitive personal data unless strictly required.

The POC writes audit events to:

```text
data/knowledge/learning_audit.jsonl
```

## How To Test

### Analyze Text

Endpoint:

```text
POST /api/v1/tasks/analyze-text
```

Body:

```json
{
  "query": "Analyze this bank statement and explain the key observations to a client",
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

Expected:

- Response content type should be `text/plain`.
- Response should contain a human-readable analysis with headings and spacing.
- With OpenAI configured, the final response should come from the configured OpenAI model.
- With `approve_learning=false`, learned content is saved as pending and is not retrieved later.
- With `approve_learning=true`, learned content becomes retrievable for the same `tenant_id`.

### Analyze File

Endpoint:

```text
POST /api/v1/tasks/analyze-file
```

Query:

```text
Analyze this bank statement and explain the key observations to a client
```

Upload one sample file:

```text
examples/sample_bank_statement.pdf
examples/sample_bank_statement.xls
examples/sample_bank_statement.xlsx
examples/sample_bank_statement.csv
examples/sample_bank_statement.txt
```

Expected:

- Response content type should be `text/plain`.
- Response should contain a human-readable analysis.
- Excel artifacts are still generated internally under `data/outputs` when transaction rows are detected.
