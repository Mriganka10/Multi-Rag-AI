# Models and Agent Techniques

## Summary

The current branch uses specialist Python agents for domain analysis and one shared OpenAI model for the final human-readable response.

The agents do not each have a separate LLM model today. Instead, the flow is:

```text
Prompt or uploaded file
        |
        v
Agent Orchestrator
        |
        v
Selected specialist agent
        |
        v
Internal structured analysis
        |
        v
RAG context retrieval
        |
        v
OpenAI model
        |
        v
Human-readable client response
```

## Current OpenAI Model

The final response model is configured in `.env`:

```text
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-5.5
```

The default in `.env.example` is:

```text
OPENAI_MODEL=gpt-5.5
```

This model is used for all final client-facing responses:

- SCN analysis responses.
- Bank statement analysis responses.
- Financial analysis responses.
- ITR draft helper responses.
- OCR/document extraction responses.

If `LLM_PROVIDER=openai`, the app must call OpenAI. It does not silently fall back to the offline template. A failed OpenAI request returns `502 LLM provider error`.

## Agent Analysis vs OpenAI Response

The specialist agent and the OpenAI model have different responsibilities.

The specialist agent performs domain analysis first. It uses Python code, rules, parsers, calculations, regular expressions, and local retrieval. This creates a controlled internal result.

OpenAI runs after that. It receives the internal result, relevant RAG context, the selected agent name, the user query, and a source excerpt. Its job is to convert those inputs into a professional human-readable response.

This means the system is not:

```text
User -> OpenAI directly
```

The intended flow is:

```text
User -> Orchestrator -> Specialist Agent -> RAG -> OpenAI -> Final Response
```

For example, an SCN request first goes to the SCN agent. The SCN agent detects the section, amount, allegation, and draft response points. RAG then retrieves relevant GST or tax context. OpenAI then writes the final readable answer.

For a bank statement upload, the file is extracted first. The orchestrator routes it to the bank statement agent. The bank statement agent calculates credits, debits, cash transactions, interest entries, EMI entries, and high-value items. OpenAI then writes the final commentary.

## Agent-by-Agent Map

| Agent | File | Current model or technique | OpenAI usage |
| --- | --- | --- | --- |
| Agent Orchestrator | `app/agents/orchestrator.py` | Keyword/rule-based router | Does not call OpenAI directly; selects the agent first. |
| OCR Agent | `app/agents/ocr_agent.py` | `pypdf`, `pytesseract`, direct text/CSV read, transaction-row parser | OpenAI writes the final response after OCR/extraction. |
| Bank Statement Agent | `app/agents/bank_statement_agent.py` | Rule-based transaction parser and `pandas` aggregation | OpenAI receives bank totals, observations, extracted text, and RAG context. |
| SCN Agent | `app/agents/scn_agent.py` | Regex section/amount/allegation extraction, deterministic draft reply, RAG retrieval | OpenAI receives notice analysis, draft reply, legal context, and source text. |
| Financial Analysis Agent | `app/agents/financial_agent.py` | Ratio formulas plus `IsolationForest` anomaly detection | OpenAI receives ratios, conflicts, anomalies, and RAG context. |
| ITR Agent | `app/agents/itr_agent.py` | Regex/rule-based draft tax value extraction | OpenAI receives draft preparation values and missing-document checklist. |
| Multi-RAG | `app/rag/multi_rag.py` | `TfidfVectorizer` and cosine similarity | Supplies context to OpenAI; does not call OpenAI embeddings yet. |
| RAG Learning Store | `app/rag/learning.py` | Tenant-scoped file store plus audit log | Saves generated responses when learning consent is enabled. |

## Example: SCN Query

Input:

```text
Show Cause Notice under section 73 of the CGST Act.
It is alleged that input tax credit of INR 250000 was wrongly availed...
```

Current route:

```text
analyze-text -> AgentOrchestrator -> SCNAgent -> Multi-RAG -> OpenAI gpt-5.5 -> plain text response
```

Why SCN agent is selected:

- Text contains `Show Cause Notice`.
- Text contains `section 73`.
- Text contains notice/recovery language.

## Example: Bank Statement Upload

Input:

```text
Uploaded PDF, CSV, XLS, XLSX, or TXT bank statement
```

Current route:

```text
analyze-file -> OCRAgent/extraction -> AgentOrchestrator -> BankStatementAgent -> Multi-RAG -> OpenAI gpt-5.5 -> plain text response -> requested document exports
```

Why bank statement agent is selected:

- Query or extracted text contains bank terms such as `bank`, `statement`, `debit`, `credit`, or `balance`.
- Parsed transaction rows are converted into bank analysis and Excel artifacts when possible.
- The final response can also be exported as PDF, Word, Excel, or all three formats.

## Response Verification

The API returns `text/plain`, but the response headers show which model produced the final response:

```text
X-LLM-Provider: openai
X-LLM-Model: gpt-5.5
X-LLM-Fallback: false
```

If the response header says:

```text
X-LLM-Provider: offline
```

then the API is running in offline mode and is not using OpenAI.

## Current Limitations

- Routing is rule-based, not yet an LLM classifier.
- RAG uses TF-IDF, not OpenAI embeddings or Qdrant yet.
- OCR for complex scanned documents should be upgraded to Azure Document Intelligence, Google Document AI, or another production OCR service.
- The same OpenAI model is used for every final response.
- Agent-specific model selection can be added later if needed.

## Recommended Production Direction

| Area | Current | Production recommendation |
| --- | --- | --- |
| Routing | Keyword rules | LangGraph supervisor or LLM classifier with confidence scoring. |
| RAG retrieval | TF-IDF local files | Qdrant plus OpenAI embeddings and citation tracking. |
| OCR | Local extraction and Tesseract | Cloud document intelligence with bank/notice parsers. |
| LLM response | Shared `gpt-5.5` | Configurable model policy per workflow and cost tier. |
| Learning | Tenant-scoped pending/approved files | Database-backed approval workflow with audit trail. |
| Security | Local `.env` | Secret manager, auth, role-based tenant access, encrypted storage. |
