from __future__ import annotations

import json
from pathlib import Path

from benchmarks.core.trajectory import Trajectory


def export_benchmark_trajectory(name: str, result: dict, root="benchmarks/trajectories") -> Path:
    path = Path(root) / name
    trajectory = Trajectory(path)
    status = result.get("status", "UNKNOWN")
    trajectory.write("problem", {"benchmark": name})
    trajectory.write("baseline", result)
    trajectory.write("hypothesis_history", [])
    trajectory.write("experiment_history", {"status": status, "experiments": []})
    trajectory.write("evidence_graph", {"nodes": [], "edges": []})
    trajectory.write("reviews", {"reviews": [], "rebuttals": []})
    trajectory.write("final_decision", {"decision": status, "BLOCKED_REASON": result.get("BLOCKED_REASON")})
    return path
