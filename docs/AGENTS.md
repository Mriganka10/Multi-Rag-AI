# Agent Workflows

## Agent Orchestrator

File: `app/agents/orchestrator.py`

The orchestrator decides which specialist agent should handle a task. It uses simple keyword-based routing in the POC.

Routing examples:

- Notice, SCN, section 73, section 74 -> SCN Agent
- ITR, Form 16, AIS, 26AS -> ITR Agent
- Balance sheet, current assets, revenue -> Financial Analysis Agent
- Bank, debit, credit, balance -> Bank Statement Agent
- Otherwise -> OCR Agent

Production routing can later be upgraded to an LLM classifier or LangGraph supervisor.

## OCR Agent

File: `app/agents/ocr_agent.py`

Responsibilities:

- Extract text from PDFs using `pypdf`.
- Extract text from images using `pytesseract`.
- Read `.txt` and `.csv` files directly.
- Parse transaction-like rows.
- Export parsed transactions to Excel.

Limitations:

- Scanned PDFs need OCR, not normal PDF text extraction.
- Bank statement layouts vary widely, so production parsing should use bank-specific adapters or document AI models.

## Bank Statement Agent

File: `app/agents/bank_statement_agent.py`

Responsibilities:

- Identify debit and credit totals.
- Detect cash-related transactions.
- Detect interest income.
- Detect loan or EMI transactions.
- Detect high-value transactions of INR 100000 or more.
- Return observations useful for CA review.

Suggested production enhancements:

- Bank-specific statement parsers.
- Opening and closing balance reconciliation.
- Duplicate transaction detection.
- Related-party and round-tripping indicators.
- TDS and interest reconciliation.

## SCN Agent

File: `app/agents/scn_agent.py`

Responsibilities:

- Summarize Show Cause Notice text.
- Detect legal sections.
- Detect monetary amounts.
- Extract department allegations.
- Retrieve GST and tax context from Multi-RAG.
- Generate a draft reply for CA review.

Human review requirement:

SCN replies must not be submitted directly from AI output. The CA must verify facts, limitation, jurisdiction, attachments, portal data, and hearing timelines.

## Financial Analysis Agent

File: `app/agents/financial_agent.py`

Responsibilities:

- Extract numeric financial metrics from text.
- Compute common ratios:
  - Current ratio
  - Quick ratio
  - Debt-equity ratio
  - Net profit margin
  - Return on assets
  - Return on equity
- Detect balance sheet equation conflicts.
- Detect high-level numeric anomaly indicators using Isolation Forest.

Limitations:

- This agent currently expects simple text with label-value pairs.
- Production analysis should parse structured trial balances, financial statements, and ledgers.

## ITR Draft Agent

File: `app/agents/itr_agent.py`

Responsibilities:

- Extract likely salary, interest, capital gain, 80C, and TDS values from text.
- Identify missing documents such as Form 16, AIS, 26AS, and bank statement.
- Return draft-only preparation data.

Important boundary:

The ITR agent must not file returns or submit data to a government portal without explicit CA approval.

## Recommended LangGraph Upgrade

The POC uses a lightweight Python orchestrator. For a more agentic production workflow, replace it with LangGraph:

```text
Supervisor
   |
   +-- OCR Node
   +-- Bank Node
   +-- SCN Node
   +-- Financial Node
   +-- ITR Node
   +-- Human Review Node
   +-- Report Generator Node
```

LangGraph becomes useful when agents need to collaborate, retry, ask for missing data, or pause for human approval.
