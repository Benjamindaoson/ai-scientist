"""Export a complete, inspectable research package."""
from __future__ import annotations

import json
from pathlib import Path

from .manuscript import ManuscriptBuilder
from .research_state import ResearchState


class ResearchPackageWriter:
    """Persist structured state, manuscript, evidence graph, reviews, and audits."""

    def __init__(self):
        self.manuscript_builder = ManuscriptBuilder()

    def write(self, state: ResearchState, output_dir: str | Path) -> dict[str, str]:
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)
        (root / "reviews").mkdir(exist_ok=True)
        (root / "integrity").mkdir(exist_ok=True)

        manuscript = self.manuscript_builder.write(state, root / "manuscript.md")
        state_path = root / "research_state.json"
        state_path.write_text(
            json.dumps(state.to_dict(), indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

        graph_path = root / "evidence_graph.json"
        graph_path.write_text(
            json.dumps(state.evidence_graph, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

        reviews_path = root / "reviews" / "reviews.json"
        reviews_path.write_text(
            json.dumps(state.reviews, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

        rebuttals_path = root / "reviews" / "rebuttals.json"
        rebuttals_path.write_text(
            json.dumps(state.rebuttals, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

        audit_path = root / "integrity" / "audits.json"
        audit_path.write_text(
            json.dumps(state.integrity_audits, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

        return {
            "root": str(root),
            "manuscript": str(root / "manuscript.md"),
            "state": str(state_path),
            "evidence_graph": str(graph_path),
            "reviews": str(reviews_path),
            "rebuttals": str(rebuttals_path),
            "integrity": str(audit_path),
        }
