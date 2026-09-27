from __future__ import annotations

from typing import Any


TERMINAL = {"KILL", "BLOCKED", "FATAL"}


def decision_value(decision: dict[str, Any] | None) -> str:
    return str(decision["decision"]) if decision else "BLOCKED"


def idea_route(value: str, reframe_count: int, max_reframes: int) -> str:
    if value in {"CONTINUE", "START", "READY"}:
        return "continue"
    if value == "REFRAME" and reframe_count <= max_reframes:
        return "reframe"
    if value == "WAIT_FOR_HUMAN":
        return "human"
    return "archive"


def protocol_route(value: str) -> str:
    return {
        "CONTINUE": "pass", "PASS": "pass", "READY": "pass",
        "REVISE_SCIENCE": "science", "REVISE_MEASUREMENT": "measurement", "REVIEW_REQUIRED": "review",
    }.get(value, "archive")


def killer_route(value: str) -> str:
    return {"CONTINUE": "continue", "REFRAME": "reframe", "WAIT_FOR_HUMAN": "human"}.get(value, "archive")


def progress_route(value: str) -> str:
    return {"MORE_EVIDENCE": "more", "READY_TO_CONFIRM": "confirm", "REFRAME": "reframe", "WAIT_FOR_HUMAN": "human"}.get(value, "archive")


def audit_route(value: str) -> str:
    return {
        "PASS": "pass", "CONTINUE": "pass", "ENGINEERING_ISSUE": "engineering",
        "ANALYSIS_ISSUE": "analysis", "SCIENTIFIC_SCOPE_ISSUE": "science", "NOVELTY_ISSUE": "novelty",
    }.get(value, "archive")
