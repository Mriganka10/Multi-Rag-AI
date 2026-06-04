# Project Brief

## Objective

Build a Python-based agentic AI platform for Chartered Accountant workflows. The system should process client documents, retrieve domain knowledge from multiple knowledge bases, produce structured analysis, and generate professional drafts for CA review.

## MVP Scope

The current proof of concept focuses on four core capabilities:

1. OCR and document extraction for PDFs, images, and text files.
2. Bank statement conversion and analysis with Excel export.
3. Show Cause Notice analysis with draft professional response.
4. Financial statement analysis with ratios, conflicts, and anomaly indicators.

A draft-only ITR helper is included as an early workflow placeholder. Actual filing, portal upload, and final tax positions must remain gated by human approval.

## Target Users

- Chartered Accountants
- Tax consultants
- Audit teams
- Accounting back-office teams
- Compliance review teams

## Success Criteria

- Upload or paste document content through the API.
- Automatically route the query to the correct specialist agent.
- Retrieve relevant legal/accounting context from the applicable knowledge base.
- Produce structured JSON output suitable for a UI or downstream workflow.
- Keep all high-risk outputs marked for CA review.

## Current Status

The repository contains a working FastAPI POC with deterministic local agents and an offline TF-IDF multi-RAG layer. It is designed so production services such as Qdrant, OpenAI embeddings, cloud OCR, and human approval workflows can be added without rewriting the entire application.
