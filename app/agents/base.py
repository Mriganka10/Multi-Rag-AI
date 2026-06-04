from abc import ABC, abstractmethod

from app.models.schemas import TaskResult


class Agent(ABC):
    @abstractmethod
    def run(self, query: str, text: str) -> TaskResult:
        """Execute the agent against extracted text."""

