import pandas as pd

from app.agents.ocr_agent import OCRAgent
from app.models.schemas import AgentName, TaskResult


class BankStatementAgent:
    def __init__(self) -> None:
        self.ocr = OCRAgent()

    def run(self, query: str, text: str) -> TaskResult:
        rows = self.ocr.parse_transactions(text)
        if not rows:
            return TaskResult(
                agent=AgentName.BANK,
                summary="No transaction rows were detected. Please verify document quality or statement format.",
                data={"transactions": []},
            )

        df = pd.DataFrame(rows)
        total_debits = float(df["debit"].sum())
        total_credits = float(df["credit"].sum())
        cash_rows = df[df["description"].str.contains("cash", case=False, na=False)]
        interest_rows = df[df["description"].str.contains("interest", case=False, na=False)]
        emi_rows = df[df["description"].str.contains("emi|loan", case=False, na=False)]
        large_rows = df[(df["debit"] >= 100000) | (df["credit"] >= 100000)]

        observations = []
        if not cash_rows.empty:
            observations.append(f"{len(cash_rows)} cash-related transaction(s) found.")
        if not interest_rows.empty:
            observations.append("Interest income appears in the statement and should be reconciled.")
        if not emi_rows.empty:
            observations.append("Loan/EMI transactions were identified for liability reconciliation.")
        if not large_rows.empty:
            observations.append(f"{len(large_rows)} high-value transaction(s) of INR 100000 or more found.")
        if total_credits < total_debits:
            observations.append("Total debits exceed total credits for the provided period.")

        summary = (
            f"Analyzed {len(df)} transactions. Total credits: INR {total_credits:,.2f}; "
            f"total debits: INR {total_debits:,.2f}."
        )

        return TaskResult(
            agent=AgentName.BANK,
            summary=summary,
            data={
                "transaction_count": len(df),
                "total_debits": total_debits,
                "total_credits": total_credits,
                "cash_transactions": cash_rows.to_dict(orient="records"),
                "interest_transactions": interest_rows.to_dict(orient="records"),
                "emi_transactions": emi_rows.to_dict(orient="records"),
                "large_transactions": large_rows.to_dict(orient="records"),
                "observations": observations,
            },
        )

