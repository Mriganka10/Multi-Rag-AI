from datetime import UTC, datetime
from pathlib import Path

from app.models.schemas import TaskResult


class RAGLearningStore:
    def __init__(self, knowledge_dir: Path) -> None:
        self.learned_dir = knowledge_dir / "learned"

    def save(
        self,
        *,
        query: str,
        result: TaskResult,
        client_response: str,
    ) -> Path:
        self.learned_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        path = self.learned_dir / f"{result.agent.value}_{timestamp}.txt"
        content = (
            f"Agent: {result.agent.value}\n"
            f"Query: {query}\n"
            f"Summary: {result.summary}\n\n"
            f"Client Response:\n{client_response}\n"
        )
        path.write_text(content, encoding="utf-8")
        return path
