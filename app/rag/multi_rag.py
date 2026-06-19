from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import settings
from app.models.schemas import RetrievedContext
from app.rag.learning import qdrant_collection_name


@dataclass(frozen=True)
class KnowledgeDocument:
    collection: str
    source: str
    text: str


class MultiRAG:
    """Offline multi-collection retriever.

    This class intentionally mirrors the interface expected from a future Qdrant
    implementation. The POC remains runnable without API keys or services.
    """

    def __init__(self, knowledge_dir: Path) -> None:
        self.knowledge_dir = knowledge_dir
        self.documents: list[KnowledgeDocument] = []
        self._vectorizer = TfidfVectorizer(stop_words="english")
        self._matrix = None
        self.refresh()

    def refresh(self) -> None:
        self.documents = self._load_documents()
        self._vectorizer = TfidfVectorizer(stop_words="english")
        self._matrix = None
        if self.documents:
            self._matrix = self._vectorizer.fit_transform([doc.text for doc in self.documents])

    def retrieve(
        self,
        query: str,
        collections: list[str] | None = None,
        top_k: int = 4,
    ) -> list[RetrievedContext]:
        if settings.rag_provider.lower() == "qdrant":
            qdrant_contexts = self._retrieve_from_qdrant(query, collections, top_k)
            if qdrant_contexts:
                return qdrant_contexts

        if not self.documents or self._matrix is None:
            return []

        allowed = set(collections or [])
        candidate_indexes = [
            index
            for index, doc in enumerate(self.documents)
            if not allowed or doc.collection in allowed
        ]
        if not candidate_indexes:
            return []

        query_vector = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vector, self._matrix[candidate_indexes]).flatten()
        ranked = sorted(zip(candidate_indexes, scores, strict=True), key=lambda item: item[1], reverse=True)

        contexts: list[RetrievedContext] = []
        for index, score in ranked[:top_k]:
            doc = self.documents[index]
            contexts.append(
                RetrievedContext(
                    collection=doc.collection,
                    score=round(float(score), 4),
                    text=doc.text,
                    source=doc.source,
                )
            )
        return contexts

    def _retrieve_from_qdrant(
        self,
        query: str,
        collections: list[str] | None,
        top_k: int,
    ) -> list[RetrievedContext]:
        if not settings.qdrant_url or not settings.openai_api_key:
            return []

        try:
            from openai import OpenAI
            from qdrant_client import QdrantClient
        except ImportError:
            return []

        openai_client = OpenAI(api_key=settings.openai_api_key)
        embedding = openai_client.embeddings.create(
            model=settings.openai_embedding_model,
            input=query,
        )
        query_vector = embedding.data[0].embedding
        qdrant_client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )

        contexts: list[RetrievedContext] = []
        collection_names = collections or [
            "income_tax",
            "gst",
            "accounting_standards",
            "case_laws",
            "notifications",
        ]
        for collection in collection_names:
            qdrant_collection = qdrant_collection_name(collection)
            try:
                response = qdrant_client.query_points(
                    collection_name=qdrant_collection,
                    query=query_vector,
                    limit=top_k,
                    with_payload=True,
                )
            except Exception:
                continue

            for hit in response.points:
                payload = hit.payload or {}
                text = str(payload.get("text", ""))
                if not text:
                    continue
                contexts.append(
                    RetrievedContext(
                        collection=collection,
                        score=round(float(hit.score), 4),
                        text=text,
                        source=str(payload.get("source", qdrant_collection)),
                    )
                )
        return sorted(contexts, key=lambda item: item.score, reverse=True)[:top_k]

    def _load_documents(self) -> list[KnowledgeDocument]:
        if not self.knowledge_dir.exists():
            return []

        documents: list[KnowledgeDocument] = []
        for file_path in sorted(self.knowledge_dir.rglob("*.txt")):
            if "learned" in file_path.parts and "approved" not in file_path.parts:
                continue
            text = file_path.read_text(encoding="utf-8").strip()
            if text:
                collection = self._collection_for(file_path)
                documents.append(
                    KnowledgeDocument(
                        collection=collection,
                        source=str(file_path),
                        text=text,
                    )
                )
        return documents

    def _collection_for(self, file_path: Path) -> str:
        relative_parts = file_path.relative_to(self.knowledge_dir).parts
        if relative_parts and relative_parts[0] == "learned" and len(relative_parts) >= 3:
            return f"learned_{relative_parts[1]}"
        if file_path.parent != self.knowledge_dir:
            return file_path.parent.name
        return file_path.stem
