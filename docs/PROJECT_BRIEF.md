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
- Produce client-readable plain text responses using the configured OpenAI model.
- Preserve structured internal analysis for routing, RAG, artifacts, audit, and future UI workflows.
- Keep all high-risk outputs marked for CA review.

## Current Status

The repository contains a working FastAPI POC with deterministic local agents, an offline TF-IDF multi-RAG layer, and an OpenAI final response layer. Specialist agents perform the domain analysis first; OpenAI then converts the internal result and RAG context into a human-readable client response.

The current OpenAI model is configured through `OPENAI_MODEL` and defaults to `gpt-4.1-mini`. The model is shared across all agents for final response generation.
