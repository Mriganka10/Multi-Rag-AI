import json
from datetime import UTC, datetime
from pathlib import Path

from app.models.schemas import TaskResult


class RAGLearningStore:
    def __init__(self, knowledge_dir: Path) -> None:
        self.learned_dir = knowledge_dir / "learned"
        self.audit_path = knowledge_dir / "learning_audit.jsonl"

    def save(
        self,
        *,
        query: str,
        result: TaskResult,
        client_response: str,
        tenant_id: str,
        approved: bool,
    ) -> Path:
        safe_tenant_id = self._safe_tenant_id(tenant_id)
        status = "approved" if approved else "pending"
        target_dir = self.learned_dir / safe_tenant_id / status
        target_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        path = target_dir / f"{result.agent.value}_{timestamp}.txt"
        content = (
            f"Agent: {result.agent.value}\n"
            f"Tenant: {safe_tenant_id}\n"
            f"Status: {status}\n"
            f"Query: {query}\n"
            f"Summary: {result.summary}\n\n"
            f"Client Response:\n{client_response}\n"
        )
        path.write_text(content, encoding="utf-8")
        self._write_audit_event(
            tenant_id=safe_tenant_id,
            status=status,
            result=result,
            learned_path=path,
        )
        return path

    def _write_audit_event(
        self,
        *,
        tenant_id: str,
        status: str,
        result: TaskResult,
        learned_path: Path,
    ) -> None:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "tenant_id": tenant_id,
            "status": status,
            "agent": result.agent.value,
            "source": str(learned_path),
            "contains_source_document_text": False,
            "approval_required_for_retrieval": status != "approved",
        }
        with self.audit_path.open("a", encoding="utf-8") as audit_file:
            audit_file.write(json.dumps(event, sort_keys=True) + "\n")

    def _safe_tenant_id(self, tenant_id: str) -> str:
        normalized = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in tenant_id)
        return normalized.strip("-") or "default"
