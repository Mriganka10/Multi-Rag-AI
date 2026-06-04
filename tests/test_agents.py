from pathlib import Path

from app.agents.bank_statement_agent import BankStatementAgent
from app.agents.financial_agent import FinancialAnalysisAgent
from app.agents.orchestrator import AgentOrchestrator
from app.agents.scn_agent import SCNAgent
from app.models.schemas import AgentName
from app.rag.multi_rag import MultiRAG


SAMPLE_BANK = """
Date Description Debit Credit Balance
2026-04-03 Cash Deposit 0 150000 400000
2026-04-07 Vendor Payment 85000 0 315000
2026-04-11 Interest Credit 0 3500 318500
"""


def test_bank_statement_agent_flags_large_cash_and_interest() -> None:
    result = BankStatementAgent().run("Analyze bank statement", SAMPLE_BANK)

    assert result.agent == AgentName.BANK
    assert result.data["total_credits"] == 153500
    assert len(result.data["cash_transactions"]) == 1
    assert len(result.data["interest_transactions"]) == 1
    assert result.data["large_transactions"][0]["credit"] == 150000


def test_scn_agent_generates_draft_reply() -> None:
    rag = MultiRAG(Path("data/knowledge"))
    scn = """
    Show Cause Notice under section 73 of the CGST Act.
    It is alleged that input tax credit of INR 250000 was wrongly availed.
    """

    result = SCNAgent(rag).run("Draft SCN reply", scn)

    assert result.agent == AgentName.SCN
    assert "draft_reply" in result.data
    assert "section 73" in [section.lower() for section in result.data["sections_detected"]]
    assert result.requires_human_review is True


def test_financial_agent_computes_ratios_and_conflicts() -> None:
    text = """
    Current Assets 500000
    Current Liabilities 250000
    Inventory 100000
    Total Debt 800000
    Equity 300000
    Revenue 1200000
    Net Profit 180000
    Total Assets 1000000
    Total Liabilities 650000
    """

    result = FinancialAnalysisAgent().run("Analyze financial statements", text)

    assert result.agent == AgentName.FINANCIAL
    assert result.data["ratios"]["current_ratio"] == 2
    assert result.data["ratios"]["debt_equity_ratio"] > 2
    assert result.data["conflicts"]


def test_orchestrator_routes_scn() -> None:
    decision = AgentOrchestrator().decide("Analyze this GST show cause notice", "section 73")

    assert decision.agent == AgentName.SCN

