import re

from app.models.schemas import AgentName, RetrievedContext, TaskResult
from app.rag.multi_rag import MultiRAG


class SCNAgent:
    def __init__(self, rag: MultiRAG) -> None:
        self.rag = rag

    def run(self, query: str, text: str) -> TaskResult:
        contexts = self.rag.retrieve(
            f"{query}\n{text}",
            collections=["gst", "income_tax", "case_laws", "notifications"],
            top_k=3,
        )
        sections = sorted(set(re.findall(r"section\s+\d+[A-Z]*", text, flags=re.IGNORECASE)))
        amount_matches = re.findall(r"(?:INR|Rs\.?|₹)\s?[\d,]+(?:\.\d+)?", text, flags=re.IGNORECASE)
        allegations = self._extract_allegations(text)
        draft_reply = self._draft_reply(text, contexts, sections, allegations)

        summary = "SCN reviewed and draft response prepared for CA review."
        return TaskResult(
            agent=AgentName.SCN,
            summary=summary,
            contexts=contexts,
            data={
                "notice_summary": self._summarize_notice(text),
                "sections_detected": sections,
                "amounts_detected": amount_matches,
                "department_allegations": allegations,
                "draft_reply": draft_reply,
                "review_notes": [
                    "Validate facts against returns, ledgers, challans, and portal data.",
                    "Confirm limitation, jurisdiction, and hearing dates before submission.",
                    "Do not file this response without CA approval.",
                ],
            },
            requires_human_review=True,
        )

    def _extract_allegations(self, text: str) -> list[str]:
        allegations = []
        for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
            lowered = sentence.lower()
            if any(keyword in lowered for keyword in ["alleged", "mismatch", "wrongly", "recover"]):
                allegations.append(sentence.strip())
        return allegations or ["No explicit allegation sentence was detected."]

    def _summarize_notice(self, text: str) -> str:
        clean = " ".join(text.split())
        return clean[:500] + ("..." if len(clean) > 500 else "")

    def _draft_reply(
        self,
        text: str,
        contexts: list[RetrievedContext],
        sections: list[str],
        allegations: list[str],
    ) -> str:
        legal_context = "\n".join(f"- {context.text}" for context in contexts)
        sections_text = ", ".join(sections) if sections else "the provisions cited in the notice"
        allegations_text = "\n".join(f"{index}. {item}" for index, item in enumerate(allegations, start=1))
        return (
            "Subject: Reply to Show Cause Notice\n\n"
            "Respected Sir/Madam,\n\n"
            f"This is with reference to the notice issued under {sections_text}. "
            "The taxpayer respectfully submits this preliminary response based on available records.\n\n"
            "Department Allegations:\n"
            f"{allegations_text}\n\n"
            "Taxpayer Submission:\n"
            "1. The taxpayer denies any intentional non-compliance and requests that the matter be "
            "examined in light of returns, reconciliations, invoices, e-way bills, payment records, "
            "and books of account.\n"
            "2. Any mismatch should be treated as reconciliatory in nature unless supported by "
            "specific adverse evidence.\n"
            "3. Interest and penalty, if any, should be considered only after final determination "
            "of tax liability and after granting reasonable opportunity of being heard.\n\n"
            "Relevant Context Retrieved:\n"
            f"{legal_context or '- No matching knowledge context was retrieved.'}\n\n"
            "Prayer:\n"
            "The taxpayer requests that the proposed demand be dropped, or alternatively that a "
            "personal hearing be granted before passing any adverse order.\n\n"
            "This draft is generated for professional review and should be finalized by the CA."
        )

