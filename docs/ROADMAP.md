# Roadmap

## Phase 1: POC Foundation

Status: Complete in current repository.

Deliverables:

- FastAPI backend.
- Agent orchestrator.
- OCR and transaction extraction.
- Bank statement analysis.
- SCN analysis and draft reply.
- Financial statement analysis.
- Draft-only ITR helper.
- Offline Multi-RAG retriever.
- OpenAI final response layer for client-readable reports.
- Tenant-scoped RAG learning with pending and approved learned notes.
- Seed knowledge files.
- Tests and linter setup.

## Phase 2: Better Document Intelligence

Goals:

- Add Azure Document Intelligence or Google Document AI.
- Add bank-specific statement parsers.
- Support table extraction from PDFs.
- Improve Excel output formatting.
- Add document classification.

Deliverables:

- Provider interface for OCR engines.
- Structured extraction for invoices, statements, notices, Form 16, AIS, and 26AS.
- Confidence scores and extraction warnings.

## Phase 3: Production Multi-RAG

Goals:

- Replace TF-IDF with Qdrant.
- Add OpenAI embeddings.
- Add source citations.
- Add metadata filtering.
- Add ingestion scripts for law, circulars, standards, and case law.

Deliverables:

- Qdrant collections.
- Embedding ingestion pipeline.
- RAG search service.
- Retrieval evaluation set.

## Phase 4: LLM Drafting and Review Workflow

Status: Partially complete.

Current branch includes:

- OpenAI provider integration through `LLM_PROVIDER=openai`.
- Shared configurable response model through `OPENAI_MODEL`, currently `gpt-5.5`.
- Human-readable `text/plain` analysis responses.
- Provider/model response headers.
- Controlled RAG learning with consent and approval gates.

Goals:

- Add richer prompt templates by workflow.
- Add reviewer approval status.
- Add versioned draft history.

Deliverables:

- SCN draft generator with citations.
- Financial commentary generator.
- Review and approval API.
- Export to DOCX or PDF.

## Phase 5: ITR Preparation Workflow

Goals:

- Extract data from Form 16, AIS, 26AS, bank statements, and capital gains reports.
- Reconcile extracted data.
- Prepare draft ITR JSON.

Deliverables:

- ITR data model.
- Reconciliation engine.
- Tax computation helper.
- Draft JSON export.

Boundary:

Actual filing must remain approval-gated.

## Phase 6: Frontend Application

Goals:

- Build a simple React UI for CA teams.
- Support upload, task tracking, result review, and exports.

Views:

- Dashboard
- Upload center
- Agent result viewer
- RAG source viewer
- Review queue
- Client workspace

## Phase 7: Enterprise Controls

Goals:

- Authentication and authorization.
- Client and engagement management.
- Audit trail.
- Encrypted storage.
- Background jobs.
- Monitoring and observability.

## Suggested Immediate Next Tasks

1. Add Dockerfile and docker-compose.
2. Add Qdrant local service.
3. Add OpenAI embedding adapter.
4. Add document ingestion command.
5. Add richer sample documents.
6. Add frontend upload UI.
7. Add authentication and tenant workspace APIs.
