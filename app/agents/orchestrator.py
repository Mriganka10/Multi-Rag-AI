from pathlib import Path

from app.agents.bank_statement_agent import BankStatementAgent
from app.agents.financial_agent import FinancialAnalysisAgent
from app.agents.itr_agent import ITRAgent
from app.agents.ocr_agent import OCRAgent
from app.agents.scn_agent import SCNAgent
from app.core.config import settings
from app.models.schemas import AgentDecision, AgentName, TaskResult
from app.rag.multi_rag import MultiRAG


class AgentOrchestrator:
    def __init__(self) -> None:
        rag = MultiRAG(settings.data_dir / "knowledge")
        self.ocr_agent = OCRAgent()
        self.bank_agent = BankStatementAgent()
        self.scn_agent = SCNAgent(rag)
        self.financial_agent = FinancialAnalysisAgent()
        self.itr_agent = ITRAgent()
        self.rag = rag

    def analyze_text(self, query: str, text: str) -> TaskResult:
        decision = self.decide(query, text)
        result = self._run_decision(decision.agent, query, text)
        result.data["orchestrator_decision"] = decision.model_dump()
        return result

    def analyze_file(self, query: str, file_path: Path) -> TaskResult:
        text = self.ocr_agent.extract_text(file_path)
        result = self.analyze_text(query=query, text=text)
        rows = self.ocr_agent.parse_transactions(text)
        if rows:
            output_path = settings.data_dir / "outputs" / f"{file_path.stem}.xlsx"
            self.ocr_agent.export_excel(rows, output_path)
            result.artifacts["excel"] = str(output_path)
        result.data["source_file"] = str(file_path)
        return result

    def decide(self, query: str, text: str) -> AgentDecision:
        combined = f"{query}\n{text}".lower()
        if any(word in combined for word in ["show cause", "scn", "notice", "section 73", "section 74"]):
            return AgentDecision(agent=AgentName.SCN, reason="Notice/SCN language detected.")
        if any(word in combined for word in ["itr", "income tax return", "form 16", "ais", "26as"]):
            return AgentDecision(agent=AgentName.ITR, reason="ITR preparation language detected.")
        if any(
            word in combined
            for word in ["balance sheet", "profit and loss", "current assets", "debt equity", "revenue"]
        ):
            return AgentDecision(agent=AgentName.FINANCIAL, reason="Financial statement metrics detected.")
        if any(word in combined for word in ["bank", "statement", "debit", "credit", "balance"]):
            return AgentDecision(agent=AgentName.BANK, reason="Bank statement transaction terms detected.")
        return AgentDecision(agent=AgentName.OCR, reason="Defaulted to document extraction.")

    def _run_decision(self, agent_name: AgentName, query: str, text: str) -> TaskResult:
        if agent_name == AgentName.SCN:
            return self.scn_agent.run(query, text)
        if agent_name == AgentName.ITR:
            return self.itr_agent.run(query, text)
        if agent_name == AgentName.FINANCIAL:
            return self.financial_agent.run(query, text)
        if agent_name == AgentName.BANK:
            return self.bank_agent.run(query, text)
        return self.ocr_agent.run(query, text)

