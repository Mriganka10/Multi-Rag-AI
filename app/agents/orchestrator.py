from pathlib import Path

from app.agents.bank_statement_agent import BankStatementAgent
from app.agents.financial_agent import FinancialAnalysisAgent
from app.agents.itr_agent import ITRAgent
from app.agents.ocr_agent import OCRAgent
from app.agents.scn_agent import SCNAgent
from app.core.config import settings
from app.llm.service import LLMService
from app.models.schemas import AgentDecision, AgentName, LearningOptions, TaskResult
from app.rag.learning import RAGLearningStore
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
        self.llm = LLMService()
        self.learning_store = RAGLearningStore(settings.data_dir / "knowledge")

    def analyze_text(
        self,
        query: str,
        text: str,
        learning_options: LearningOptions | None = None,
    ) -> TaskResult:
        decision = self.decide(query, text)
        result = self._run_decision(decision.agent, query, text)
        result.data["orchestrator_decision"] = decision.model_dump()
        return self._enrich_with_llm(
            query=query,
            text=text,
            result=result,
            learning_options=learning_options or LearningOptions(),
        )

    def analyze_file(
        self,
        query: str,
        file_path: Path,
        learning_options: LearningOptions | None = None,
    ) -> TaskResult:
        text = self.ocr_agent.extract_text(file_path)
        decision = self.decide(query, text)
        result = self._run_decision(decision.agent, query, text)
        result.data["orchestrator_decision"] = decision.model_dump()
        rows = self.ocr_agent.parse_transactions(text)
        if rows:
            output_path = settings.data_dir / "outputs" / f"{file_path.stem}.xlsx"
            self.ocr_agent.export_excel(rows, output_path)
            result.artifacts["excel"] = str(output_path)
        result.data["source_file"] = str(file_path)
        return self._enrich_with_llm(
            query=query,
            text=text,
            result=result,
            learning_options=learning_options or LearningOptions(),
        )

    def _enrich_with_llm(
        self,
        query: str,
        text: str,
        result: TaskResult,
        learning_options: LearningOptions,
    ) -> TaskResult:
        contexts = result.contexts
        if not contexts:
            contexts = self._retrieve_context_for_agent(
                result.agent,
                query,
                text,
                learning_options.tenant_id,
            )
            result.contexts = contexts

        generation = self.llm.generate_client_response(
            query=query,
            extracted_text=text,
            result=result,
            contexts=contexts,
        )
        result.client_response = generation.content
        result.llm = {
            "provider": generation.provider,
            "model": generation.model,
            "used_fallback": generation.used_fallback,
        }

        has_learning_consent = (
            learning_options.learning_consent or settings.rag_learning_default_consent
        )
        if settings.rag_learning_enabled and has_learning_consent and generation.content:
            learned_path = self.learning_store.save(
                query=query,
                result=result,
                client_response=generation.content,
                tenant_id=learning_options.tenant_id,
                approved=learning_options.approve_learning,
            )
            result.learned_context_path = str(learned_path)
            if learning_options.approve_learning:
                self.rag.refresh()

        return result

    def _retrieve_context_for_agent(
        self,
        agent_name: AgentName,
        query: str,
        text: str,
        tenant_id: str,
    ):
        learned_collection = f"learned_{tenant_id}"
        collections_by_agent = {
            AgentName.BANK: ["accounting_standards", learned_collection],
            AgentName.FINANCIAL: ["accounting_standards", learned_collection],
            AgentName.ITR: ["income_tax", learned_collection],
            AgentName.SCN: ["gst", "income_tax", "case_laws", "notifications", learned_collection],
            AgentName.OCR: ["accounting_standards", learned_collection],
        }
        return self.rag.retrieve(
            query=f"{query}\n{text}",
            collections=collections_by_agent.get(agent_name),
            top_k=3,
        )

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
