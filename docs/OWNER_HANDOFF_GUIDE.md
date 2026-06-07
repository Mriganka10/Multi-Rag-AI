# Owner Handoff Guide

This document is for the project owner to review the POC step by step, explain it to the technical team, and guide the business team for client presentation.

## 1. Purpose of the POC

This repository contains a Python proof of concept for an Agentic AI Multi-RAG platform designed for Chartered Accountants.

The system can:

1. Understand a user query.
2. Route the query to the correct specialist agent.
3. Process text or uploaded documents.
4. Retrieve relevant tax/accounting context.
5. Generate internal structured analysis.
6. Use OpenAI to convert that internal analysis into a human-readable client response.
7. Keep high-risk outputs marked for CA review.

This is not yet a full production product. It is a working technical POC to demonstrate the core intelligence layer.

## 2. How You Should Review the Repository

Go through the documents in this order.

### Step 1: README

File: `README.md`

Purpose:

- Gives a short overview of the system.
- Shows how to run the API.
- Links all important documentation.

What to understand:

- This is a FastAPI-based backend POC.
- It has multiple specialist agents.
- It has an offline Multi-RAG layer.
- It has an OpenAI final response layer.
- It is designed for CA workflows.

### Step 2: Project Brief

File: `docs/PROJECT_BRIEF.md`

Purpose:

- Explains why the system exists.
- Defines the MVP scope.
- Lists target users.
- Explains success criteria.

Use this document when explaining the project vision to both business and technical teams.

### Step 3: Architecture

File: `docs/ARCHITECTURE.md`

Purpose:

- Explains the system design.
- Shows how the user request flows through the backend.

Simple explanation:

```text
User -> FastAPI -> Agent Orchestrator -> Specialist Agent -> Multi-RAG -> OpenAI -> Human-readable Response
```

Use this document with the technical team.

### Step 4: Setup Guide

File: `docs/SETUP.md`

Purpose:

- Helps the tech team clone and run the project locally.

Basic commands:

```bash
git clone https://github.com/Mriganka10/Multi-Rag-AI.git
cd Multi-Rag-AI
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,cloud]"
cp .env.example .env
uvicorn app.main:app --reload
```

Open the API documentation:

```text
http://127.0.0.1:8000/docs
```

### Step 5: API Reference

File: `docs/API.md`

Purpose:

- Shows how to test the system through API calls.
- Explains text analysis, file upload, and RAG search endpoints.

Use this document when the technical team wants to test the backend manually.

### Step 6: Agent Workflows

File: `docs/AGENTS.md`

Purpose:

- Explains each AI agent.
- Shows what each agent currently does.
- Defines boundaries and limitations.

Agents included:

1. OCR Agent
2. Bank Statement Agent
3. SCN Agent
4. Financial Analysis Agent
5. ITR Draft Agent
6. Agent Orchestrator

### Step 6A: Models and Agent Techniques

File: `docs/MODELS_AND_AGENTS.md`

Purpose:

- Explains which model or technique each agent currently uses.
- Clarifies that all final client-facing responses currently use the configured OpenAI model.
- Helps the team explain that specialist agents run before OpenAI is called.

### Step 7: Multi-RAG Design

File: `docs/RAG_DESIGN.md`

Purpose:

- Explains the current RAG implementation.
- Explains how it should evolve into Qdrant and embeddings.

Current status:

- Uses local text files.
- Uses TF-IDF retrieval.
- Works without external services.

Future target:

- Qdrant vector database.
- OpenAI embeddings.
- Source citations.
- Separate collections for GST, Income Tax, Accounting Standards, Case Laws, Notifications, and Client Documents.

### Step 8: Security and Compliance

File: `docs/SECURITY_AND_COMPLIANCE.md`

Purpose:

- Explains human review requirements.
- Explains sensitive data concerns.
- Explains production controls.

Important point:

The system must not file ITRs, submit SCN replies, or finalize tax positions without CA approval.

### Step 9: Roadmap

File: `docs/ROADMAP.md`

Purpose:

- Shows the next development phases.
- Helps you assign future tasks.

Use this document to plan technical milestones.

## 3. Explanation for the Technical Team

Tell the technical team:

"This is a backend POC for an Agentic AI system for Chartered Accountants. The main architecture is FastAPI plus an Agent Orchestrator plus multiple domain agents. The selected specialist agent runs first, RAG context is attached, and OpenAI then generates the final human-readable response. The current RAG layer is offline TF-IDF, but the code is structured so Qdrant, embeddings, stronger OCR, and approval workflows can be added later."

## 4. Technical Team Walkthrough

Ask the technical team to follow these steps.

### Step 1: Clone and Run

They should clone the repository and run the server using `docs/SETUP.md`.

### Step 2: Open Swagger UI

Open:

```text
http://127.0.0.1:8000/docs
```

### Step 3: Test Health API

Endpoint:

```text
GET /health
```

Expected output:

```json
{
  "status": "ok",
  "environment": "local"
}
```

