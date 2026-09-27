from __future__ import annotations

from .contracts import Capability, ResearchRole, TaskSpec


ROLE_CAPABILITIES = {
    ResearchRole.SCOUT: {Capability.DISCOVER_CANDIDATES, Capability.PRIOR_SEARCH, Capability.CANDIDATE_POOL, Capability.NOVELTY_EVIDENCE},
    ResearchRole.PI: {Capability.FORMALIZE_QUESTION, Capability.COMPETING_EXPLANATIONS, Capability.STUDY_DESIGN, Capability.NEXT_RESEARCH_ACTION, Capability.INTERPRETATION},
    ResearchRole.ENGINEER: {Capability.IMPLEMENT_CODE, Capability.IMPLEMENT_BASELINE, Capability.IMPLEMENT_EXPERIMENT, Capability.TEST_CODE, Capability.RECORD_RUN_ARTIFACT},
    ResearchRole.ANALYST: {Capability.DESIGN_MEASUREMENT, Capability.FORMAL_ANALYSIS, Capability.STATISTICS, Capability.UNCERTAINTY, Capability.FORMAL_EVIDENCE},
    ResearchRole.EDITOR: {Capability.DRAFT_PAPER, Capability.LATEX, Capability.FIGURES_TABLES, Capability.APPENDIX, Capability.REBUTTAL_EDITING, Capability.SUBMISSION_PACKAGE},
    ResearchRole.REVIEWER: {Capability.INDEPENDENT_NOVELTY_AUDIT, Capability.PROTOCOL_AUDIT, Capability.INDEPENDENT_RESULT_AUDIT, Capability.CLAIM_EVIDENCE_AUDIT, Capability.PAPER_REVIEW},
}


def authorize(task: TaskSpec) -> None:
    if task.capability not in ROLE_CAPABILITIES[task.role]:
        raise PermissionError(f"{task.role.value} is not permitted to perform {task.capability.value}")
