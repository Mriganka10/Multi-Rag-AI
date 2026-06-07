from dataclasses import dataclass

from app.core.config import settings
from app.models.schemas import RetrievedContext, TaskResult


@dataclass(frozen=True)
class LLMGeneration:
    content: str
    provider: str
    model: str
    used_fallback: bool = False


class LLMService:
    def generate_client_response(
        self,
        *,
        query: str,
        extracted_text: str,
        result: TaskResult,
        contexts: list[RetrievedContext],
    ) -> LLMGeneration:
        if settings.llm_provider.lower() == "openai":
            try:
                return self._generate_with_openai(
                    query=query,
                    extracted_text=extracted_text,
                    result=result,
                    contexts=contexts,
                )
            except Exception:
                fallback = self._generate_offline(result=result, contexts=contexts)
                return LLMGeneration(
                    content=fallback.content,
                    provider="offline",
                    model="deterministic-template",
                    used_fallback=True,
                )
        return self._generate_offline(result=result, contexts=contexts)

    def _generate_with_openai(
        self,
        *,
        query: str,
        extracted_text: str,
        result: TaskResult,
        contexts: list[RetrievedContext],
    ) -> LLMGeneration:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install cloud dependencies with: pip install -e '.[dev,cloud]'") from exc

        client = OpenAI(api_key=settings.openai_api_key)
        response = client.responses.create(
            model=settings.openai_model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert AI assistant for Chartered Accountants. "
                        "Give clear, professional, client-readable analysis in plain text. "
                        "Use concise headings, spacing, and bullets where useful. "
                        "Never return JSON, raw dictionaries, or developer payloads to the client. "
                        "Do not claim that a tax filing, notice response, or legal position is final. "
                        "Mention that CA review is required where relevant."
                    ),
                },
                {
                    "role": "user",
                    "content": self._build_prompt(
                        query=query,
                        extracted_text=extracted_text,
                        result=result,
                        contexts=contexts,
                    ),
                },
            ],
        )
        return LLMGeneration(
            content=response.output_text,
            provider="openai",
            model=settings.openai_model,
        )

    def _build_prompt(
        self,
        *,
        query: str,
        extracted_text: str,
        result: TaskResult,
        contexts: list[RetrievedContext],
    ) -> str:
        context_text = "\n\n".join(
            f"[{context.collection} | score={context.score}]\n{context.text}" for context in contexts
        )
        return (
            f"User query:\n{query}\n\n"
            f"Selected agent:\n{result.agent}\n\n"
            f"Structured agent result:\n{result.model_dump_json(indent=2)}\n\n"
            f"Retrieved RAG context:\n{context_text or 'No retrieved context.'}\n\n"
            f"Extracted source text excerpt:\n{extracted_text[:3000]}\n\n"
            "Write a polished client-facing response with clear spacing and indentation. "
            "Include: summary, key observations, recommended next steps, and review caveats. "
            "Return plain human-readable text only. Do not return JSON."
        )

    def _generate_offline(
        self,
        *,
        result: TaskResult,
        contexts: list[RetrievedContext],
    ) -> LLMGeneration:
        observations = result.data.get("observations") or result.data.get("commentary") or []
        if isinstance(observations, str):
            observations = [observations]

        lines = [
            "Analysis Report",
            "",
            f"Agent Used: {result.agent.value}",
            "",
            result.summary,
        ]

        if observations:
            lines.append("")
            lines.append("Key Observations")
            lines.extend(f"- {item}" for item in observations)

        if result.agent.value == "scn" and result.data.get("draft_reply"):
            lines.append("")
            lines.append("Draft Response Prepared")
            lines.append(result.data["draft_reply"])

        if result.agent.value == "bank_statement":
            lines.append("")
            lines.append(
                "The statement has been reviewed for credit/debit movement, cash activity, "
                "interest, EMI/loan entries, and high-value transactions."
            )

        if result.agent.value == "financial":
            lines.append("")
            lines.append("Financial ratios and anomaly indicators have been prepared for review.")

        if contexts:
            lines.append("")
            lines.append("Relevant knowledge context was retrieved and attached in the API response.")

        if result.requires_human_review:
            lines.append("")
            lines.append("Review Caveat")
            lines.append("Please review this output with a qualified CA before taking action.")

        return LLMGeneration(
            content="\n".join(lines),
            provider="offline",
            model="deterministic-template",
        )
