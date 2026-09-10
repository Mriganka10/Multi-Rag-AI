# CA Agentic AI Multi-RAG POC

Python proof-of-concept for an agentic AI platform tailored for Chartered Accountants.

The MVP focuses on three high-value workflows:

1. OCR + Excel conversion for bank statements and accounting documents.
2. SCN analysis with notice summary, allegations, applicable areas, and draft reply.
3. Financial statement analysis with ratios, trends, and anomaly flags.

The design keeps ITR automation and production-grade government integrations behind explicit human review because tax filing and legal submissions must not be fully autonomous.

## Documentation

- [Owner Handoff Guide](docs/OWNER_HANDOFF_GUIDE.md)
- [Project Brief](docs/PROJECT_BRIEF.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Code Walkthrough](docs/CODE_WALKTHROUGH.md)
- [Setup Guide](docs/SETUP.md)
- [API Reference](docs/API.md)
- [Agent Workflows](docs/AGENTS.md)
- [Models and Agent Techniques](docs/MODELS_AND_AGENTS.md)
- [Multi-RAG Design](docs/RAG_DESIGN.md)
- [LLM Responses and RAG Learning](docs/LLM_AND_LEARNING.md)
- [Security and Compliance](docs/SECURITY_AND_COMPLIANCE.md)
- [AWS Deployment Guide](docs/AWS_DEPLOYMENT.md)
- [AWS Deployment Walkthrough](docs/AWS_DEPLOYMENT_WALKTHROUGH.md)
- [Roadmap](docs/ROADMAP.md)

## Architecture

```text
User / API
   |
FastAPI
   |
Agent Orchestrator
   |
   +-- OCR Agent
   +-- Bank Statement Agent
   +-- SCN Agent
   +-- Financial Analysis Agent
   +-- Multi-RAG Retriever
   |
OpenAI LLM Response Layer
```

Production keeps `https://ledgermind.co.in` and runs this container as an isolated ECS web service
behind CloudFront and the shared ALB. It has its own target group, task role, secrets, logical
PostgreSQL database/role, and S3 namespace; no application worker is currently required.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,cloud]"
cp .env.example .env
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/
```

The root URL opens the user-friendly assistant screen with a prompt box, file attachment, and readable response area. Developers can still use Swagger at:

```text
http://127.0.0.1:8000/docs
```

## Example API Calls

Analyze text:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tasks/analyze-text \
  -H "Content-Type: application/json" \
  -d '{"query":"Analyze this GST show cause notice","text":"Show Cause Notice under section 73..."}'
```

Upload a PDF/image:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tasks/analyze-file \
  -F "query=Convert this bank statement to Excel and analyze it" \
  -F "file=@examples/sample_bank_statement.txt"
```

## Knowledge Base

Seed documents live in `data/knowledge`. The current implementation uses an offline TF-IDF retriever so tests and demos work without external services. For production, replace `app/rag/multi_rag.py` with Qdrant/OpenAI embeddings while keeping the same interface.

The public analysis APIs return human-readable `text/plain` reports. Internally, the app still builds a structured `TaskResult`, retrieves RAG context, and sends that context to the configured OpenAI model for final response generation.

Suggested RAG collections:

- `income_tax`
- `gst`
- `companies_act`
- `accounting_standards`
- `case_laws`
- `notifications`

## Human Review Policy

The system can draft SCN replies, analysis reports, and ITR preparation data. It must not submit notices, file returns, or finalize tax positions without CA approval.

## Roadmap

- Phase 1: OCR, SCN, financial analysis POC.
- Phase 2: Qdrant-backed multi-RAG with source citations.
- Phase 3: LLM drafting with review workflows.
- Phase 4: ITR preparation data model and JSON export.
- Phase 5: Portal integrations gated by human approval.

See the full [Roadmap](docs/ROADMAP.md) for phased implementation details.
