"""Persistent Objection Ledger Service (v4).

Manages the lifecycle of scientific objections across research runs.
Ensures historical objections are never silently dropped.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from ai_scientist.core.models.domain import (
    ObjectionSeverity,
    ObjectionStatus,
    ObjectionCategory,
    ResolutionType,
    ScientificObjection,
)


@dataclass
class ObjectionSummary:
    """Summary view of objections for a research project."""
    total: int = 0
    open_fatal: int = 0
    open_major: int = 0
    open_minor: int = 0
    resolved: int = 0
    invalidated: int = 0
    accepted_risk: int = 0
    requires_human: int = 0

    def has_blocking_objections(self) -> bool:
        """Returns True if there are open FATAL objections."""
        return self.open_fatal > 0

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "open_fatal": self.open_fatal,
            "open_major": self.open_major,
            "open_minor": self.open_minor,
            "resolved": self.resolved,
            "invalidated": self.invalidated,
            "accepted_risk": self.accepted_risk,
            "requires_human": self.requires_human,
            "has_blocking_objections": self.has_blocking_objections(),
        }


@dataclass
class ObjectionReviewResult:
    """Result of reviewing an objection against new evidence."""
    objection_id: str
    previous_status: ObjectionStatus
    new_status: ObjectionStatus
    resolution_type: ResolutionType | None = None
    resolution_reason: str = ""
    resolved_by_evidence_ids: list[str] = field(default_factory=list)
    review_note: str = ""

    def to_dict(self) -> dict:
        return {
            "objection_id": self.objection_id,
            "previous_status": self.previous_status.value,
            "new_status": self.new_status.value,
            "resolution_type": self.resolution_type.value if self.resolution_type else None,
            "resolution_reason": self.resolution_reason,
            "resolved_by_evidence_ids": self.resolved_by_evidence_ids,
            "review_note": self.review_note,
        }


class ObjectionLedger:
    """Service for managing persistent scientific objections.

    Key responsibilities:
    1. Track objections across research runs
    2. Ensure historical objections are reviewed
    3. Prevent "silent disappearance" of objections
    4. Support evidence-based resolution

    Usage:
        ledger = ObjectionLedger(repo)
        ledger.load_project(project_id)

        # Add new objections from red team
        ledger.add_objection(target_type="RESEARCH_QUESTION", ...)

        # Get all open objections that need review
        open_objections = ledger.get_open_objections()

        # Review against new evidence
        result = ledger.review_objection(obj_id, new_evidence)

        # Check if research can proceed
        if ledger.can_proceed():
            ...
    """

    def __init__(self, repo):
        """Initialize the ObjectionLedger.

        Args:
            repo: Repository instance for database operations
        """
        self.repo = repo
        self.project_id: str | None = None
        self.current_run: int = 0
        self._objections_cache: list[dict] = []

    def load_project(self, project_id: str, current_run: int = 1) -> None:
        """Load a project's objection state.

        Args:
            project_id: Project to load
            current_run: Current research run number
        """
        self.project_id = project_id
        self.current_run = current_run
        self._refresh_cache()

    def _refresh_cache(self) -> None:
        """Refresh the local cache of objections."""
        if not self.project_id:
            return
        self._objections_cache = self.repo.list_objections(self.project_id)

    # ──────────────────────────────────────────────
    # Objection CRUD
    # ──────────────────────────────────────────────

    def add_objection(
        self,
        target_type: str,
        target_id: str,
        title: str,
        argument: str,
        category: ObjectionCategory,
        severity: ObjectionSeverity,
        supporting_evidence_ids: list[str] | None = None,
        contradictory_evidence_ids: list[str] | None = None,
        raised_by: str = "RED_TEAM",
    ) -> dict:
        """Add a new scientific objection.

        Args:
            target_type: Type of target (RESEARCH_QUESTION, DIRECTION, THEORY, etc.)
            target_id: ID of the target entity
            title: Short summary of the objection
            argument: Full argument/proof of the objection
            category: Category of objection
            severity: Severity level (FATAL, MAJOR, MINOR)
            supporting_evidence_ids: Evidence supporting this objection
            contradictory_evidence_ids: Evidence contradicting this objection
            raised_by: Who raised this objection

        Returns:
            The created objection record
        """
        import uuid

        # Accept the string values used by persisted/legacy callers as well as
        # the typed enums used by the current package API.
        category = ObjectionCategory(category)
        severity = ObjectionSeverity(severity)

        objection_data = {
            "id": f"obj_{uuid.uuid4().hex[:8]}",
            "project_id": self.project_id,
            "target_type": target_type,
            "target_id": target_id,
            "category": category.value,
            "severity": severity.value,
            "title": title,
            "argument": argument,
            "supporting_evidence_ids": supporting_evidence_ids or [],
            "contradictory_evidence_ids": contradictory_evidence_ids or [],
            "introduced_in_run": self.current_run,
            "last_reviewed_in_run": self.current_run,
            "status": ObjectionStatus.OPEN.value,
            "raised_by": raised_by,
        }

        result = self.repo.create_objection(objection_data)
        self._refresh_cache()
        return result

    def get_objection(self, objection_id: str) -> dict | None:
        """Get a specific objection by ID."""
        return self.repo.get_objection(objection_id)

    def get_objections_for_target(
        self,
        target_type: str,
        target_id: str,
        include_resolved: bool = True,
    ) -> list[dict]:
        """Get all objections for a specific target.

        Args:
            target_type: Type of target
            target_id: ID of target
            include_resolved: Whether to include resolved objections

        Returns:
            List of objection records
        """
        status_filter = None if include_resolved else ["OPEN", "UNDER_REVIEW", "REQUIRES_HUMAN"]

        if status_filter:
            return [
                obj for obj in self._objections_cache
                if obj["target_type"] == target_type
                and obj["target_id"] == target_id
                and obj["status"] in status_filter
            ]
        else:
            return [
                obj for obj in self._objections_cache
                if obj["target_type"] == target_type
                and obj["target_id"] == target_id
            ]

    # ──────────────────────────────────────────────
    # Objection Query
    # ──────────────────────────────────────────────

    def get_open_objections(
        self,
        severity: ObjectionSeverity | None = None,
    ) -> list[dict]:
        """Get all open (non-resolved) objections.

        Args:
            severity: Optional filter by severity

        Returns:
            List of open objection records, sorted by severity (FATAL first)
        """
        if severity:
            return self.repo.get_open_objections(self.project_id, severity.value)
        return self.repo.get_open_objections(self.project_id)

    def get_fatal_objections(self) -> list[dict]:
        """Get all open FATAL objections.

        These are the primary blockers for research continuation.

        Returns:
            List of open FATAL objections
        """
        return self.repo.get_fatal_objections(self.project_id)

    def get_requires_human_objections(self) -> list[dict]:
        """Get all objections requiring human judgment.

        Returns:
            List of REQUIRES_HUMAN status objections
        """
        return self.repo.list_objections(
            self.project_id,
            status=ObjectionStatus.REQUIRES_HUMAN.value,
        )

    def get_objections_needing_review(self) -> list[dict]:
        """Get objections that need review in the current run.

        This includes:
        - Open objections not reviewed in current run
        - New objections added this run

        Returns:
            List of objections needing review
        """
        all_open = self.get_open_objections()
        return [
            obj for obj in all_open
            if obj.get("last_reviewed_in_run", 0) < self.current_run
            or obj.get("introduced_in_run") == self.current_run
        ]

    def get_historical_objections(self) -> list[dict]:
        """Get all objections from previous runs.

        These are objections introduced in runs before the current one.

        Returns:
            List of historical objection records
        """
        all_objections = self.repo.list_objections(self.project_id)
        return [
            obj for obj in all_objections
            if obj.get("introduced_in_run", 0) < self.current_run
        ]

    def get_summary(self) -> ObjectionSummary:
        """Get a summary of all objections for the project.

        Returns:
            ObjectionSummary with counts by status and severity
        """
        all_objections = self.repo.list_objections(self.project_id)
        summary = ObjectionSummary()

        for obj in all_objections:
            summary.total += 1
            status = obj.get("status", "OPEN")
            severity = obj.get("severity", "MINOR")

            if status == "OPEN" or status == "UNDER_REVIEW":
                if severity == "FATAL":
                    summary.open_fatal += 1
                elif severity == "MAJOR":
                    summary.open_major += 1
                else:
                    summary.open_minor += 1
            elif status == "RESOLVED":
                summary.resolved += 1
            elif status == "INVALIDATED":
                summary.invalidated += 1
            elif status == "ACCEPTED_RISK":
                summary.accepted_risk += 1
            elif status == "REQUIRES_HUMAN":
                summary.requires_human += 1

        return summary

    # ──────────────────────────────────────────────
    # Objection Resolution
    # ──────────────────────────────────────────────

    def can_proceed(self) -> bool:
        """Check if research can proceed.

        Research CANNOT proceed if there are open FATAL objections
        that have not been resolved, invalidated, or accepted as risk.

        Returns:
            True if research can proceed, False otherwise
        """
        fatal_objections = self.get_fatal_objections()

        for obj in fatal_objections:
            status = obj.get("status")
            if status in [
                ObjectionStatus.OPEN.value,
                ObjectionStatus.UNDER_REVIEW.value,
                ObjectionStatus.REQUIRES_HUMAN.value,
            ]:
                return False

        return True

    def review_objection(
        self,
        objection_id: str,
        new_evidence: str | None = None,
        resolution_type: ResolutionType | None = None,
        resolution_reason: str = "",
        resolved_by_evidence_ids: list[str] | None = None,
        review_note: str = "",
    ) -> ObjectionReviewResult | None:
        """Review an objection and potentially resolve it.

        Args:
            objection_id: ID of objection to review
            new_evidence: New evidence to consider
            resolution_type: How the objection was resolved
            resolution_reason: Explanation of resolution
            resolved_by_evidence_ids: Evidence IDs that resolved it
            review_note: Note about this review

        Returns:
            ObjectionReviewResult or None if objection not found
        """
        objection = self.repo.get_objection(objection_id)
        if not objection:
            return None

        previous_status = ObjectionStatus(objection["status"])

        # Determine new status
        new_status = previous_status
        if resolution_type:
            if resolution_type == ResolutionType.ADDRESSED:
                new_status = ObjectionStatus.RESOLVED
            elif resolution_type == ResolutionType.DISMISSED:
                new_status = ObjectionStatus.INVALIDATED
            elif resolution_type == ResolutionType.ACCEPTED:
                new_status = ObjectionStatus.ACCEPTED_RISK
            elif resolution_type == ResolutionType.RETRACTED:
                new_status = ObjectionStatus.INVALIDATED

        # Build review note
        full_note = review_note
        if new_evidence:
            full_note = f"[Run {self.current_run}] {review_note}\nNew evidence: {new_evidence[:200]}..."

        # Update in database
        self.repo.update_objection_status(
            objection_id=objection_id,
            status=new_status.value,
            resolution_type=resolution_type.value if resolution_type else None,
            resolution_reason=resolution_reason,
            resolved_by_evidence_ids=resolved_by_evidence_ids,
            last_reviewed_in_run=self.current_run,
            review_note=full_note,
        )

        self._refresh_cache()

        return ObjectionReviewResult(
            objection_id=objection_id,
            previous_status=previous_status,
            new_status=new_status,
            resolution_type=resolution_type,
            resolution_reason=resolution_reason,
            resolved_by_evidence_ids=resolved_by_evidence_ids or [],
            review_note=full_note,
        )

    def resolve_with_evidence(
        self,
        objection_id: str,
        evidence_ids: list[str],
        resolution_reason: str,
    ) -> ObjectionReviewResult | None:
        """Resolve an objection by providing evidence that addresses it.

        Args:
            objection_id: ID of objection to resolve
            evidence_ids: Evidence IDs that address the objection
            resolution_reason: Why this evidence resolves the objection

        Returns:
            ObjectionReviewResult or None if not found
        """
        return self.review_objection(
            objection_id=objection_id,
            resolution_type=ResolutionType.ADDRESSED,
            resolution_reason=resolution_reason,
            resolved_by_evidence_ids=evidence_ids,
            review_note="Resolved with supporting evidence",
        )

    def accept_as_risk(
        self,
        objection_id: str,
        justification: str,
    ) -> ObjectionReviewResult | None:
        """Accept an objection as a known risk and proceed.

        Args:
            objection_id: ID of objection to accept as risk
            justification: Justification for accepting the risk

        Returns:
            ObjectionReviewResult or None if not found
        """
        return self.review_objection(
            objection_id=objection_id,
            resolution_type=ResolutionType.ACCEPTED,
            resolution_reason=justification,
            review_note="Accepted as known risk",
        )

    def invalidate(
        self,
        objection_id: str,
        reason: str,
    ) -> ObjectionReviewResult | None:
        """Invalidate an objection (found to be based on incorrect premises).

        Args:
            objection_id: ID of objection to invalidate
            reason: Why the objection is invalid

        Returns:
            ObjectionReviewResult or None if not found
        """
        return self.review_objection(
            objection_id=objection_id,
            resolution_type=ResolutionType.DISMISSED,
            resolution_reason=reason,
            review_note="Invalidated - based on incorrect premises",
        )

    def require_human_review(
        self,
        objection_id: str,
        reason: str,
    ) -> ObjectionReviewResult | None:
        """Mark an objection as requiring human judgment.

        Args:
            objection_id: ID of objection
            reason: Why human review is needed

        Returns:
            ObjectionReviewResult or None if not found
        """
        objection = self.repo.get_objection(objection_id)
        if not objection:
            return None

        previous_status = ObjectionStatus(objection["status"])

        self.repo.update_objection_status(
            objection_id=objection_id,
            status=ObjectionStatus.REQUIRES_HUMAN.value,
            resolution_reason=reason,
            last_reviewed_in_run=self.current_run,
            review_note=f"Requires human review: {reason}",
        )

        self._refresh_cache()

        return ObjectionReviewResult(
            objection_id=objection_id,
            previous_status=previous_status,
            new_status=ObjectionStatus.REQUIRES_HUMAN,
            review_note=f"Requires human review: {reason}",
        )

    # ──────────────────────────────────────────────
    # Historical Objection Management
    # ──────────────────────────────────────────────

    def get_all_objections_for_export(self) -> dict:
        """Get all objections in a format suitable for export/import.

        Returns:
            Dictionary with all objections and metadata
        """
        all_objections = self.repo.list_objections(self.project_id)
        summary = self.get_summary()

        return {
            "project_id": self.project_id,
            "current_run": self.current_run,
            "summary": summary.to_dict(),
            "objections": all_objections,
            "exported_at": datetime.utcnow().isoformat(),
        }

    def import_objections(self, data: dict) -> int:
        """Import objections from a previous export.

        Args:
            data: Exported objection data

        Returns:
            Number of objections imported
        """
        imported = 0
        for obj_data in data.get("objections", []):
            # Check if objection already exists (by title + target_id)
            existing = [
                o for o in self._objections_cache
                if o.get("title") == obj_data.get("title")
                and o.get("target_id") == obj_data.get("target_id")
            ]

            if not existing:
                # Create new objection with original metadata
                new_obj = dict(obj_data)
                new_obj["project_id"] = self.project_id
                new_obj["status"] = ObjectionStatus.OPEN.value  # Reset to open
                new_obj["last_reviewed_in_run"] = 0  # Mark for review
                if "id" in new_obj:
                    del new_obj["id"]  # Generate new ID

                self.repo.create_objection(new_obj)
                imported += 1

        self._refresh_cache()
        return imported

    def get_decision_graph(self) -> dict:
        """Get a graph showing objection resolution history.

        Returns:
            Dictionary representing the decision graph
        """
        all_objections = self.repo.list_objections(self.project_id)

        nodes = []
        edges = []

        for obj in all_objections:
            node_id = obj["id"]
            nodes.append({
                "id": node_id,
                "title": obj["title"],
                "severity": obj["severity"],
                "status": obj["status"],
                "introduced_run": obj["introduced_in_run"],
                "last_reviewed_run": obj["last_reviewed_in_run"],
            })

            # Add edges to evidence
            for ev_id in obj.get("resolved_by_evidence_ids", []):
                edges.append({
                    "from": node_id,
                    "to": ev_id,
                    "type": "resolved_by",
                })

        return {
            "nodes": nodes,
            "edges": edges,
            "run_count": self.current_run,
        }

    # ──────────────────────────────────────────────
    # Red Team Integration
    # ──────────────────────────────────────────────

    def create_objections_from_red_team_report(
        self,
        red_team_report: str,
        target_type: str,
        target_id: str,
        run_number: int,
    ) -> list[dict]:
        """Create objections from a red team report.

        Parses the red team report and creates objections for each
        identified issue.

        Args:
            red_team_report: Text of the red team report
            target_type: Type of target being reviewed
            target_id: ID of target being reviewed
            run_number: Current run number

        Returns:
            List of created objection records
        """
        created_objections = []

        # Parse for fatal/major issues
        lines = red_team_report.split("\n")
        current_issue = None
        current_severity = None
        current_argument = []

        for line in lines:
            line = line.strip()

            # Detect severity markers
            if "### 1." in line or "### 致命问题" in line or "FATAL" in line.upper():
                # Save previous issue
                if current_issue and current_severity:
                    self._create_parsed_objection(
                        title=current_issue,
                        argument="\n".join(current_argument),
                        severity=current_severity,
                        target_type=target_type,
                        target_id=target_id,
                    )

                current_severity = ObjectionSeverity.FATAL
                # Extract title
                current_issue = line.replace("###", "").replace("致命问题", "").replace("FATAL", "").strip()
                current_argument = []

            elif "### 2." in line or "### 3." in line or "### 4." in line:
                # Save previous issue
                if current_issue and current_severity:
                    created = self._create_parsed_objection(
                        title=current_issue,
                        argument="\n".join(current_argument),
                        severity=current_severity,
                        target_type=target_type,
                        target_id=target_id,
                    )
                    if created:
                        created_objections.append(created)

                # Determine severity based on section
                if "MAJOR" in line.upper():
                    current_severity = ObjectionSeverity.MAJOR
                else:
                    current_severity = ObjectionSeverity.MAJOR  # Default for numbered issues

                current_issue = line.replace("###", "").strip()
                current_argument = []

            elif current_issue and line:
                current_argument.append(line)

        # Save last issue
        if current_issue and current_severity:
            created = self._create_parsed_objection(
                title=current_issue,
                argument="\n".join(current_argument),
                severity=current_severity,
                target_type=target_type,
                target_id=target_id,
            )
            if created:
                created_objections.append(created)

        self._refresh_cache()
        return created_objections

    def _create_parsed_objection(
        self,
        title: str,
        argument: str,
        severity: ObjectionSeverity,
        target_type: str,
        target_id: str,
    ) -> dict | None:
        """Create a single parsed objection.

        Returns None if objection already exists for this target.
        """
        # Check for duplicates
        existing = [
            o for o in self._objections_cache
            if o.get("target_id") == target_id
            and o.get("title", "").lower() == title.lower()
        ]

        if existing:
            return None  # Don't create duplicate

        return self.add_objection(
            target_type=target_type,
            target_id=target_id,
            title=title[:200],  # Truncate long titles
            argument=argument,
            category=ObjectionCategory.OTHER,
            severity=severity,
            raised_by="RED_TEAM",
        )
