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
Specialist Agent JSON Analysis
        |
        v
Relevant RAG Context Retrieval
        |
        v
LLM / Offline Response Builder
        |
        v
Client-readable response + developer JSON
        |
        v
Learned response stored under data/knowledge/learned
```

## Response Modes

### Offline Mode

Default mode:

```text
LLM_PROVIDER=offline
```

This does not call any external LLM. It creates a deterministic human-readable response from the structured agent output. Use this mode for local testing and demos without API keys.

### OpenAI Mode

OpenAI mode:

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-5.4-mini
```

Install cloud dependencies:

```bash
python -m pip install -e ".[dev,cloud]"
```

Then restart the API:

```bash
python -m uvicorn app.main:app --reload
```

## API Response Shape

The API still returns structured JSON for developers, but now also includes a client-readable response.

Important fields:

```json
{
  "agent": "bank_statement",
  "summary": "Analyzed 8 transactions...",
  "client_response": "Analysis completed using the bank statement agent...",
  "data": {},
  "contexts": [],
  "llm": {
    "provider": "offline",
    "model": "deterministic-template",
    "used_fallback": false
  },
  "learned_context_path": "data/knowledge/learned/bank_statement_20260606050000.txt",
  "requires_human_review": true
}
```

## RAG Learning

When `RAG_LEARNING_ENABLED=true`, generated client responses are stored under:

```text
data/knowledge/learned
```

The retriever is refreshed after each learned response, so future requests can retrieve prior learned context.

For production, this must be controlled carefully because client documents and generated outputs may contain confidential information.

Recommended production controls:

- Make learning opt-in per client or engagement.
- Store learned material in a tenant-specific collection.
- Add CA approval before learned content becomes reusable knowledge.
- Keep audit logs for what was learned and who approved it.
- Avoid storing sensitive personal data unless strictly required.

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
  ]
}
```

Expected:

- `agent` should be `bank_statement`.
- `client_response` should contain a human-readable explanation.
- `llm.provider` should be `offline` unless OpenAI mode is enabled.
- `learned_context_path` should be populated if RAG learning is enabled.

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

- `agent` should be `bank_statement`.
- `client_response` should be populated.
- `artifacts.excel` should be populated when transaction rows are detected.

