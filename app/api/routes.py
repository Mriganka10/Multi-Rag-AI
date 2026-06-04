from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, UploadFile

from app.agents.orchestrator import AgentOrchestrator
from app.core.config import settings
from app.models.schemas import TaskResult, TextAnalysisRequest

router = APIRouter()
orchestrator = AgentOrchestrator()


@router.post("/tasks/analyze-text", response_model=TaskResult)
def analyze_text(payload: TextAnalysisRequest) -> TaskResult:
    return orchestrator.analyze_text(query=payload.query, text=payload.text)


@router.post("/tasks/analyze-file", response_model=TaskResult)
async def analyze_file(query: str = Form(...), file: UploadFile = File(...)) -> TaskResult:
    upload_dir = settings.data_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "upload").suffix
    file_path = upload_dir / f"{uuid4().hex}{suffix}"
    file_path.write_bytes(await file.read())
    return orchestrator.analyze_file(query=query, file_path=file_path)


@router.get("/rag/search")
def rag_search(query: str, collections: str | None = None) -> dict[str, object]:
    selected = [item.strip() for item in collections.split(",")] if collections else None
    return {"contexts": orchestrator.rag.retrieve(query=query, collections=selected)}

