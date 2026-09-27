from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Engine, func, insert, select, update

from . import models


class FrozenRecordError(ValueError):
    pass


class IdentityConflictError(ValueError):
    pass


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _uuid() -> str:
    return str(uuid.uuid4())


def _row(row: Any) -> dict[str, Any] | None:
    return dict(row._mapping) if row is not None else None


class ResearchRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def _insert(self, table, values: dict[str, Any]) -> dict[str, Any]:
        with self.engine.begin() as connection:
            return _row(connection.execute(insert(table).values(**values).returning(table)).one())  # type: ignore[return-value]

    def _get(self, table, column, value: str) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            return _row(connection.execute(select(table).where(column == value)).first())

    def create_project(self, name: str, domain: str = "", seed_question: str = "", description: str = "", *, legacy_id: str | None = None) -> dict[str, Any]:
        if legacy_id:
            existing = self.get_project_by_legacy_id(legacy_id)
            if existing:
                return existing
        return self._insert(models.projects, {
            "project_id": _uuid(), "legacy_id": legacy_id, "name": name, "domain": domain,
            "seed_question": seed_question, "description": description,
        })

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        return self._get(models.projects, models.projects.c.project_id, project_id)

    def get_project_by_legacy_id(self, legacy_id: str) -> dict[str, Any] | None:
        return self._get(models.projects, models.projects.c.legacy_id, legacy_id)

    def create_research_question(self, project_id: str, question_text: str, *, idea_id: str | None = None, scope: dict | None = None) -> dict[str, Any]:
        return self._insert(models.research_questions, {
            "research_question_id": _uuid(), "project_id": project_id, "idea_id": idea_id,
            "question_text": question_text, "scope": scope or {},
        })

    def create_hypothesis(
        self, project_id: str, claim: str, rationale: str = "", predicted_effect: str = "",
        falsification_conditions: list[str] | None = None, *, hypothesis_id: str | None = None,
        parent_hypothesis_id: str | None = None,
    ) -> dict[str, Any]:
        identity = hypothesis_id or _uuid()
        existing = self._get(models.hypotheses, models.hypotheses.c.hypothesis_id, identity)
        if existing:
            meaning = (existing["project_id"], existing["claim"], existing["predicted_effect"], existing["falsification_conditions"])
            proposed = (project_id, claim, predicted_effect, falsification_conditions or [])
            if meaning != proposed:
                raise IdentityConflictError("hypothesis_id cannot be reused for different scientific meaning")
            return existing
        return self._insert(models.hypotheses, {
            "hypothesis_id": identity, "project_id": project_id, "parent_hypothesis_id": parent_hypothesis_id,
            "claim": claim, "rationale": rationale, "predicted_effect": predicted_effect,
            "falsification_conditions": falsification_conditions or [],
        })

    @staticmethod
    def _protocol_content(values: dict[str, Any]) -> dict[str, Any]:
        fields = ("research_question_id", "hypothesis_id", "design", "measurement_plan", "data_split_policy", "analysis_plan", "stopping_rules", "exclusion_rules", "resource_budget")
        return {field: values.get(field) for field in fields}

    def create_protocol_version(
        self, project_id: str, research_question_id: str, hypothesis_id: str | None,
        *, design: dict, measurement_plan: dict, data_split_policy: dict, analysis_plan: dict,
        stopping_rules: dict, exclusion_rules: dict, resource_budget: dict, status: str = "DRAFT",
        version: int | None = None,
    ) -> dict[str, Any]:
        if version is None:
            with self.engine.connect() as connection:
                version = (connection.execute(select(func.max(models.protocol_versions.c.version)).where(models.protocol_versions.c.project_id == project_id)).scalar() or 0) + 1
        values = {
            "protocol_version_id": _uuid(), "project_id": project_id, "research_question_id": research_question_id,
            "hypothesis_id": hypothesis_id, "version": version, "status": status, "design": design,
            "measurement_plan": measurement_plan, "data_split_policy": data_split_policy, "analysis_plan": analysis_plan,
            "stopping_rules": stopping_rules, "exclusion_rules": exclusion_rules, "resource_budget": resource_budget,
        }
        values["content_hash"] = canonical_hash(self._protocol_content(values))
        return self._insert(models.protocol_versions, values)

    def get_protocol(self, protocol_version_id: str) -> dict[str, Any] | None:
        return self._get(models.protocol_versions, models.protocol_versions.c.protocol_version_id, protocol_version_id)

    def freeze_protocol(self, protocol_version_id: str) -> dict[str, Any]:
        protocol = self.get_protocol(protocol_version_id)
        if not protocol:
            raise KeyError(protocol_version_id)
        if protocol["status"] == "FROZEN":
            return protocol
        with self.engine.begin() as connection:
            row = connection.execute(
                update(models.protocol_versions).where(models.protocol_versions.c.protocol_version_id == protocol_version_id)
                .values(status="FROZEN", frozen_at=datetime.now(timezone.utc)).returning(models.protocol_versions)
            ).one()
        return _row(row)  # type: ignore[return-value]

    def update_protocol(self, protocol_version_id: str, **changes: Any) -> dict[str, Any]:
        protocol = self.get_protocol(protocol_version_id)
        if not protocol:
            raise KeyError(protocol_version_id)
        if protocol["status"] == "FROZEN":
            raise FrozenRecordError("frozen protocols are immutable; create a new version")
        allowed = {"design", "measurement_plan", "data_split_policy", "analysis_plan", "stopping_rules", "exclusion_rules", "resource_budget", "status"}
        invalid = set(changes) - allowed
        if invalid:
            raise ValueError(f"unsupported protocol fields: {sorted(invalid)}")
        merged = {**protocol, **changes}
        changes["content_hash"] = canonical_hash(self._protocol_content(merged))
        with self.engine.begin() as connection:
            return _row(connection.execute(update(models.protocol_versions).where(models.protocol_versions.c.protocol_version_id == protocol_version_id).values(**changes).returning(models.protocol_versions)).one())  # type: ignore[return-value]

    def revise_protocol(self, protocol_version_id: str, **changes: Any) -> dict[str, Any]:
        previous = self.get_protocol(protocol_version_id)
        if not previous:
            raise KeyError(protocol_version_id)
        content = {field: previous[field] for field in ("design", "measurement_plan", "data_split_policy", "analysis_plan", "stopping_rules", "exclusion_rules", "resource_budget")}
        content.update(changes)
        return self.create_protocol_version(
            previous["project_id"], previous["research_question_id"], previous["hypothesis_id"], **content,
        )

    def create_experiment_spec(
        self, *, project_id: str, protocol_version_id: str, hypothesis_id: str, objective: str,
        command: list[str], workspace: str, metrics_contract: dict, controls: dict, resource_limits: dict,
        execution_profile: str, code_revision: str, data_manifest_hash: str | None, declared_seed: int | None,
    ) -> dict[str, Any]:
        scientific = {
            "protocol_version_id": protocol_version_id, "hypothesis_id": hypothesis_id, "objective": objective,
            "command": command, "workspace": workspace, "metrics_contract": metrics_contract, "controls": controls,
            "resource_limits": resource_limits, "execution_profile": execution_profile, "code_revision": code_revision,
            "data_manifest_hash": data_manifest_hash, "declared_seed": declared_seed,
        }
        spec_hash = canonical_hash(scientific)
        idempotency_key = canonical_hash([protocol_version_id, spec_hash, code_revision, data_manifest_hash or "", declared_seed])
        with self.engine.connect() as connection:
            existing = connection.execute(select(models.experiment_specs).where(models.experiment_specs.c.idempotency_key == idempotency_key)).first()
        if existing:
            return _row(existing)  # type: ignore[return-value]
        return self._insert(models.experiment_specs, {"experiment_spec_id": _uuid(), "project_id": project_id, **scientific, "spec_hash": spec_hash, "idempotency_key": idempotency_key})

    def get_experiment_spec_by_idempotency_key(self, key: str) -> dict[str, Any] | None:
        return self._get(models.experiment_specs, models.experiment_specs.c.idempotency_key, key)

    def get_experiment_spec(self, experiment_spec_id: str) -> dict[str, Any] | None:
        return self._get(models.experiment_specs, models.experiment_specs.c.experiment_spec_id, experiment_spec_id)

    def create_experiment_run(self, experiment_spec_id: str, *, attempt: int, status: str, metrics: dict | None = None, return_code: int | None = None, error_type: str | None = None, external_run_id: str | None = None, runtime_metadata: dict | None = None) -> dict[str, Any]:
        with self.engine.connect() as connection:
            existing = connection.execute(select(models.experiment_runs).where(models.experiment_runs.c.experiment_spec_id == experiment_spec_id, models.experiment_runs.c.attempt == attempt)).first()
        if existing:
            return _row(existing)  # type: ignore[return-value]
        return self._insert(models.experiment_runs, {
            "experiment_run_id": _uuid(), "experiment_spec_id": experiment_spec_id, "attempt": attempt,
            "status": status, "metrics": metrics or {}, "return_code": return_code, "error_type": error_type,
            "external_run_id": external_run_id, "runtime_metadata": runtime_metadata or {},
        })

    def get_experiment_run(self, experiment_run_id: str) -> dict[str, Any] | None:
        return self._get(models.experiment_runs, models.experiment_runs.c.experiment_run_id, experiment_run_id)

    def list_experiment_runs(self, experiment_spec_id: str) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            return [dict(row._mapping) for row in connection.execute(
                select(models.experiment_runs).where(models.experiment_runs.c.experiment_spec_id == experiment_spec_id).order_by(models.experiment_runs.c.attempt)
            )]

    def update_experiment_run(self, experiment_run_id: str, **changes: Any) -> dict[str, Any]:
        allowed = {"status", "return_code", "metrics", "error_type", "external_run_id", "runtime_metadata", "completed_at"}
        values = {key: value for key, value in changes.items() if key in allowed}
        with self.engine.begin() as connection:
            row = connection.execute(update(models.experiment_runs).where(models.experiment_runs.c.experiment_run_id == experiment_run_id).values(**values).returning(models.experiment_runs)).one()
        return _row(row)  # type: ignore[return-value]

    def create_analysis_run(self, project_id: str, protocol_version_id: str, input_experiment_run_ids: list[str], *, analysis_code_revision: str, analysis_plan_hash: str, status: str, results: dict, uncertainty: dict | None = None, limitations: dict | None = None, artifact_refs: list | None = None) -> dict[str, Any]:
        return self._insert(models.analysis_runs, {
            "analysis_run_id": _uuid(), "project_id": project_id, "protocol_version_id": protocol_version_id,
            "input_experiment_run_ids": input_experiment_run_ids, "analysis_code_revision": analysis_code_revision,
            "analysis_plan_hash": analysis_plan_hash, "status": status, "results": results,
            "uncertainty": uncertainty or {}, "limitations": limitations or {}, "artifact_refs": artifact_refs or [],
        })

    def create_evidence_item(self, project_id: str, *, evidence_type: str, source_ref: dict, content_summary: str, validity_status: str) -> dict[str, Any]:
        content_hash = canonical_hash({"source_ref": source_ref, "content_summary": content_summary, "validity_status": validity_status})
        return self._insert(models.evidence_items, {
            "evidence_id": _uuid(), "project_id": project_id, "evidence_type": evidence_type, "source_ref": source_ref,
            "content_summary": content_summary, "validity_status": validity_status, "content_hash": content_hash,
        })

    def create_claim(self, project_id: str, claim_type: str, claim_text: str, *, scope: dict, created_by_role: str, status: str = "DRAFT", version: int = 1) -> dict[str, Any]:
        return self._insert(models.claims, {
            "claim_id": _uuid(), "project_id": project_id, "claim_type": claim_type, "claim_text": claim_text,
            "scope": scope, "created_by_role": created_by_role, "status": status, "version": version,
        })

    def link_claim_evidence(self, claim_id: str, evidence_id: str, relation: str, rationale: str, created_by_role: str, review_status: str = "UNVERIFIED") -> dict[str, Any]:
        return self._insert(models.claim_evidence_links, {
            "claim_id": claim_id, "evidence_id": evidence_id, "relation": relation, "rationale": rationale,
            "created_by_role": created_by_role, "review_status": review_status,
        })

    def get_claim_provenance(self, claim_id: str) -> dict[str, Any]:
        claim = self._get(models.claims, models.claims.c.claim_id, claim_id)
        if not claim:
            raise KeyError(claim_id)
        with self.engine.connect() as connection:
            links = [dict(row._mapping) for row in connection.execute(select(models.claim_evidence_links).where(models.claim_evidence_links.c.claim_id == claim_id))]
            evidence = [dict(row._mapping) for row in connection.execute(select(models.evidence_items).where(models.evidence_items.c.evidence_id.in_([item["evidence_id"] for item in links])))] if links else []
            analysis_ids = [item["source_ref"].get("analysis_run_id") for item in evidence if item["source_ref"].get("analysis_run_id")]
            analyses = [dict(row._mapping) for row in connection.execute(select(models.analysis_runs).where(models.analysis_runs.c.analysis_run_id.in_(analysis_ids)))] if analysis_ids else []
            run_ids = [run_id for analysis in analyses for run_id in analysis["input_experiment_run_ids"]]
            runs = [dict(row._mapping) for row in connection.execute(select(models.experiment_runs).where(models.experiment_runs.c.experiment_run_id.in_(run_ids)))] if run_ids else []
            spec_ids = [run["experiment_spec_id"] for run in runs]
            specs = [dict(row._mapping) for row in connection.execute(select(models.experiment_specs).where(models.experiment_specs.c.experiment_spec_id.in_(spec_ids)))] if spec_ids else []
            protocol_ids = list({analysis["protocol_version_id"] for analysis in analyses} | {spec["protocol_version_id"] for spec in specs})
            protocols = [dict(row._mapping) for row in connection.execute(select(models.protocol_versions).where(models.protocol_versions.c.protocol_version_id.in_(protocol_ids)))] if protocol_ids else []
        return {"claim": claim, "links": links, "evidence": evidence, "analyses": analyses, "experiment_runs": runs, "experiment_specs": specs, "protocols": protocols}

    def create_objection(self, project_id: str, target_type: str, target_id: str, category: str, severity: str, title: str, argument: str, *, raised_by_role: str, supporting_evidence_ids: list[str] | None = None, status: str = "OPEN") -> dict[str, Any]:
        return self._insert(models.objections, {
            "objection_id": _uuid(), "project_id": project_id, "target_type": target_type, "target_id": target_id,
            "category": category, "severity": severity, "title": title, "argument": argument,
            "supporting_evidence_ids": supporting_evidence_ids or [], "status": status, "raised_by_role": raised_by_role,
        })

    def get_objection(self, objection_id: str) -> dict[str, Any] | None:
        return self._get(models.objections, models.objections.c.objection_id, objection_id)

    def list_objections(self, project_id: str, *, status: str | None = None, severity: str | None = None) -> list[dict[str, Any]]:
        statement = select(models.objections).where(models.objections.c.project_id == project_id)
        if status:
            statement = statement.where(models.objections.c.status == status)
        if severity:
            statement = statement.where(models.objections.c.severity == severity)
        with self.engine.connect() as connection:
            return [dict(row._mapping) for row in connection.execute(statement.order_by(models.objections.c.created_at))]

    def update_objection(self, objection_id: str, **changes: Any) -> dict[str, Any]:
        allowed = {"status", "resolution_type", "resolution_reason"}
        values = {key: value for key, value in changes.items() if key in allowed}
        if not values:
            current = self.get_objection(objection_id)
            if not current:
                raise KeyError(objection_id)
            return current
        with self.engine.begin() as connection:
            row = connection.execute(update(models.objections).where(models.objections.c.objection_id == objection_id).values(**values).returning(models.objections)).one()
        return _row(row)  # type: ignore[return-value]

    def create_approval(self, project_id: str, approval_type: str, target_type: str, target_id: str, target_hash: str, *, status: str = "PENDING", approved_by: str | None = None, budget_authorized: dict | None = None) -> dict[str, Any]:
        return self._insert(models.approvals, {
            "approval_id": _uuid(), "project_id": project_id, "approval_type": approval_type,
            "target_type": target_type, "target_id": target_id, "target_hash": target_hash,
            "status": status, "approved_by": approved_by, "budget_authorized": budget_authorized,
        })

    def approval_authorizes(self, approval_id: str, target_id: str, target_hash: str) -> bool:
        approval = self._get(models.approvals, models.approvals.c.approval_id, approval_id)
        return bool(approval and approval["status"] == "APPROVED" and approval["target_id"] == target_id and approval["target_hash"] == target_hash)

    def create_decision(self, project_id: str, decision_type: str, decision: str, *, policy_version: str, gate_results: dict | None = None, reason_refs: list | None = None) -> dict[str, Any]:
        return self._insert(models.decisions, {
            "decision_id": _uuid(), "project_id": project_id, "decision_type": decision_type,
            "decision": decision, "gate_results": gate_results or {}, "reason_refs": reason_refs or [],
            "policy_version": policy_version,
        })

    def get_decision(self, decision_id: str) -> dict[str, Any] | None:
        return self._get(models.decisions, models.decisions.c.decision_id, decision_id)

    def get_latest_decision(self, project_id: str, decision_type: str) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            return _row(connection.execute(
                select(models.decisions).where(models.decisions.c.project_id == project_id, models.decisions.c.decision_type == decision_type).order_by(models.decisions.c.created_at.desc()).limit(1)
            ).first())

    def register_artifact(self, *, artifact_type: str, uri: str, sha256: str, size_bytes: int, project_id: str | None = None, mime_type: str | None = None, metadata: dict | None = None, created_by_task_id: str | None = None) -> dict[str, Any]:
        with self.engine.connect() as connection:
            existing = connection.execute(select(models.artifacts).where(models.artifacts.c.uri == uri)).first()
        if existing:
            row = _row(existing)
            if row and row["sha256"] != sha256:
                raise IdentityConflictError("artifact URI already registered with different content")
            return row  # type: ignore[return-value]
        return self._insert(models.artifacts, {
            "artifact_id": _uuid(), "project_id": project_id, "artifact_type": artifact_type, "uri": uri,
            "sha256": sha256, "mime_type": mime_type, "size_bytes": size_bytes, "metadata": metadata or {},
            "created_by_task_id": created_by_task_id,
        })

    def get_artifact(self, artifact_id: str) -> dict[str, Any] | None:
        return self._get(models.artifacts, models.artifacts.c.artifact_id, artifact_id)

    def list_artifacts_for_project(self, project_id: str) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            return [dict(row._mapping) for row in connection.execute(select(models.artifacts).where(models.artifacts.c.project_id == project_id).order_by(models.artifacts.c.created_at))]

    def legacy_row_imported(self, source_hash: str, source_table: str, source_row_id: str) -> bool:
        with self.engine.connect() as connection:
            return connection.execute(select(models.legacy_imports.c.legacy_import_id).where(
                models.legacy_imports.c.source_hash == source_hash,
                models.legacy_imports.c.source_table == source_table,
                models.legacy_imports.c.source_row_id == source_row_id,
            )).first() is not None

    def record_legacy_import(self, source_hash: str, source_table: str, source_row_id: str, target_type: str, target_id: str) -> None:
        self._insert(models.legacy_imports, {
            "legacy_import_id": _uuid(), "source_hash": source_hash, "source_table": source_table,
            "source_row_id": source_row_id, "target_type": target_type, "target_id": target_id,
        })
