from __future__ import annotations

ABLATION_MODES = ("full", "single_shot", "no_hypothesis_evolution", "no_review_loop", "no_integrity")


def run_system_ablation(run_callable, modes=ABLATION_MODES) -> list[dict]:
    return [{"mode": mode, **run_callable(mode)} for mode in modes]
