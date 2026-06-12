from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.auth import auth_challenge, authenticate_request
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Agentic multi-RAG POC for Chartered Accountant workflows.",
)

app.include_router(router, prefix="/api/v1")

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def web_app() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.head("/", include_in_schema=False)
def web_app_head() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.middleware("http")
async def basic_auth_middleware(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)

    user = authenticate_request(request)
    if user is None:
        return auth_challenge()

    request.state.current_user = user
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = exc.errors()
    has_json_decode_error = any(error.get("type") == "json_invalid" for error in errors)
    if has_json_decode_error:
        return JSONResponse(
            status_code=422,
            content={
                "detail": errors,
                "message": (
                    "Invalid JSON body. Multiline text must either use escaped newline "
                    "characters (\n) inside one string, or be sent as a JSON array of lines."
                ),
                "valid_example": {
                    "query": "Analyze this bank statement",
                    "text": [
                        "2026-04-03 Cash Deposit 0 150000 400000",
                        "2026-04-07 Vendor Payment 85000 0 315000",
                    ],
                },
                "path": str(request.url.path),
            },
        )
    return JSONResponse(status_code=422, content={"detail": errors})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}