### Step 4: Test SCN Agent

Endpoint:

```text
POST /api/v1/tasks/analyze-text
```

Query:

```text
Analyze this GST show cause notice and draft a reply
```

Text:

```text
Show Cause Notice under section 73 of the CGST Act.
It is alleged that input tax credit of INR 250000 was wrongly availed due to mismatch between GSTR-2B and GSTR-3B for FY 2024-25.
The taxpayer is required to explain why tax, interest and penalty should not be recovered.
```

Expected result:

- Agent selected: `scn`
- Notice summary
- Section detected
- Amount detected
- Department allegation
- Draft reply
- RAG context
- Human review flag

### Step 5: Test Bank Statement Agent

Endpoint:

```text
POST /api/v1/tasks/analyze-text
```

Query:

```text
Analyze this bank statement
```

Text:

```text
2026-04-03 Cash Deposit 0 150000 400000
2026-04-07 Vendor Payment 85000 0 315000
2026-04-11 Interest Credit 0 3500 318500
2026-04-15 Loan EMI 45000 0 273500
2026-04-20 High Value Receipt 0 250000 523500
```

Expected result:

- Agent selected: `bank_statement`
- Total credits
- Total debits
- Cash transaction detection
- Interest transaction detection
- EMI detection
- High-value transaction detection

### Step 6: Test Financial Analysis Agent

Endpoint:

```text
POST /api/v1/tasks/analyze-text
```

Query:

```text
Analyze financial statement ratios and anomalies
```

Text:

```text
Current Assets 500000
Current Liabilities 250000
Inventory 100000
Total Debt 800000
Equity 300000
Revenue 1200000
Net Profit 180000
Total Assets 1000000
Total Liabilities 650000
```

Expected result:

- Agent selected: `financial`
- Current ratio
- Quick ratio
- Debt-equity ratio
- Profit margin
- ROA
- ROE
- Balance sheet conflict warning if applicable
- Anomaly indicators

## 5. Next Tasks for the Technical Team

Give the technical team these tasks in sequence.

### Priority 1: Make the POC Easier to Run

1. Add `Dockerfile`.
2. Add `docker-compose.yml`.
3. Add Makefile commands such as `make install`, `make test`, `make run`.
4. Add GitHub Actions for tests and linting.

### Priority 2: Improve OCR and Document Processing

1. Add Azure Document Intelligence or Google Document AI adapter.
2. Improve PDF table extraction.
3. Add bank-specific parsers for HDFC, ICICI, SBI, Axis, Kotak.
4. Add invoice extraction.
5. Add Form 16, AIS, and 26AS extraction.

### Priority 3: Upgrade RAG

1. Add Qdrant locally through Docker.
2. Add OpenAI embedding adapter.
3. Create ingestion scripts for PDFs and text files.
4. Create collections:
   - `income_tax`
   - `gst`
   - `companies_act`
   - `accounting_standards`
   - `case_laws`
   - `notifications`
   - `client_documents`
5. Add source citations to every legal response.

### Priority 4: Improve LLM-Based Drafting

1. Add richer prompt templates for SCN replies.
2. Add prompt templates for financial commentary.
3. Add reviewer-editable draft outputs.
4. Add version history for generated responses.
5. Add model/cost policy per workflow if needed.

### Priority 5: Add Frontend

1. Build React UI.
2. Add document upload screen.
3. Add result viewer.
4. Add RAG source viewer.
5. Add review queue.
6. Add export buttons for Excel, PDF, and DOCX.

### Priority 6: Add Production Controls

1. Add login and authentication.
2. Add client workspaces.
3. Add role-based access.
4. Add approval workflow.
5. Add audit trail.
6. Add encrypted document storage.

## 6. Explanation for the Business Team

Tell the business team:

"We have prepared a POC of an AI assistant for Chartered Accountant firms. It can process CA-related documents, route tasks to specialist agents, retrieve relevant tax/accounting knowledge, and use OpenAI to produce a human-readable analysis or draft response for CA review. It is not a final filing tool yet. It is a productivity and review assistant for CA teams."

## 7. Functionalities Prepared for Business Demonstration

### Functionality 1: SCN / Notice Processing

Input:

- GST notice
- Income tax notice
- Assessment-related text

Output:

- Notice summary
- Sections detected
- Amounts detected
- Department allegations
- Relevant legal context
- Draft professional reply
- Human review warning

Business value:

- Saves time in first-level notice review.
- Creates a structured draft for CA review.
- Reduces repetitive drafting effort.

### Functionality 2: Bank Statement Analysis

Input:

- Bank statement text or file

Output:

- Total credits
- Total debits
- Cash transaction detection
- Interest income detection
- Loan/EMI detection
- High-value transaction detection
- Excel output when file upload has transaction rows

Business value:

- Helps CA teams quickly review client bank statements.
- Flags items that may need reconciliation.
- Supports audit and tax preparation workflows.

### Functionality 3: Financial Statement Analysis

Input:

- Balance sheet and P&L figures

