FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY app ./app
COPY data/knowledge ./data/knowledge
COPY data/uploads/.gitkeep ./data/uploads/.gitkeep
COPY data/outputs/.gitkeep ./data/outputs/.gitkeep
COPY data/audit/.gitkeep ./data/audit/.gitkeep

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e ".[cloud]"

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
