from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class AgentName(StrEnum):
    OCR = "ocr"
    BANK = "bank_statement"
    SCN = "scn"
    FINANCIAL = "financial"
    ITR = "itr"
    GENERAL = "general"


class TextAnalysisRequest(BaseModel):
    query: str = Field(..., min_length=3)
    text: str = Field(..., min_length=1)


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
    data: dict[str, Any] = Field(default_factory=dict)
    contexts: list[RetrievedContext] = Field(default_factory=list)
    artifacts: dict[str, Path | str] = Field(default_factory=dict)
    requires_human_review: bool = True

