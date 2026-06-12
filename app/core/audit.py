import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import settings


class AuditLogger:
    def __init__(self) -> None:
        self.audit_path = settings.data_dir / "audit" / "events.jsonl"

    def log(
        self,
        *,
        event_type: str,
        tenant_id: str,
        actor: str,
        status: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not settings.audit_enabled:
            return

        event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event_type": event_type,
            "tenant_id": tenant_id,
            "actor": actor,
            "status": status,
            "metadata": metadata or {},
        }

        if settings.database_url:
            self._write_postgres(event)
            return

        self._write_jsonl(event)

    def _write_jsonl(self, event: dict[str, Any]) -> None:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8") as audit_file:
            audit_file.write(json.dumps(event, sort_keys=True) + "\n")

    def _write_postgres(self, event: dict[str, Any]) -> None:
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError(
                "DATABASE_URL is configured, but psycopg is not installed. "
                "Install cloud dependencies with pip install -e '.[cloud]'."
            ) from exc

        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    create table if not exists audit_events (
                        id bigserial primary key,
                        timestamp timestamptz not null,
                        event_type text not null,
                        tenant_id text not null,
                        actor text not null,
                        status text not null,
                        metadata jsonb not null
                    )
                    """
                )
                cur.execute(
                    """
                    insert into audit_events
                        (timestamp, event_type, tenant_id, actor, status, metadata)
                    values (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        event["timestamp"],
                        event["event_type"],
                        event["tenant_id"],
                        event["actor"],
                        event["status"],
                        json.dumps(event["metadata"]),
                    ),
                )
            conn.commit()


def safe_tenant_id(tenant_id: str) -> str:
    normalized = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in tenant_id)
    return normalized.strip("-") or "default"


def audit_log_path() -> Path:
    return settings.data_dir / "audit" / "events.jsonl"
