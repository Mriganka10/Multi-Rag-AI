from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import PlainTextResponse

from app.agents.orchestrator import AgentOrchestrator
from app.core.audit import AuditLogger, safe_tenant_id
from app.core.auth import AuthService, CurrentUser, OTPRequest, OTPVerifyRequest, is_reviewer
from app.core.config import settings
from app.core.storage import UploadStorage
from app.llm.service import LLMProviderError
from app.models.schemas import LearningOptions, TextAnalysisRequest

router = APIRouter()
orchestrator = AgentOrchestrator()
audit_logger = AuditLogger()
upload_storage = UploadStorage()
auth_service = AuthService()


@router.post("/auth/request-otp")
def request_otp(payload: OTPRequest) -> dict[str, object]:
    result = auth_service.request_otp(payload.email)
    audit_logger.log(
        event_type="auth_otp_requested",
        tenant_id=safe_tenant_id(payload.email),
        actor=payload.email,
        status="success",
        metadata={"email": payload.email},
    )
    return result


@router.post("/auth/verify-otp")
def verify_otp(payload: OTPVerifyRequest, response: Response) -> dict[str, object]:
    user, session_token = auth_service.verify_otp(payload.email, payload.otp)
    response.set_cookie(
        key=settings.auth_session_cookie_name,
        value=session_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=settings.auth_session_ttl_minutes * 60,
    )
    audit_logger.log(
        event_type="auth_login",
        tenant_id=user.tenant_id,
        actor=user.email,
        status="success",
        metadata={"role": user.role},
    )
    return _user_payload(user)


@router.get("/auth/me")
def auth_me(request: Request) -> dict[str, object]:
    return _user_payload(_current_user(request))


@router.post("/auth/logout")
def auth_logout(request: Request, response: Response) -> dict[str, str]:
    user = _current_user(request)
    auth_service.logout(request)
    response.delete_cookie(settings.auth_session_cookie_name)
    audit_logger.log(
        event_type="auth_logout",
        tenant_id=user.tenant_id,
        actor=user.email,
        status="success",
        metadata={},
    )
    return {"message": "Signed out"}


@router.post("/tasks/analyze-text", response_class=PlainTextResponse)
def analyze_text(payload: TextAnalysisRequest, request: Request) -> PlainTextResponse:
    current_user = _current_user(request)
    _enforce_learning_approval(payload.approve_learning, current_user)
    tenant_id = current_user.tenant_id
    try:
        result = orchestrator.analyze_text(
            query=payload.query,
            text=payload.text,
            learning_options=LearningOptions(
                tenant_id=tenant_id,
                learning_consent=payload.learning_consent,
                approve_learning=payload.approve_learning,
            ),
        )
    except LLMProviderError as exc:
        _log_analysis_event(
            tenant_id=tenant_id,
            actor=current_user.username,
            status="llm_error",
            metadata={"error": str(exc), "input_type": "text"},
        )
        return PlainTextResponse(f"LLM provider error: {exc}", status_code=502)
    _log_analysis_event(
        tenant_id=tenant_id,
        actor=current_user.username,
        status="success",
        metadata={
            "input_type": "text",
            "agent": result.agent.value,
            "llm": result.llm,
            "learning_approved": payload.approve_learning,
            "learning_consent": payload.learning_consent,
        },
    )
    return _client_response(result)


@router.post("/tasks/analyze-file", response_class=PlainTextResponse)
async def analyze_file(
    request: Request,
    query: str = Form(...),
    file: UploadFile = File(...),
    learning_consent: bool = Form(False),
    approve_learning: bool = Form(False),
) -> PlainTextResponse:
    current_user = _current_user(request)
    _enforce_learning_approval(approve_learning, current_user)
    safe_tenant = current_user.tenant_id
    upload_dir = settings.data_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "upload").suffix
    file_path = upload_dir / f"{uuid4().hex}{suffix}"
    file_path.write_bytes(await file.read())
    stored_upload = upload_storage.persist_upload(
        local_path=file_path,
        tenant_id=safe_tenant,
        original_filename=file.filename or file_path.name,
    )
    try:
        result = orchestrator.analyze_file(
            query=query,
            file_path=file_path,
            learning_options=LearningOptions(
                tenant_id=safe_tenant,
                learning_consent=learning_consent,
                approve_learning=approve_learning,
            ),
        )
    except LLMProviderError as exc:
        _log_analysis_event(
            tenant_id=safe_tenant,
            actor=current_user.username,
            status="llm_error",
            metadata={
                "error": str(exc),
                "input_type": "file",
                "filename": file.filename,
                "stored_upload": stored_upload,
            },
        )
        return PlainTextResponse(f"LLM provider error: {exc}", status_code=502)
    result.data["stored_upload"] = stored_upload
    _log_analysis_event(
        tenant_id=safe_tenant,
        actor=current_user.username,
        status="success",
        metadata={
            "input_type": "file",
            "filename": file.filename,
            "stored_upload": stored_upload,
            "agent": result.agent.value,
            "llm": result.llm,
            "learning_approved": approve_learning,
            "learning_consent": learning_consent,
        },
    )
    return _client_response(result)


@router.get("/rag/search")
def rag_search(query: str, request: Request, collections: str | None = None) -> dict[str, object]:
    _current_user(request)
    selected = [item.strip() for item in collections.split(",")] if collections else None
    return {"contexts": orchestrator.rag.retrieve(query=query, collections=selected)}


def _client_response(result) -> PlainTextResponse:
    response = PlainTextResponse(result.client_response)
    response.headers["X-Agent-Selected"] = str(result.agent)
    response.headers["X-LLM-Provider"] = str(result.llm.get("provider", "unknown"))
    response.headers["X-LLM-Model"] = str(result.llm.get("model", "unknown"))
    response.headers["X-LLM-Fallback"] = str(result.llm.get("used_fallback", False)).lower()
    return response


def _current_user(request: Request) -> CurrentUser:
    return auth_service.current_user(request)


def _user_payload(user: CurrentUser) -> dict[str, object]:
    return {
        "email": user.email,
        "role": user.role,
        "tenant_id": user.tenant_id,
        "authenticated": True,
    }


def _enforce_learning_approval(approve_learning: bool, current_user: CurrentUser) -> None:
    if approve_learning and not is_reviewer(current_user):
        raise HTTPException(
            status_code=403,
            detail="CA-approved learning requires an admin or reviewer role.",
        )


def _log_analysis_event(
    *,
    tenant_id: str,
    actor: str,
    status: str,
    metadata: dict[str, object],
) -> None:
    audit_logger.log(
        event_type="analysis_request",
        tenant_id=tenant_id,
        actor=actor,
        status=status,
        metadata=metadata,
    )
