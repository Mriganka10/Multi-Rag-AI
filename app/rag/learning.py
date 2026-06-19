import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.core.audit import safe_tenant_id
from app.core.config import settings
from app.core.storage import UploadStorage
from app.models.schemas import TaskResult


@dataclass(frozen=True)
class LearningRecord:
    learning_id: str
    tenant_id: str
    status: str
    location: str
    content_hash: str
    qdrant_collection: str | None
    qdrant_point_id: str | None
    indexing_status: str
    indexing_error: str | None = None


class RAGLearningStore:
    def __init__(self, knowledge_dir: Path) -> None:
        self.learned_dir = knowledge_dir / "learned"
        self.audit_path = knowledge_dir / "learning_audit.jsonl"
        self.storage = UploadStorage()

    def save(
        self,
        *,
        query: str,
        result: TaskResult,
        client_response: str,
        tenant_id: str,
        approved: bool,
        approved_by: str | None = None,
    ) -> LearningRecord:
        tenant = safe_tenant_id(tenant_id)
        status = "approved" if approved else "pending"
        learning_id = str(uuid4())
        target_dir = self.learned_dir / tenant / status
        target_dir.mkdir(parents=True, exist_ok=True)
        local_path = target_dir / f"{learning_id}.txt"
        content = self._content(
            query=query,
            result=result,
            client_response=client_response,
            tenant_id=tenant,
            status=status,
            learning_id=learning_id,
        )
        local_path.write_text(content, encoding="utf-8")
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        location = self.storage.persist_learning(
            local_path=local_path,
            tenant_id=tenant,
            learning_id=learning_id,
            status=status,
        )

        collection: str | None = None
        point_id: str | None = None
        indexing_status = "not_applicable"
        indexing_error: str | None = None
        if approved:
            indexing_status = "pending"
            if settings.qdrant_url and settings.openai_api_key:
                try:
                    collection, point_id = self._index_approved(
                        learning_id=learning_id,
                        tenant_id=tenant,
                        content=content,
                        source=location,
                        agent=result.agent.value,
                    )
                    indexing_status = "indexed"
                except Exception as exc:
                    indexing_status = "failed"
                    indexing_error = str(exc)[:1000]
            else:
                indexing_status = "not_configured"

        record = LearningRecord(
            learning_id=learning_id,
            tenant_id=tenant,
            status=status,
            location=location,
            content_hash=content_hash,
            qdrant_collection=collection,
            qdrant_point_id=point_id,
            indexing_status=indexing_status,
            indexing_error=indexing_error,
        )
        self._register(
            record=record,
            agent=result.agent.value,
            approved_by=approved_by,
        )
        if not settings.database_url:
            self._write_local_audit(
                record=record,
                agent=result.agent.value,
                approved_by=approved_by,
            )
        return record

    def _content(
        self,
        *,
        query: str,
        result: TaskResult,
        client_response: str,
        tenant_id: str,
        status: str,
        learning_id: str,
    ) -> str:
        return (
            f"Learning ID: {learning_id}\n"
            f"Agent: {result.agent.value}\n"
            f"Tenant: {tenant_id}\n"
            f"Status: {status}\n"
            f"Query: {query}\n"
            f"Summary: {result.summary}\n\n"
            f"Client Response:\n{client_response}\n"
        )

    def _index_approved(
        self,
        *,
        learning_id: str,
        tenant_id: str,
        content: str,
        source: str,
        agent: str,
    ) -> tuple[str, str]:
        from openai import OpenAI
        from qdrant_client import QdrantClient, models

        embedding = OpenAI(api_key=settings.openai_api_key).embeddings.create(
            model=settings.openai_embedding_model,
            input=content,
        )
        vector = embedding.data[0].embedding
        collection = qdrant_collection_name(f"learned_{tenant_id}")
        client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )
        if not client.collection_exists(collection):
            client.create_collection(
                collection_name=collection,
                vectors_config=models.VectorParams(
                    size=len(vector),
                    distance=models.Distance.COSINE,
                ),
            )
        client.upsert(
            collection_name=collection,
            points=[
                models.PointStruct(
                    id=learning_id,
                    vector=vector,
                    payload={
                        "text": content,
                        "source": source,
                        "tenant_id": tenant_id,
                        "status": "approved",
                        "agent": agent,
                        "learning_id": learning_id,
                    },
                )
            ],
            wait=True,
        )
        return collection, learning_id

    def _register(
        self,
        *,
        record: LearningRecord,
        agent: str,
        approved_by: str | None,
    ) -> None:
        if not settings.database_url:
            return
        self._ensure_table()
        import psycopg

        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into rag_learning_records (
                        learning_id, tenant_id, status, agent, storage_location,
                        content_hash, approved_by, qdrant_collection, qdrant_point_id,
                        indexing_status, indexing_error, created_at, approved_at
                    )
                    values (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, now(), %s
                    )
                    """,
                    (
                        record.learning_id,
                        record.tenant_id,
                        record.status,
                        agent,
                        record.location,
                        record.content_hash,
                        approved_by,
                        record.qdrant_collection,
                        record.qdrant_point_id,
                        record.indexing_status,
                        record.indexing_error,
                        datetime.now(UTC) if record.status == "approved" else None,
                    ),
                )
            conn.commit()

    def _write_local_audit(
        self,
        *,
        record: LearningRecord,
        agent: str,
        approved_by: str | None,
    ) -> None:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "learning_id": record.learning_id,
            "tenant_id": record.tenant_id,
            "status": record.status,
            "agent": agent,
            "storage_location": record.location,
            "approved_by": approved_by,
            "qdrant_collection": record.qdrant_collection,
            "qdrant_point_id": record.qdrant_point_id,
            "indexing_status": record.indexing_status,
            "indexing_error": record.indexing_error,
            "content_hash": record.content_hash,
        }
        with self.audit_path.open("a", encoding="utf-8") as audit_file:
            audit_file.write(json.dumps(event, sort_keys=True) + "\n")

    def _ensure_table(self) -> None:
        import psycopg

        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    create table if not exists rag_learning_records (
                        learning_id text primary key,
                        tenant_id text not null,
                        status text not null check (status in ('pending', 'approved')),
                        agent text not null,
                        storage_location text not null,
                        content_hash text not null,
                        approved_by text,
                        qdrant_collection text,
                        qdrant_point_id text,
                        indexing_status text not null,
                        indexing_error text,
                        created_at timestamptz not null,
                        approved_at timestamptz
                    )
                    """
                )
                cur.execute(
                    """
                    create index if not exists idx_rag_learning_tenant_status
                    on rag_learning_records (tenant_id, status, created_at desc)
                    """
                )
            conn.commit()


def qdrant_collection_name(collection: str) -> str:
    safe_collection = "".join(
        char if char.isalnum() or char in {"-", "_"} else "-"
        for char in collection
    )
    return f"{settings.qdrant_collection_prefix}_{safe_collection}"[:255]
