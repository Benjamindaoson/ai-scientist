"""Generate a reproducible research manuscript from structured state."""
from __future__ import annotations

from pathlib import Path

from .research_state import ResearchState


class ManuscriptBuilder:
    """Build Markdown from structured research artifacts; never invent results."""

    def build(self, state: ResearchState) -> str:
        hypotheses = state.hypotheses[-5:]
        experiments = state.experiment_runs
        ablations = state.ablations
        evidence = state.evidence

        lines = [
            f"# {state.metadata.get('title', 'Autonomous Research Report')}",
            "",
            "## Research Problem",
            state.problem,
            "",
            "## Hypotheses",
        ]
        for h in hypotheses:
            lines.append(f"- **{h.get('id','')}** — {h.get('claim','')} ({h.get('status','')})")
        lines += ["", "## Experiments"]
        for r in experiments:
            lines += [
                f"### {r.get('experiment_id','')}",
                f"- Status: {r.get('status','')}",
                f"- Metrics: {r.get('metrics', {})}",
            ]
        lines += ["", "## Ablations"]
        for a in ablations:
            lines.append(f"- {a.get('hypothesis_id','')}: {len(a.get('variants', []))} planned variants")
        lines += ["", "## Evidence"]
        for ev in evidence:
            lines.append(
                f"- {ev.get('id','')} -> hypothesis {ev.get('hypothesis_id','')}: {ev.get('evaluation', {})}"
            )
        lines += [
            "",
            "## Limitations",
            "- Conclusions are limited to the executed experiments and recorded evidence.",
            "- Unresolved objections and failed experiments remain visible in the research package.",
        ]
        return "\n".join(lines) + "\n"

    def write(self, state: ResearchState, output_path: str | Path) -> str:
        text = self.build(state)
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        state.manuscript = {"path": str(path), "format": "markdown", "content": text}
        return text
