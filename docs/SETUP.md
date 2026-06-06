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
LLM_PROVIDER=offline
```

The POC works without OpenAI or Qdrant keys because the initial retriever is offline.

## Optional LLM Mode

The API runs in offline response mode by default:

```text
LLM_PROVIDER=offline
```

To use OpenAI for client-readable responses:

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-5.4-mini
```

Install cloud dependencies when using OpenAI mode:

```bash
python -m pip install -e ".[dev,cloud]"
```

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
