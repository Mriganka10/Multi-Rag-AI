import re


import pandas as pd
from sklearn.ensemble import IsolationForest

from app.models.schemas import AgentName, TaskResult


class FinancialAnalysisAgent:
    def run(self, query: str, text: str) -> TaskResult:
        metrics = self._extract_metrics(text)
        ratios = self._compute_ratios(metrics)
        anomalies = self._detect_numeric_anomalies(metrics)
        conflicts = self._detect_conflicts(metrics)

        summary = "Financial statement analysis completed with ratios and anomaly indicators."
        return TaskResult(
            agent=AgentName.FINANCIAL,
            summary=summary,
            data={
                "query": query,
                "metrics": metrics,
                "ratios": ratios,
                "anomalies": anomalies,
                "conflicts": conflicts,
                "commentary": self._commentary(ratios, anomalies, conflicts),
            },
        )

    def _extract_metrics(self, text: str) -> dict[str, float]:
        metrics: dict[str, float] = {}
        pattern = re.compile(
            r"(?P<label>[A-Za-z][A-Za-z\s&/-]{2,40})[:\s]+(?P<value>-?\d+(?:,\d{3})*(?:\.\d+)?)"
        )
        for match in pattern.finditer(text):
            label = "_".join(match.group("label").strip().lower().split())
            metrics[label] = float(match.group("value").replace(",", ""))
        return metrics

    def _compute_ratios(self, metrics: dict[str, float]) -> dict[str, float | None]:
        current_assets = self._get(metrics, "current_assets")
        current_liabilities = self._get(metrics, "current_liabilities")
        inventory = self._get(metrics, "inventory")
        total_debt = self._get(metrics, "total_debt", "debt")
        equity = self._get(metrics, "equity", "shareholders_equity")
        net_profit = self._get(metrics, "net_profit", "profit_after_tax")
        revenue = self._get(metrics, "revenue", "sales")
        total_assets = self._get(metrics, "total_assets")

        return {
            "current_ratio": self._safe_div(current_assets, current_liabilities),
            "quick_ratio": self._safe_div(
                None if current_assets is None else current_assets - (inventory or 0),
                current_liabilities,
            ),
            "debt_equity_ratio": self._safe_div(total_debt, equity),
            "net_profit_margin": self._safe_div(net_profit, revenue),
            "return_on_assets": self._safe_div(net_profit, total_assets),
            "return_on_equity": self._safe_div(net_profit, equity),
        }

    def _detect_numeric_anomalies(self, metrics: dict[str, float]) -> list[dict[str, float | str]]:
        if len(metrics) < 4:
            return []
        labels = list(metrics)
        values = pd.DataFrame({"value": list(metrics.values())})
        model = IsolationForest(contamination=min(0.25, 1 / len(metrics)), random_state=42)
        predictions = model.fit_predict(values)
        return [
            {"metric": labels[index], "value": float(values.iloc[index]["value"])}
            for index, prediction in enumerate(predictions)
            if prediction == -1
        ]

    def _detect_conflicts(self, metrics: dict[str, float]) -> list[str]:
        conflicts = []
        assets = self._get(metrics, "total_assets")
        liabilities = self._get(metrics, "total_liabilities")
        equity = self._get(metrics, "equity", "shareholders_equity")
        if assets is not None and liabilities is not None and equity is not None:
            difference = abs(assets - (liabilities + equity))
            if difference > max(1, assets * 0.01):
                conflicts.append("Balance sheet equation does not reconcile within 1% tolerance.")

        revenue = self._get(metrics, "revenue", "sales")
        profit = self._get(metrics, "net_profit", "profit_after_tax")
        if revenue is not None and profit is not None and profit > revenue:
            conflicts.append("Net profit exceeds revenue, which requires review.")
        return conflicts

    def _commentary(
        self,
        ratios: dict[str, float | None],
        anomalies: list[dict[str, float | str]],
        conflicts: list[str],
    ) -> list[str]:
        commentary = []
        current_ratio = ratios.get("current_ratio")
        if current_ratio is not None and current_ratio < 1:
            commentary.append("Current ratio is below 1.0, indicating potential liquidity pressure.")
        debt_equity = ratios.get("debt_equity_ratio")
        if debt_equity is not None and debt_equity > 2:
            commentary.append("Debt-equity ratio is above 2.0 and should be reviewed for leverage risk.")
        if anomalies:
            commentary.append(f"{len(anomalies)} numeric anomaly indicator(s) detected.")
        if conflicts:
            commentary.extend(conflicts)
        return commentary or ["No major ratio warning was detected from the supplied values."]

    def _get(self, metrics: dict[str, float], *names: str) -> float | None:
        for name in names:
            if name in metrics:
                return metrics[name]
        return None

    def _safe_div(self, numerator: float | None, denominator: float | None) -> float | None:
        if numerator is None or denominator in {None, 0}:
            return None
        return round(numerator / denominator, 4)

