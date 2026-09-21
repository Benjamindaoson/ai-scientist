"""Predeclared system ablations for Benchmark v1."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SystemVariant(str, Enum):
    FULL = "full"
    NO_HYPOTHESIS_EVOLUTION = "no_hypothesis_evolution"
    NO_REVIEW_EXPERIMENT = "no_review_experiment"
    SINGLE_SHOT = "single_shot"


@dataclass(frozen=True)
class VariantConfig:
    evolve_hypothesis: bool
    execute_ablations: bool
    execute_review_actions: bool
    run_review: bool
    run_integrity: bool = True


VARIANT_CONFIGS = {
    SystemVariant.FULL: VariantConfig(True, True, True, True),
    SystemVariant.NO_HYPOTHESIS_EVOLUTION: VariantConfig(False, True, True, True),
    SystemVariant.NO_REVIEW_EXPERIMENT: VariantConfig(True, True, False, True),
    SystemVariant.SINGLE_SHOT: VariantConfig(False, False, False, False),
}


def config_for(variant: SystemVariant | str) -> VariantConfig:
    return VARIANT_CONFIGS[SystemVariant(variant)]