Output:

- Current ratio
- Quick ratio
- Debt-equity ratio
- Net profit margin
- ROA
- ROE
- Conflict checks
- Anomaly indicators

Business value:

- Speeds up preliminary financial review.
- Helps identify red flags before deeper audit work.

### Functionality 4: Draft ITR Helper

Input:

- Form 16, AIS, 26AS, salary, interest, capital gains, deduction-related text

Output:

- Draft salary value
- Draft interest value
- Draft capital gain value
- Draft 80C value
- Draft TDS value
- Missing document checklist

Business value:

- Demonstrates future ITR automation potential.
- Helps organize data before return preparation.

Important note:

This is not yet direct ITR filing. Filing must be added later with CA approval workflow.

## 8. How Business Team Can Demo the POC to Clients

### Step 1: Start the Backend

Ask the technical person to run:

```bash
uvicorn app.main:app --reload
```

### Step 2: Open Swagger UI

Open:

```text
http://127.0.0.1:8000/docs
```

### Step 3: Demo SCN Agent

Use endpoint:

```text
POST /api/v1/tasks/analyze-text
```

Use query:

```text
Analyze this GST show cause notice and draft a reply
```

Use text:

```text
Show Cause Notice under section 73 of the CGST Act.
It is alleged that input tax credit of INR 250000 was wrongly availed due to mismatch between GSTR-2B and GSTR-3B for FY 2024-25.
The taxpayer is required to explain why tax, interest and penalty should not be recovered.
```

Explain to client:

"The system understood this is a notice, selected the SCN Agent, extracted the allegation, identified the section, retrieved GST context, and generated a draft reply for CA review."

### Step 4: Demo Bank Statement Agent

Use query:

```text
Analyze this bank statement
```

Use text:

```text
2026-04-03 Cash Deposit 0 150000 400000
2026-04-07 Vendor Payment 85000 0 315000
2026-04-11 Interest Credit 0 3500 318500
2026-04-15 Loan EMI 45000 0 273500
2026-04-20 High Value Receipt 0 250000 523500
```

Explain to client:

"The system detected cash deposit, interest income, EMI transaction, and high-value receipt. In production, this can be connected to uploaded bank statements and Excel reports."

### Step 5: Demo Financial Analysis Agent

Use query:

```text
Analyze financial statement ratios and anomalies
```

Use text:

```text
Current Assets 500000
Current Liabilities 250000
Inventory 100000
Total Debt 800000
Equity 300000
Revenue 1200000
Net Profit 180000
Total Assets 1000000
Total Liabilities 650000
```

Explain to client:

"The system calculates financial ratios and flags review points. This can become a preliminary financial statement review assistant."

## 9. Client Positioning

Do not present this as a finished filing product.

Present it as:

"A working POC of an AI assistant for CA firms that reduces manual effort in document review, notice response drafting, bank statement analysis, and financial review."

Recommended client message:

"The system is currently in POC stage. It demonstrates the agentic workflow and intelligence layer. The production version will include stronger OCR, secure document storage, RAG with citations, client workspaces, user login, approval workflow, and export options."

## 10. What Is Already Prepared

Already available in the repo:

- FastAPI backend
- Agent orchestrator
- OCR agent
- Bank statement analysis agent
- SCN analysis agent
- Financial analysis agent
- Draft ITR helper
- Offline Multi-RAG retriever
- OpenAI final response layer
- Tenant-scoped RAG learning controls
- Seed knowledge files
- API documentation
- Setup documentation
- Roadmap
- Security and compliance notes
- Tests

## 11. What Is Not Yet Production Ready

Not yet complete:

- React frontend
- Login and user roles
- Real cloud OCR
- Qdrant vector database
- Workflow-specific prompt templates
- Full source citations
- Real legal knowledge ingestion
- Client workspace management
- Approval workflow
- Government portal integrations
- Production deployment

## 12. Suggested Meeting Flow

### Technical Team Meeting

1. Show repository README.
2. Open architecture document.
3. Run the API locally.
4. Test the three demo workflows.
5. Review code structure.
6. Assign technical tasks from section 5.

### Business Team Meeting

1. Explain the business problem.
2. Show current POC capabilities.
3. Demo SCN processing.
4. Demo bank statement analysis.
5. Demo financial analysis.
6. Explain limitations honestly.
7. Discuss client pilot use cases.

### Client POC Meeting

1. Present the problem statement.
2. Show that the system routes tasks to specialist agents.
3. Demo SCN draft generation.
4. Demo bank statement review.
5. Demo financial ratio analysis.
6. Emphasize CA review and compliance controls.
7. Discuss next production phase.

## 13. Immediate Next Action Plan

For the next development cycle, start with these five tasks:

1. Add Docker and docker-compose.
2. Add React upload and result UI.
3. Add Qdrant and OpenAI embeddings.
4. Add better OCR/document parsing.
5. Add export to Excel, PDF, and DOCX.

These five items will make the POC easier to demo and move it closer to a client pilot.
