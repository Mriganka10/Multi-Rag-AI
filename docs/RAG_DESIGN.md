# Multi-RAG Design

## Goal

The platform should retrieve the right professional context for each CA workflow. A GST notice should not search only income tax material. A financial statement review should prioritize accounting standards and audit indicators.

## Current POC Implementation

File: `app/rag/multi_rag.py`

The current retriever:

- Loads `.txt` files from `data/knowledge`.
- Treats each file as a collection.
- Builds a TF-IDF matrix locally.
- Returns ranked context snippets with collection, score, text, and source.

This lets the POC run without external infrastructure.

## Current Seed Collections

- `gst`
- `income_tax`
- `accounting_standards`

## Recommended Production Collections

- `income_tax`
- `gst`
- `companies_act`
- `accounting_standards`
- `auditing_standards`
- `case_laws`
- `circulars_notifications`
- `client_documents`
- `prior_responses`

## Retrieval Strategy

### Step 1: Route Query

The orchestrator identifies the task type:

- SCN processing
- Bank statement analysis
- Financial statement analysis
- ITR preparation
- General research

### Step 2: Select Collections

Examples:

- GST SCN -> `gst`, `case_laws`, `circulars_notifications`
- Income tax notice -> `income_tax`, `case_laws`, `circulars_notifications`
- Financial review -> `accounting_standards`, `auditing_standards`, `client_documents`
- ITR preparation -> `income_tax`, `client_documents`

### Step 3: Retrieve and Rank

Production retrieval should use:

- Embeddings
- Vector search
- Metadata filters
- Hybrid keyword search
- Reranking
- Source citations

### Step 4: Generate Grounded Output

LLM output should explicitly use retrieved context and preserve citations wherever legal or compliance claims are made.

## Qdrant Upgrade Plan

1. Create one Qdrant collection per knowledge type.
2. Chunk source documents by section, rule, circular, paragraph, or case-law headnote.
3. Generate embeddings for each chunk.
4. Store metadata:
   - `source_type`
   - `act`
   - `section`
   - `assessment_year`
   - `effective_date`
   - `jurisdiction`
   - `document_url`
   - `uploaded_by`
5. Query only relevant collections based on orchestrator decision.
6. Return sources in API response.

## Document Ingestion Pipeline

```text
Source PDF / DOC / HTML
        |
        v
Text Extraction
        |
        v
Chunking
        |
        v
Metadata Enrichment
        |
        v
Embedding Generation
        |
        v
Vector DB Upsert
```

## Quality Controls

- Keep source citations in every legal response.
- Track source date and applicability period.
- Separate law, case law, client documents, and generated drafts.
- Do not allow generated drafts to become authoritative knowledge unless reviewed.
- Version knowledge bases because tax law changes frequently.
