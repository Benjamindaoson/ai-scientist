"""Research manuscript drafting from structured state."""
from __future__ import annotations

import json
from typing import Any

from .core.gateway import BaseGateway
from .research_state import ResearchState


class ManuscriptWriter:
    def __init__(self, gateway: BaseGateway | None = None):
        self.gateway = gateway

    def draft(self, state: ResearchState, title: str = "Autonomous Research Report") -> dict[str, Any]:
        if self.gateway:
            prompt = (
                "Write a concise scientific manuscript in Markdown using only evidence in the supplied state. "
                "Every empirical claim must cite its evidence id in square brackets. Do not invent results.\n"
                f"STATE={json.dumps(state.to_dict(), default=str)}"
            )
            try:
                body = self.gateway.generate(prompt)
                return {"title": title, "format": "markdown", "body": body}
            except Exception:
                pass

        lines = [f"# {title}", "", "## Research Question", state.problem, "", "## Hypotheses"]
        for h in state.hypotheses:
            lines.append(f"- {h.get('claim', '')} ({h.get('status', 'UNKNOWN')})")
        lines.extend(["", "## Experimental Evidence"])
        for e in state.evidence:
            metrics = e.get("metrics", {})
            lines.append(f"- [{e.get('id')}] metrics={json.dumps(metrics, sort_keys=True)}")
        lines.extend(["", "## Ablations"])
        for a in state.ablations:
            lines.append(f"- Hypothesis {a.get('hypothesis_id')}: {len(a.get('variants', []))} planned variants")
        lines.extend(["", "## Limitations and Open Objections"])
        for o in state.objections:
            lines.append(f"- {o.get('title', o.get('description', str(o)))}")
        return {"title": title, "format": "markdown", "body": "\n".join(lines)}
