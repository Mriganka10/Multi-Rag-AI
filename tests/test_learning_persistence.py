import sys
from types import SimpleNamespace

from app.models.schemas import AgentName, TaskResult
from app.rag.learning import RAGLearningStore


def _result() -> TaskResult:
    return TaskResult(
        agent=AgentName.SCN,
        summary="SCN reviewed for CA approval.",
        client_response="Client-ready response.",
    )


def test_pending_learning_uses_tenant_scoped_s3_path(tmp_path, monkeypatch) -> None:
    from app.core.config import settings

    uploads: list[dict[str, object]] = []

    class FakeS3Client:
        def upload_file(self, **kwargs) -> None:
            uploads.append(kwargs)

    monkeypatch.setattr(settings, "storage_provider", "s3")
    monkeypatch.setattr(settings, "s3_bucket", "learning-bucket")
    monkeypatch.setattr(settings, "s3_prefix", "ca-agentic-ai")
    monkeypatch.setattr(settings, "database_url", None)
    monkeypatch.setattr(settings, "qdrant_url", None)
    monkeypatch.setitem(
        sys.modules,
        "boto3",
        SimpleNamespace(client=lambda *args, **kwargs: FakeS3Client()),
    )

    record = RAGLearningStore(tmp_path).save(
        query="Analyze this notice",
        result=_result(),
        client_response="Draft response for review.",
        tenant_id="client@example.com",
        approved=False,
    )

    assert record.status == "pending"
    assert record.indexing_status == "not_applicable"
    assert record.location.startswith(
        "s3://learning-bucket/ca-agentic-ai/tenants/client-example-com/rag/pending/"
    )
    assert uploads[0]["Key"].endswith(f"/rag/pending/{record.learning_id}.txt")
    assert uploads[0]["ExtraArgs"]["ServerSideEncryption"] == "AES256"


def test_approved_learning_records_qdrant_index_details(tmp_path, monkeypatch) -> None:
    from app.core.config import settings

    registered = []
    store = RAGLearningStore(tmp_path)

    monkeypatch.setattr(settings, "storage_provider", "local")
    monkeypatch.setattr(settings, "database_url", None)
    monkeypatch.setattr(settings, "qdrant_url", "https://qdrant.example")
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr(
        store,
        "_index_approved",
        lambda **kwargs: ("ca_learned_client-example-com", kwargs["learning_id"]),
    )
    monkeypatch.setattr(
        store,
        "_register",
        lambda **kwargs: registered.append(kwargs),
    )

    record = store.save(
        query="Analyze this notice",
        result=_result(),
        client_response="Approved response.",
        tenant_id="client@example.com",
        approved=True,
        approved_by="reviewer@example.com",
    )

    assert record.status == "approved"
    assert record.indexing_status == "indexed"
    assert record.qdrant_collection == "ca_learned_client-example-com"
    assert record.qdrant_point_id == record.learning_id
    assert registered[0]["approved_by"] == "reviewer@example.com"


def test_approved_learning_remains_persisted_when_qdrant_is_not_configured(
    tmp_path,
    monkeypatch,
) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "storage_provider", "local")
    monkeypatch.setattr(settings, "database_url", None)
    monkeypatch.setattr(settings, "qdrant_url", None)
    monkeypatch.setattr(settings, "openai_api_key", None)

    record = RAGLearningStore(tmp_path).save(
        query="Analyze this notice",
        result=_result(),
        client_response="Approved response.",
        tenant_id="client@example.com",
        approved=True,
    )

    assert record.status == "approved"
    assert record.indexing_status == "not_configured"
    assert record.location.endswith(f"/approved/{record.learning_id}.txt")


def test_qdrant_retrieval_uses_tenant_collection_and_query_points(
    tmp_path,
    monkeypatch,
) -> None:
    from app.core.config import settings
    from app.rag.multi_rag import MultiRAG

    calls = {}

    class FakeEmbeddings:
        def create(self, **kwargs):
            return SimpleNamespace(data=[SimpleNamespace(embedding=[0.1, 0.2])])

    class FakeOpenAI:
        def __init__(self, **kwargs) -> None:
            self.embeddings = FakeEmbeddings()

    class FakeQdrantClient:
        def __init__(self, **kwargs) -> None:
            calls["client"] = kwargs

        def query_points(self, **kwargs):
            calls["query"] = kwargs
            return SimpleNamespace(
                points=[
                    SimpleNamespace(
                        score=0.92,
                        payload={
                            "text": "Approved tenant-specific learning.",
                            "source": "s3://learning/approved.txt",
                        },
                    )
                ]
            )

    monkeypatch.setattr(settings, "rag_provider", "qdrant")
    monkeypatch.setattr(settings, "qdrant_url", "https://qdrant.example")
    monkeypatch.setattr(settings, "qdrant_api_key", "qdrant-key")
    monkeypatch.setattr(settings, "openai_api_key", "openai-key")
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))
    monkeypatch.setitem(
        sys.modules,
        "qdrant_client",
        SimpleNamespace(QdrantClient=FakeQdrantClient),
    )

    contexts = MultiRAG(tmp_path).retrieve(
        query="tenant-specific question",
        collections=["learned_client-example-com"],
        top_k=3,
    )

    assert calls["query"]["collection_name"] == "ca_learned_client-example-com"
    assert calls["query"]["query"] == [0.1, 0.2]
    assert contexts[0].text == "Approved tenant-specific learning."
