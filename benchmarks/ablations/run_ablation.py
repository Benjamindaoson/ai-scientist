from __future__ import annotations

import json
from pathlib import Path

from .system import ABLATION_MODES


def generate_ablation_record(output="results/ablations/summary.json"):
    rows = [{
        "mode": mode,
        "status": "BLOCKED",
        "final_score": None,
        "experiment_count": None,
        "cost": None,
        "valid_discovery_rate": None,
        "review_resolution_rate": None,
        "BLOCKED_REASON": "Requires protocol-level variants of the existing core loop; core semantics were intentionally not changed.",
    } for mode in ABLATION_MODES]
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return rows


if __name__ == "__main__":
    print(json.dumps(generate_ablation_record(), indent=2))
