import re

from app.models.schemas import AgentName, TaskResult


class ITRAgent:
    """Draft-only ITR preparation helper.

    Full filing is intentionally out of scope for the MVP. This agent extracts
    likely figures and returns a review checklist for the CA.
    """

    def run(self, query: str, text: str) -> TaskResult:
        fields = self._extract_fields(text)
        return TaskResult(
            agent=AgentName.ITR,
            summary="Draft ITR preparation data extracted for professional review.",
            data={
                "query": query,
                "draft_return_data": fields,
                "missing_documents": self._missing_documents(text),
                "review_required": [
                    "Reconcile AIS and Form 26AS before finalizing.",
                    "Validate deductions and exemptions against evidence.",
                    "Do not submit return without CA approval.",
                ],
            },
            requires_human_review=True,
        )

    def _extract_fields(self, text: str) -> dict[str, float]:
        mapping = {
            "salary": r"salary[:\s]+([\d,]+(?:\.\d+)?)",
            "interest": r"interest[:\s]+([\d,]+(?:\.\d+)?)",
            "capital_gain": r"capital\s+gain[:\s]+([\d,]+(?:\.\d+)?)",
            "deduction_80c": r"80c[:\s]+([\d,]+(?:\.\d+)?)",
            "tds": r"tds[:\s]+([\d,]+(?:\.\d+)?)",
        }
        fields = {}
        for key, pattern in mapping.items():
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                fields[key] = float(match.group(1).replace(",", ""))
        return fields

    def _missing_documents(self, text: str) -> list[str]:
        required = ["form 16", "ais", "26as", "bank statement"]
        lowered = text.lower()
        return [item for item in required if item not in lowered]

