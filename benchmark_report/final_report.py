from __future__ import annotations

import json
from pathlib import Path


def generate_final_report(root=".") -> Path:
    root = Path(root)
    tables = root / "benchmark_report" / "tables"
    figures = root / "benchmark_report" / "figures"
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    ett = json.loads((root / "results/ettm1/baseline/summary_dlinear.json").read_text())
    table = json.loads((root / "results/tableshift/summary.json").read_text())
    cifar = json.loads((root / "results/cifar10c/summary.json").read_text())
    lines = [
        "# Evidence-Driven Autonomous AI Scientist Benchmark Platform",
        "",
        "## Question",
        "",
        "Does an evidence-driven autonomous research loop improve ML discovery?",
        "",
        "## Results",
        "",
        "| Benchmark | Status | Primary result | Implementation |",
        "| --- | --- | --- | --- |",
        f"| ETTm1 | SUCCEEDED | DLinear MSE={ett['metrics']['mse']:.6f}, MAE={ett['metrics']['mae']:.6f} | NumPy fallback |",
        f"| CIFAR-10-C | {cifar['status']} | {cifar.get('BLOCKED_REASON', 'N/A')} | {cifar.get('implementation', 'N/A')} |",
        f"| TableShift diabetes_readmission | {table['status']} | XGBoost OOD AUROC={table.get('models', {}).get('XGBoost', {}).get('ood_auroc', 'N/A')} | NumPy fallback |",
        "",
        "## Trajectories",
        "",
        "ETTm1 has a complete AI Scientist trajectory with hypothesis, experiment, evidence graph, reviews, integrity audit, and meta-review. CIFAR-10-C and TableShift have auditable benchmark trajectory records; CIFAR-10-C is explicitly blocked by its unavailable 2.9GB archive.",
        "",
        "## Ablations",
        "",
        "The declared system ablation modes are recorded in `results/ablations/summary.json`. Modes that require changing the existing core loop are marked blocked rather than silently simulated.",
        "",
        "## Integrity and limitations",
        "",
        "- Core `auto_research/src/ai_scientist/` was not modified.",
        "- ETTm1 uses real downloaded data and a complete trajectory.",
        "- PyTorch/CUDA was unavailable; DLinear, PatchTST, XGBoost, and MLP are explicitly marked fallback implementations.",
        "- CIFAR-10-C is blocked because downloading the official archive was not feasible in this environment.",
        "- No claim that the research loop improves discovery is supported by this run alone; the ETTm1 meta-review remained `REVISE`.",
        "",
        "## Next benchmark",
        "",
        "CIFAR10-C",
    ]
    report = root / "benchmark_report" / "final_report.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(generate_final_report())
