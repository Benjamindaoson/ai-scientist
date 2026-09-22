from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

class ExperimentPlanner:
    def plan(
        self,
        hypothesis: dict[str, Any],
        baseline: dict[str, Any],
        workspace: str | Path,
        data_root: str | Path,
        max_windows: int,
        evaluation_split: str = "val",
        dataset_kwargs: dict[str, Any] | None = None,
    ) -> ExperimentSpec:
        workspace = Path(workspace)
        config_path = workspace / "experiment_config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(hypothesis.get("mutation", {}), indent=2) + "\n", encoding="utf-8")
        script = workspace / "run_experiment.py"
        script.write_text(
            "import json\n"
            "from benchmarks.runners.baseline_runner import run_baseline\n"
            f"config = json.load(open('experiment_config.json'))\n"
            f"summary = run_baseline('ettm1', 'dlinear', data_root={str(Path(data_root).resolve())!r}, "
            f"max_windows={max_windows}, evaluation_split={evaluation_split!r}, persist=False, model_kwargs=config, **{dataset_kwargs or {}})\n"
            "json.dump(summary, open('metrics.json', 'w'), indent=2)\n",
            encoding="utf-8",
        )
        root = Path(__file__).parents[2].resolve()
        env = {"PYTHONPATH": os.pathsep.join([str(root), str(root / "auto_research" / "src")])}
        import sys
        source = Path(__file__).parents[2] / "auto_research" / "src"
        if str(source) not in sys.path:
            sys.path.insert(0, str(source))
        from ai_scientist.experiment.models import ExperimentSpec

        return ExperimentSpec(
            hypothesis_id=hypothesis["id"],
            objective=f"Test: {hypothesis['claim']}",
            command=[sys.executable, "run_experiment.py"],
            workspace=str(workspace),
            metrics_file="metrics.json",
            baseline=baseline,
            success_criteria={"mse": {"op": "<", "value": baseline["metrics"]["mse"]}},
            env=env,
            max_attempts=1,
            metadata={"benchmark": "ETTm1", "mutation": hypothesis.get("mutation", {}), "evaluation_split": evaluation_split},
        )
