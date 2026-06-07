from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import PlainTextResponse

from app.agents.orchestrator import AgentOrchestrator
from app.core.config import settings
from app.models.schemas import LearningOptions, TextAnalysisRequest

router = APIRouter()
orchestrator = AgentOrchestrator()


@router.post("/tasks/analyze-text", response_class=PlainTextResponse)
def analyze_text(payload: TextAnalysisRequest) -> PlainTextResponse:
    result = orchestrator.analyze_text(
        query=payload.query,
        text=payload.text,
        learning_options=LearningOptions(
            tenant_id=payload.tenant_id,
            learning_consent=payload.learning_consent,
            approve_learning=payload.approve_learning,
        ),
    )
    return PlainTextResponse(result.client_response)


@router.post("/tasks/analyze-file", response_class=PlainTextResponse)
async def analyze_file(
    query: str = Form(...),
    file: UploadFile = File(...),
    tenant_id: str = Form("default"),
    learning_consent: bool = Form(False),
    approve_learning: bool = Form(False),
) -> PlainTextResponse:
    upload_dir = settings.data_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "upload").suffix
    file_path = upload_dir / f"{uuid4().hex}{suffix}"
    file_path.write_bytes(await file.read())
    result = orchestrator.analyze_file(
        query=query,
        file_path=file_path,
        learning_options=LearningOptions(
            tenant_id=tenant_id,
            learning_consent=learning_consent,
            approve_learning=approve_learning,
        ),
    )
    return PlainTextResponse(result.client_response)


@router.get("/rag/search")
def rag_search(query: str, collections: str | None = None) -> dict[str, object]:
    selected = [item.strip() for item in collections.split(",")] if collections else None
    return {"contexts": orchestrator.rag.retrieve(query=query, collections=selected)}
