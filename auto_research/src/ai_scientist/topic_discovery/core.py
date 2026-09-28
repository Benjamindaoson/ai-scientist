from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Protocol

from ai_scientist.opportunity_intelligence import OpportunityRepository
from ai_scientist.opportunity_intelligence import models as opportunity_models
from ai_scientist.opportunity_intelligence.repository import new_id


def normalize(value: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", value.lower())
    synonyms = {
        "closed-loop": "closedloop", "closed": "closedloop", "loop": "closedloop",
        "action-conditioned": "actionconditioned", "action": "actionconditioned", "conditioned": "actionconditioned",
        "failures": "failure", "fails": "failure", "failing": "failure",
        "predicts": "predict", "predicted": "predict", "identified": "identify", "identifies": "identify",
        "policies": "policy", "tasks": "task", "models": "model",
        "vision": "vla", "language": "vla", "vla": "vla",
    }
    normalized = [synonyms.get(token, token) for token in tokens]
    return " ".join(dict.fromkeys(normalized))


def token_set(value: str) -> set[str]:
    return set(normalize(value).split()) - {"a", "an", "the", "is", "are", "does", "do", "can", "be", "before", "under", "than"}


def jaccard(left: str, right: str) -> float:
    a, b = token_set(left), token_set(right)
    return len(a & b) / max(1, len(a | b))


def claim_coverage(claim: str, source: str) -> float:
    required, observed = token_set(claim), token_set(source)
    return len(required & observed) / max(1, len(required))


@dataclass(frozen=True)
class CandidateIdea:
    idea_id: str
    title: str
    current_belief: str
    proposed_challenge: str
    scientific_question: str
    falsifiable_claim: str
    why_now: str
    origin_signal_ids: tuple[str, ...]
    expected_contribution_type: str
    possible_target_venues: tuple[str, ...]
    cheap_falsifier: str
    main_risk: str
    generation_model: str = ""
    prompt_hash: str = ""
    input_signal_ids: tuple[str, ...] = ()
    literature_context_ids: tuple[str, ...] = ()
    reasoning_summary: str = ""
    generation_timestamp: str = ""

    @property
    def semantic_fingerprint(self) -> str:
        return hashlib.sha256(normalize(f"{self.scientific_question} {self.falsifiable_claim}").encode()).hexdigest()


@dataclass(frozen=True)
class ResearchProgram:
    name: str
    domains: tuple[str, ...]
    adjacent_domains: tuple[str, ...]
    candidate_batch_size: int = 20

    @classmethod
    def production_default(cls) -> "ResearchProgram":
        return cls(
            "Embodied Intelligence Topic Discovery",
            ("Embodied AI", "Robot Learning", "Vision-Language-Action", "World Models", "Multimodal Agents", "Agentic Robotics"),
            ("machine learning", "computer vision", "reinforcement learning", "control", "multimodal learning", "NLP/agents"),
        )


class GapDecision(str, Enum):
    KILLED_BY_PRIOR = "KILLED_BY_PRIOR"
    REFRAME_REQUIRED = "REFRAME_REQUIRED"
    NOVELTY_UNCERTAIN = "NOVELTY_UNCERTAIN"
    NOVELTY_SURVIVES_AUDIT = "NOVELTY_SURVIVES_AUDIT"


@dataclass(frozen=True)
class NoveltyDecision:
    decision: GapDecision
    killing_paper_id: str | None = None
    overlap: dict[str, bool] = field(default_factory=dict)
    required_expansion: tuple[str, ...] = ()
    reason: str = ""


class NoveltyJudge:
    def __init__(self, minimum_candidates: int = 20, kill_threshold: float = 0.66):
        self.minimum_candidates = minimum_candidates
        self.kill_threshold = kill_threshold

    def decide(self, idea: CandidateIdea, priors: list[dict], *, search_complete: bool) -> NoveltyDecision:
        """Cheap lexical screening only; never grants final novelty."""
        for prior in priors:
            content = f"{prior.get('title', '')} {prior.get('abstract', '')} {prior.get('claim_text', '')}"
            question_overlap = claim_coverage(idea.scientific_question, content)
            claim_overlap = claim_coverage(idea.falsifiable_claim, content)
            overlap = {
                "same_question": question_overlap >= self.kill_threshold,
                "same_claim": claim_overlap >= self.kill_threshold,
                "same_method": bool(token_set(idea.falsifiable_claim) & {"uncertainty", "causal", "calibration", "world", "model"} <= token_set(content)),
                "same_metric": False, "same_setting": "vla" in token_set(content), "same_conclusion": claim_overlap >= 0.75,
            }
            if overlap["same_question"] and overlap["same_claim"] and prior.get("source_chunk_ids"):
                return NoveltyDecision(GapDecision.KILLED_BY_PRIOR, prior.get("paper_id"), overlap, reason="A source-backed prior covers both the scientific question and core claim.")
        if not search_complete or len(priors) < self.minimum_candidates:
            return NoveltyDecision(
                GapDecision.NOVELTY_UNCERTAIN,
                required_expansion=("wider_years", "adjacent_fields", "external_corpus", "citation_graph", "exact_claims", "preprints_and_journals"),
                reason="Documented coverage is insufficient to let novelty survive audit.",
            )
        return NoveltyDecision(GapDecision.NOVELTY_UNCERTAIN, reason="Cheap screening found no obvious overlap; structured full-text audit is required.")

    def deep_decide(self, idea: CandidateIdea, audits: list[dict], *, search_complete: bool) -> NoveltyDecision:
        dimensions = (
            "scientific_question_overlap", "claim_overlap", "assumption_overlap", "method_overlap",
            "measurement_overlap", "setting_overlap", "conclusion_overlap",
        )
        if not search_complete or not audits:
            return NoveltyDecision(GapDecision.NOVELTY_UNCERTAIN, reason="Independent search coverage is incomplete.")
        for audit in audits:
            if audit.get("full_text_status") != "AVAILABLE" or not audit.get("source_spans"):
                return NoveltyDecision(GapDecision.NOVELTY_UNCERTAIN, reason="A dangerous prior lacks legal full text or source spans.")
            if any(audit.get(name) not in {"TRUE", "FALSE", "PARTIAL", "UNKNOWN"} for name in dimensions):
                return NoveltyDecision(GapDecision.NOVELTY_UNCERTAIN, reason="Structured scientific-overlap fields are incomplete.")
            if audit.get("scientific_question_overlap") == "TRUE" and audit.get("claim_overlap") == "TRUE":
                return NoveltyDecision(GapDecision.KILLED_BY_PRIOR, audit.get("paper_id"), reason="Full-text evidence covers the question and claim.")
            if audit.get("claim_overlap") == "PARTIAL" and audit.get("measurement_overlap") in {"TRUE", "PARTIAL"}:
                return NoveltyDecision(GapDecision.REFRAME_REQUIRED, audit.get("paper_id"), reason="A prior covers the broad claim and measurement; a narrower reframe is required.")
            if any(audit.get(name) == "UNKNOWN" for name in dimensions):
                return NoveltyDecision(GapDecision.NOVELTY_UNCERTAIN, reason="At least one deep-comparison dimension remains unknown.")
        return NoveltyDecision(GapDecision.NOVELTY_SURVIVES_AUDIT, reason="Independent structured full-text audits found no prior covering the question and claim.")


class IdeaDeduplicator:
    def __init__(self, repository: OpportunityRepository, threshold: float = 0.78):
        self.repository = repository
        self.threshold = threshold

    def remember_killed(self, idea: CandidateIdea, *, kill_reason: str, killing_papers: list[str], failed_gate: str) -> dict:
        existing = self.repository.get_lineage(idea.idea_id)
        if existing:
            with self.repository.engine.begin() as connection:
                row = connection.execute(opportunity_models.idea_lineage.update().where(
                    opportunity_models.idea_lineage.c.idea_id == idea.idea_id
                ).values(status="KILLED", kill_reason=kill_reason, killing_papers=killing_papers, failed_gate=failed_gate).returning(opportunity_models.idea_lineage)).one()
            return dict(row._mapping)
        return self.repository.insert(
            opportunity_models.idea_lineage, idea_lineage_id=new_id(), idea_id=idea.idea_id, parent_idea_id=None,
            generation=0, origin_signal_ids=list(idea.origin_signal_ids), normalized_question=normalize(idea.scientific_question),
            semantic_fingerprint=idea.semantic_fingerprint, reframe_reason=None, kill_reason=kill_reason,
            killing_papers=killing_papers, failed_gate=failed_gate, status="KILLED", material_change_refs=[],
        )

    def is_duplicate(self, idea: CandidateIdea) -> bool:
        normalized_question = normalize(idea.scientific_question)
        for killed in self.repository.list_killed_lineage():
            if killed["semantic_fingerprint"] == idea.semantic_fingerprint:
                return True
            if jaccard(normalized_question, killed["normalized_question"]) >= self.threshold:
                return True
        return False

    def record_reframe(self, parent: CandidateIdea, child: CandidateIdea, reason: str, material_change_refs: list[str] | None = None) -> dict:
        if jaccard(parent.scientific_question, child.scientific_question) >= 0.90 and not material_change_refs:
            raise ValueError("reframe must materially change the scientific question or cite new conditions")
        parent_row = self.repository.get_lineage(parent.idea_id)
        return self.repository.insert(
            opportunity_models.idea_lineage, idea_lineage_id=new_id(), idea_id=child.idea_id, parent_idea_id=parent.idea_id,
            generation=(parent_row["generation"] + 1 if parent_row else 1), origin_signal_ids=list(child.origin_signal_ids),
            normalized_question=normalize(child.scientific_question), semantic_fingerprint=child.semantic_fingerprint,
            reframe_reason=reason, kill_reason=None, killing_papers=[], failed_gate=None, status="CANDIDATE",
            material_change_refs=material_change_refs or [],
        )


@dataclass
class GateEvidence:
    scientific_question: str | None = None
    falsifiable_claim: str | None = None
    scout_retrieval_run_id: str | None = None
    reviewer_retrieval_run_id: str | None = None
    no_covering_prior: bool = False
    closest_prior_work: list[dict] | None = None
    adjacent_field_search: bool = False
    citation_expansion: bool = False
    gap_statement: str | None = None
    significance: dict | None = None
    critical_questions: list[dict] | None = None
    data: dict | None = None
    method: dict | None = None
    engineering: dict | None = None
    compute: dict | None = None
    time_estimate: dict | None = None
    killer_experiment: dict | None = None
    venue_fit: dict | None = None
    deadline: datetime | None = None
    p90_completion_days: int = 0
    safety_buffer_days: int = 0
    future_cycle_target: bool = False
    reviewer_attacks: list[str] | None = None
    unresolved_fatal_objections: tuple[str, ...] = ()
    generation_provenance: dict | None = None
    deep_audit: list[dict] | None = None
    coherence: dict | None = None
    benchmark_status: str | None = None

    @classmethod
    def complete(cls) -> "GateEvidence":
        evidence = cls(
            scientific_question="Does a measurable relation distinguish two competing scientific explanations?",
            falsifiable_claim="The relation improves failure identification by at least a declared effect under matched controls.",
            scout_retrieval_run_id="scout-run", reviewer_retrieval_run_id="reviewer-run", no_covering_prior=True,
            closest_prior_work=[{"paper_id": "p1", "source_chunk_ids": ["c1"]}], adjacent_field_search=True,
            citation_expansion=True, gap_statement="Existing work does not test the declared relation under matched controls.",
            significance={name: {"pass": True, "reason": name, "evidence_refs": ["e1"], "assessor": "reviewer"} for name in ("fundamental", "surprising", "broad", "actionable", "cheap_to_falsify", "hard_to_explain_away", "defensible_novelty", "value_over_cost")},
            critical_questions=[{"question": str(index), "answer": f"resolved {index}", "evidence_refs": ["e1"], "counterarguments": ["counter"], "confidence_class": "MEDIUM", "unresolved": [], "status": "RESOLVED", "answer_model": "codex", "prompt_hash": f"{index:064x}"} for index in range(15)],
            data={"status": "DATA_READY", "target_variable": "outcome", "target_variable_available": True, "official_docs": ["doc"], "actual_size": "small", "download_method": "command", "license": "documented", "schema": ["outcome"], "metadata_load": {"status": "SUCCEEDED", "command": "loader", "artifact": "metadata.json"}},
            method={"research_type": "MEASUREMENT", "baselines": ["calibration"], "controls": ["matched success"], "metrics": ["AUROC"], "analysis": "paired bootstrap"},
            engineering={"status": "READY", "command": "python smoke.py", "artifact": "smoke.json", "metric_computed": "AUROC"},
            compute={"candidate_id": "candidate", "assumptions": ["sample count"], "calculation": "samples/rate", "best_case": {"gpu_hours": 2}, "expected": {"gpu_hours": 8}, "worst_reasonable": {"gpu_hours": 24}, "vram_gb": 24, "storage_gb": 50},
            time_estimate={"candidate_id": "candidate", "assumptions": ["loader ready"], "calculation": "sum tasks", "best_days": 7, "expected_days": 14, "p90_days": 21},
            killer_experiment={"candidate_id": "candidate", "data": "public", "sample_size": 200, "baseline": "calibration", "control": "matched success", "metric": "AUROC", "statistical_test": "paired bootstrap", "runtime_hours": 12, "kill_condition": "no improvement"},
            venue_fit={"primary": "ICLR", "secondary": "CoRL", "workshop": "robot learning", "scope_evidence": "official CFP"},
            future_cycle_target=True, reviewer_attacks=[f"attack {index}" for index in range(5)],
            generation_provenance={"generation_model": "codex", "prompt_hash": "a" * 64, "input_signal_ids": ["s1"], "literature_context_ids": ["p1"], "reasoning_summary": "evidence-backed", "generation_timestamp": "2026-01-01T00:00:00Z"},
            deep_audit=[{"paper_version_id": "v1", "full_text_status": "AVAILABLE", "source_chunk_ids": ["c1"], "source_spans": [{"section": "method", "text": "evidence"}], "scientific_question_overlap": "FALSE", "claim_overlap": "FALSE", "assumption_overlap": "PARTIAL", "method_overlap": "PARTIAL", "measurement_overlap": "FALSE", "setting_overlap": "PARTIAL", "conclusion_overlap": "FALSE"}],
            coherence={"pass": True, "question_construct": "relation", "claim_construct": "relation", "primary_measurement": "relation", "outcome": "failure", "baseline": "baseline"},
        )
        return evidence


@dataclass(frozen=True)
class TopicVerdict:
    ready: bool
    status: str
    missing: tuple[str, ...]
    deadline_slack_days: int | None = None


class TopicReadinessGate:
    def __init__(self, now: Callable[[], datetime] | None = None):
        self.now = now or (lambda: datetime.now(timezone.utc))

    def evaluate(self, evidence: GateEvidence) -> TopicVerdict:
        significance_keys = {"fundamental", "surprising", "broad", "actionable", "cheap_to_falsify", "hard_to_explain_away", "defensible_novelty", "value_over_cost"}
        significance_ok = bool(evidence.significance and significance_keys <= set(evidence.significance) and all(
            isinstance(evidence.significance[name], dict)
            and evidence.significance[name].get("pass") is True
            and evidence.significance[name].get("reason")
            and evidence.significance[name].get("evidence_refs")
            and evidence.significance[name].get("assessor") == "reviewer"
            for name in significance_keys
        ))
        critical_ok = bool(evidence.critical_questions and len(evidence.critical_questions) >= 15 and all(
            row.get("status") == "RESOLVED" and row.get("answer") and row.get("evidence_refs")
            and row.get("counterarguments") and row.get("confidence_class") in {"LOW", "MEDIUM", "HIGH"}
            and not row.get("unresolved") and row.get("answer_model") and row.get("prompt_hash")
            for row in evidence.critical_questions
        ))
        data_ok = bool(evidence.data and evidence.data.get("status") == "DATA_READY"
                       and evidence.data.get("target_variable_available") is True
                       and evidence.data.get("target_variable") and evidence.data.get("schema")
                       and evidence.data.get("metadata_load", {}).get("status") == "SUCCEEDED"
                       and evidence.data.get("metadata_load", {}).get("command")
                       and evidence.data.get("metadata_load", {}).get("artifact"))
        provenance_ok = bool(evidence.generation_provenance and evidence.generation_provenance.get("generation_model") not in {None, "", "static", "template"}
                             and evidence.generation_provenance.get("prompt_hash") and evidence.generation_provenance.get("input_signal_ids")
                             and evidence.generation_provenance.get("literature_context_ids") and evidence.generation_provenance.get("reasoning_summary")
                             and evidence.generation_provenance.get("generation_timestamp"))
        deep_audit_ok = bool(evidence.deep_audit and all(row.get("full_text_status") == "AVAILABLE" and row.get("source_spans") for row in evidence.deep_audit))
        required = {
            "scientific_question": bool(evidence.scientific_question and "?" in evidence.scientific_question),
            "falsifiable_claim": bool(evidence.falsifiable_claim),
            "scout_novelty_audit": bool(evidence.scout_retrieval_run_id),
            "reviewer_novelty_audit": bool(evidence.reviewer_retrieval_run_id),
            "independent_retrieval_runs": bool(evidence.scout_retrieval_run_id and evidence.reviewer_retrieval_run_id and evidence.scout_retrieval_run_id != evidence.reviewer_retrieval_run_id),
            "no_covering_prior": evidence.no_covering_prior,
            "closest_prior_work": bool(evidence.closest_prior_work and all(row.get("source_chunk_ids") for row in evidence.closest_prior_work)),
            "adjacent_field_search": evidence.adjacent_field_search,
            "citation_expansion": evidence.citation_expansion,
            "gap_statement": bool(evidence.gap_statement),
            "generation_provenance": provenance_ok,
            "deep_audit": deep_audit_ok,
            "significance": significance_ok,
            "critical_questions": critical_ok,
            "data": data_ok,
            "method": bool(evidence.method and evidence.method.get("baselines") and evidence.method.get("controls") and evidence.method.get("metrics")),
            "engineering": bool(evidence.engineering and evidence.engineering.get("status") == "READY" and evidence.engineering.get("command") and evidence.engineering.get("artifact") and evidence.engineering.get("metric_computed")),
            "compute": bool(evidence.compute and evidence.compute.get("candidate_id") and evidence.compute.get("assumptions") and evidence.compute.get("calculation") and all(key in evidence.compute for key in ("best_case", "expected", "worst_reasonable"))),
            "time_estimate": bool(evidence.time_estimate and evidence.time_estimate.get("candidate_id") and evidence.time_estimate.get("assumptions") and evidence.time_estimate.get("calculation") and evidence.time_estimate.get("p90_days")),
            "killer_experiment": bool(evidence.killer_experiment and evidence.killer_experiment.get("candidate_id") and evidence.killer_experiment.get("kill_condition")),
            "coherence": bool(evidence.coherence and evidence.coherence.get("pass") is True),
            "venue_fit": bool(evidence.venue_fit and evidence.venue_fit.get("primary") and evidence.venue_fit.get("scope_evidence")),
            "reviewer_attacks": bool(evidence.reviewer_attacks and len(evidence.reviewer_attacks) >= 5),
            "no_unresolved_fatal": not evidence.unresolved_fatal_objections,
        }
        slack = None
        if evidence.future_cycle_target:
            required["deadline_fit"] = True
        elif evidence.deadline:
            days = (evidence.deadline - self.now()).days
            slack = days - evidence.p90_completion_days - evidence.safety_buffer_days
            required["deadline_fit"] = slack >= 0
        else:
            required["deadline_fit"] = False
        missing = tuple(name for name, passed in required.items() if not passed)
        return TopicVerdict(not missing, "TOPIC_READY" if not missing else "BLOCKED", missing, slack)


class DiscoveryPipeline(Protocol):
    def sync(self): ...
    def signals(self): ...
    def candidates(self, minimum: int, strategy: str) -> list[CandidateIdea]: ...
    def evaluate(self, candidate: CandidateIdea) -> GateEvidence | None: ...


@dataclass(frozen=True)
class DiscoveryResult:
    status: str
    waves_run: int
    ideas_generated: int
    ideas_killed: int
    selected_idea: CandidateIdea | None
    gate_evidence: GateEvidence | None
    candidates_screened: int = 0
    candidates_deep_audited: int = 0
    ready_candidates: tuple[CandidateIdea, ...] = ()


class DiscoveryLoop:
    STRATEGIES = ("CFP_THEMES", "WORKSHOP_OPEN_QUESTIONS", "LIMITATIONS_AND_CONTRADICTIONS", "MEASUREMENT_AND_IDENTIFICATION", "CROSS_DOMAIN_TRANSFER", "NEW_CAPABILITIES")

    def __init__(self, pipeline: DiscoveryPipeline, program: ResearchProgram, *, max_waves: int | None = None):
        self.pipeline = pipeline
        self.program = program
        self.max_waves = max_waves

    def run_until_topic_ready(self) -> DiscoveryResult:
        generated = killed = screened = deep_audited = wave = 0
        while self.max_waves is None or wave < self.max_waves:
            self.pipeline.sync()
            self.pipeline.signals()
            strategy = self.STRATEGIES[wave % len(self.STRATEGIES)]
            wave += 1
            candidates = self.pipeline.candidates(self.program.candidate_batch_size, strategy)
            if len(candidates) < self.program.candidate_batch_size:
                raise ValueError("each discovery wave must contain at least 20 candidates")
            generated += len(candidates)
            survivors = []
            for candidate in candidates:
                screened += 1
                if hasattr(self.pipeline, "cheap_screen") and not self.pipeline.cheap_screen(candidate):
                    killed += 1
                    continue
                survivors.append(candidate)
            if not survivors:
                continue
            ranked = self.pipeline.rank_survivors(survivors) if hasattr(self.pipeline, "rank_survivors") else survivors
            audited = ranked[:max(5, min(len(ranked), 5))]
            ready: list[tuple[CandidateIdea, GateEvidence]] = []
            for candidate in audited:
                deep_audited += 1
                evidence = self.pipeline.evaluate(candidate)
                if evidence is None:
                    killed += 1
                    continue
                verdict = TopicReadinessGate().evaluate(evidence)
                if verdict.ready:
                    ready.append((candidate, evidence))
                else:
                    killed += 1
            if ready:
                selected = self.pipeline.select(ready) if hasattr(self.pipeline, "select") else ready[0]
                candidate, evidence = selected
                return DiscoveryResult("TOPIC_READY", wave, generated, killed, candidate, evidence, screened, deep_audited, tuple(item[0] for item in ready))
        return DiscoveryResult("NO_TOPIC_READY_WITHIN_LIMIT", wave, generated, killed, None, None, screened, deep_audited)
