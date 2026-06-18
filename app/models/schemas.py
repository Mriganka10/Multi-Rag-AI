from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentName(StrEnum):
    OCR = "ocr"
    BANK = "bank_statement"
    SCN = "scn"
    FINANCIAL = "financial"
    ITR = "itr"
    GENERAL = "general"


class TextAnalysisRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=3,
        examples=["Analyze this bank statement"],
    )
    text: str | list[str] = Field(
        ...,
        min_length=1,
        examples=[
            [
                "2026-04-03 Cash Deposit 0 150000 400000",
                "2026-04-07 Vendor Payment 85000 0 315000",
                "2026-04-11 Interest Credit 0 3500 318500",
            ]
        ],
        description="Document text as one string, or as a list of lines for easier JSON entry.",
    )
    tenant_id: str = Field(
        default="default",
        min_length=1,
        max_length=64,
        description="Client or engagement identifier used to scope learned RAG notes.",
    )
    learning_consent: bool = Field(
        default=False,
        description="Set true only when the client/engagement has opted into RAG learning.",
    )
    approve_learning: bool = Field(
        default=False,
        description="Set true only after CA approval. Approved notes become retrievable RAG context.",
    )
    output_formats: list[Literal["pdf", "docx", "xlsx"]] = Field(
        default_factory=list,
        description=(
            "Optional response document formats. Formats mentioned in the query are also detected "
            "automatically."
        ),
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "query": "Analyze this bank statement",
                    "text": [
                        "2026-04-03 Cash Deposit 0 150000 400000",
                        "2026-04-07 Vendor Payment 85000 0 315000",
                        "2026-04-11 Interest Credit 0 3500 318500",
                        "2026-04-15 Loan EMI 45000 0 273500",
                        "2026-04-20 High Value Receipt 0 250000 523500",
                    ],
                    "tenant_id": "demo-client",
                    "learning_consent": True,
                    "approve_learning": False,
                },
                {
                    "query": "Analyze this GST show cause notice and draft a reply",
                    "text": (
                        "Show Cause Notice under section 73 of the CGST Act.\n"
                        "It is alleged that input tax credit of INR 250000 was wrongly availed."
                    ),
                },
            ]
        }
    )

    @field_validator("text", mode="before")
    @classmethod
    def normalize_text(cls, value: str | list[str]) -> str:
        if isinstance(value, list):
            return "\n".join(str(line) for line in value)
        return value

    @field_validator("tenant_id")
    @classmethod
    def normalize_tenant_id(cls, value: str) -> str:
        normalized = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in value)
        return normalized.strip("-") or "default"


class LearningOptions(BaseModel):
    tenant_id: str = "default"
    learning_consent: bool = False
    approve_learning: bool = False

    @field_validator("tenant_id")
    @classmethod
    def normalize_tenant_id(cls, value: str) -> str:
        normalized = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in value)
        return normalized.strip("-") or "default"


class AgentDecision(BaseModel):
    agent: AgentName
    reason: str


class RetrievedContext(BaseModel):
    collection: str
    score: float
    text: str
    source: str


class TaskResult(BaseModel):
    agent: AgentName
    summary: str
    client_response: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    contexts: list[RetrievedContext] = Field(default_factory=list)
    artifacts: dict[str, Path | str] = Field(default_factory=dict)
    llm: dict[str, Any] = Field(default_factory=dict)
    learned_context_path: str | None = None
    requires_human_review: bool = True
