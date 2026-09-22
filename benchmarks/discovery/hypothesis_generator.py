from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re
from typing import Any

from .problem import ResearchProblem


@dataclass
class CandidateHypothesis:
    id: str
    claim: str
    mechanism: str
    expected_effect: str
    falsification: str
    mutation: dict[str, Any]
    novelty: float
    feasibility: float
    expected_impact: float
    rank_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class HypothesisGenerator:
    """Generate auditable candidates with an optional real LLM gateway.

    The candidate set is derived from the problem constraints and baseline
    configuration. It is deliberately conservative: a candidate is only
    selected if its mutation is executable by the benchmark adapter.
    """

    def __init__(self, gateway=None):
        self.gateway = gateway
        self.last_source = "deterministic_fallback"

    def _llm_candidates(self, problem: ResearchProblem, baseline_result: dict[str, Any]) -> list[dict[str, Any]]:
        prompt = f"""You are an ML research scientist. Generate exactly five distinct, executable hypotheses for this benchmark.
Research problem: {problem.description}
Benchmark: {problem.benchmark}
Baseline metrics: {json.dumps(baseline_result.get('metrics', {}))}
Constraints: {json.dumps(problem.constraints)}
Only propose configuration mutations supported by the current DLinear ETTm1 adapter. Use an odd integer moving_avg between 1 and 95 as the mutation.
Return JSON only: a list of objects with keys id, claim, mechanism, expected_effect, falsification, mutation, novelty, feasibility, expected_impact.
Do not claim success; make each hypothesis falsifiable."""
        raw = self.gateway.generate(prompt, model=getattr(self.gateway, "model", None), max_tokens=1400, temperature=0)
        match = re.search(r"\[.*\]", raw, flags=re.DOTALL)
        if not match:
            raise ValueError("LLM response did not contain a JSON list")
        items = json.loads(match.group(0))
        if not isinstance(items, list) or len(items) < 5:
            raise ValueError("LLM returned fewer than five hypotheses")
        output = []
        for index, item in enumerate(items[:5], start=1):
            mutation = item.get("mutation", {})
            moving_avg = mutation.get("moving_avg")
            if not isinstance(moving_avg, int) or moving_avg < 1 or moving_avg > 95 or moving_avg % 2 == 0:
                raise ValueError("LLM returned an unsupported mutation")
            novelty = float(item["novelty"])
            feasibility = float(item["feasibility"])
            impact = float(item["expected_impact"])
            output.append(CandidateHypothesis(
                id=f"hyp_{index:03d}", claim=str(item["claim"]), mechanism=str(item["mechanism"]),
                expected_effect=str(item["expected_effect"]), falsification=str(item["falsification"]),
                mutation={"moving_avg": moving_avg}, novelty=novelty, feasibility=feasibility,
                expected_impact=impact, rank_score=round((novelty + feasibility + impact) / 3, 6),
            ).to_dict())
        self.last_source = "llm"
        return sorted(output, key=lambda item: item["rank_score"], reverse=True)

    def generate(
        self,
        problem: ResearchProblem,
        baseline_result: dict[str, Any],
        literature_context: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        del literature_context
        if self.gateway is not None:
            try:
                return self._llm_candidates(problem, baseline_result)
            except Exception:
                self.last_source = "deterministic_fallback_after_llm_error"
        candidates = [
            ("Adaptive moving-average window improves temporal stability", "A longer decomposition window suppresses high-frequency noise", "MSE decrease", "No MSE decrease against the unchanged window", {"moving_avg": 49}, .70, .95, .70),
            ("Shorter moving-average window preserves local dynamics", "A shorter trend window reduces lag at regime changes", "MAE decrease", "No MAE decrease against the unchanged window", {"moving_avg": 13}, .65, .98, .62),
            ("Moderate smoothing is a Pareto compromise", "An intermediate window balances noise removal and responsiveness", "MSE/MAE improve together", "Either metric worsens beyond tolerance", {"moving_avg": 25}, .45, 1.0, .55),
            ("A wider smoothing window improves seasonal extrapolation", "A wider trend window gives the linear head a more stable seasonal signal", "MSE decrease", "MSE is not lower with the wider window", {"moving_avg": 37}, .72, .95, .74),
            ("Channel-wise decomposition is sufficient under fixed compute", "Independent channel heads avoid cross-channel overfitting", "Stable metrics with no parameter increase", "Cross-channel coupling is required for improvement", {"moving_avg": 31}, .55, .92, .58),
        ]
        output = []
        for index, item in enumerate(candidates, start=1):
            claim, mechanism, effect, falsification, mutation, novelty, feasibility, impact = item
            score = round((novelty + feasibility + impact) / 3, 6)
            output.append(CandidateHypothesis(
                id=f"hyp_{index:03d}", claim=claim, mechanism=mechanism,
                expected_effect=effect, falsification=falsification,
                mutation=mutation, novelty=novelty, feasibility=feasibility,
                expected_impact=impact, rank_score=score,
            ).to_dict())
        return sorted(output, key=lambda item: item["rank_score"], reverse=True)
