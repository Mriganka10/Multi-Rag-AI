# Setup Guide

## Prerequisites

- Python 3.11 or newer
- Git
- Tesseract OCR installed locally if image OCR is required

For macOS, Tesseract can usually be installed with:

```bash
brew install tesseract
```

## Clone Repository

```bash
git clone https://github.com/Mriganka10/Multi-Rag-AI.git
cd Multi-Rag-AI
```

## Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

## Install Dependencies

For normal development:

```bash
pip install -e ".[dev]"
```

For optional cloud integrations:

```bash
pip install -e ".[dev,cloud]"
```

## Configure Environment

```bash
cp .env.example .env
```

Important environment variables:

```text
APP_NAME="CA Agentic AI RAG"
ENVIRONMENT=local
DATA_DIR=data
OPENAI_API_KEY=
QDRANT_URL=
QDRANT_API_KEY=
OCR_PROVIDER=local
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4.1-mini
RAG_LEARNING_ENABLED=true
RAG_LEARNING_DEFAULT_CONSENT=false
```

The analysis APIs are configured for OpenAI by default. During local development, if no
`OPENAI_API_KEY` is provided, the service falls back to the offline plain-text response builder.
For production demos, provide an OpenAI API key.

Do not commit `.env`. Keep the API key only on the local machine or in a production secret manager.

## OpenAI LLM Mode

Use OpenAI for client-readable responses:

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4.1-mini
```

Install cloud dependencies:

```bash
python -m pip install -e ".[dev,cloud]"
```

When OpenAI mode is active, successful responses include:

```text
X-LLM-Provider: openai
X-LLM-Model: gpt-4.1-mini
X-LLM-Fallback: false
```

If the app cannot call OpenAI, the endpoint returns `502 LLM provider error`.

## Local Offline Mode

For local testing without an API key:

```text
LLM_PROVIDER=offline
```

## RAG Learning Controls

The API supports controlled RAG learning:

```text
RAG_LEARNING_ENABLED=true
RAG_LEARNING_DEFAULT_CONSENT=false
```

Keep default consent as `false` in production. Send request-level consent and approval only when the client or engagement allows it.

## Run API Server

```bash
uvicorn app.main:app --reload
```

Open the API docs:

```text
http://127.0.0.1:8000/docs
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok","environment":"local"}
```

## Run Tests

```bash
pytest -q
```

## Run Linter

```bash
ruff check .
```

## Common Issues

### `pytesseract` import works but image OCR fails

Install the Tesseract system binary. The Python package is only a wrapper.

### PDF text extraction returns empty text

Some PDFs are scanned images. Use image OCR or cloud OCR such as Azure Document Intelligence or Google Document AI.

### RAG returns low-quality context

The seed knowledge files are intentionally small. Add more domain material under `data/knowledge` or replace the retriever with Qdrant embeddings.
