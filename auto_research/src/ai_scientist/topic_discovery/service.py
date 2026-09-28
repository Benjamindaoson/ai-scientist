from __future__ import annotations

import hashlib
import json
import uuid
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select, update

from ai_scientist.literature_intelligence import HybridSearch, LiteratureRepository, LiteratureService, NoveltyService
from ai_scientist.literature_intelligence import models as literature_models
from ai_scientist.opportunity_intelligence import OFFICIAL_SOURCES, OpportunityRepository, OpportunityService
from ai_scientist.opportunity_intelligence import models as opportunity_models
from ai_scientist.opportunity_intelligence.repository import new_id
from ai_scientist.research_store.repository import canonical_hash
from ai_scientist.research_os.agents import AgentExecutor, Capability, ResearchRole, TaskSpec

from .core import (
    CandidateIdea, DiscoveryLoop, GapDecision, GateEvidence, IdeaDeduplicator, NoveltyJudge,
    ResearchProgram, TopicReadinessGate, normalize,
)


DISCOVERY_HEURISTICS = (
    "measurement and identification", "contradictions and negative results", "new dataset affordances",
    "benchmark changes", "reviewer pain points", "citation-neighborhood gaps", "cross-domain transfer",
)

KNOWN_DANGEROUS_VLA_PRIORS = (
    {"title": "Failure Prediction at Runtime for Generative Robot Policies", "arxiv": "2510.09459"},
    {"title": "Perturbation-Based Epistemic Uncertainty for Failure Detection in Vision-Language-Action Models", "arxiv": "2606.20754"},
    {"title": "SAFE: Multitask Failure Detection for Vision-Language-Action Models", "arxiv": "2506.09937"},
    {"title": "Uncertainty Quantification for Flow-Based Vision-Language-Action Models", "arxiv": "2606.18043"},
    {"title": "Ask Before You Act: Token-Level Uncertainty for Intervention in Vision-Language-Action Models", "arxiv": None, "openreview": "NX0euXAv98"},
)


def validate_dataset_preflight(evidence: dict[str, Any]) -> dict[str, Any]:
    required = ("official_docs", "actual_size", "download_method", "license", "schema", "target_variable", "target_variable_available", "metadata_load")
    missing = [name for name in required if not evidence.get(name)]
    load = evidence.get("metadata_load") or {}
    if evidence.get("status") == "DATA_BLOCKED":
        status = "DATA_BLOCKED"
    elif evidence.get("target_variable_available") is not True:
        status = "DATA_LABEL_GAP"
    elif missing or load.get("status") != "SUCCEEDED" or not load.get("artifact"):
        status = "DATA_PARTIAL"
    else:
        status = "DATA_READY"
    return {**evidence, "status": status, "missing": missing}


class CodexCandidateGenerator:
    def __init__(self, executor: AgentExecutor, workspace: str | Path = "."):
        self.executor = executor
        self.workspace = Path(workspace).resolve()

    def generate(self, *, minimum: int, strategy: str, signals: list[dict], literature_context: list[dict], killed_memory: list[dict]) -> list[dict]:
        task_id = f"topic-generation-{uuid.uuid4().hex[:12]}"
        output = self.workspace / "artifacts" / "topic_discovery" / f"{task_id}.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        context = {
            "strategy": strategy, "minimum_candidates": minimum, "heuristics": list(DISCOVERY_HEURISTICS),
            "signals": signals[:40], "recent_literature": literature_context[:80], "killed_idea_memory": killed_memory[:100],
            "required_output_path": str(output),
            "candidate_fields": ["title", "current_belief", "proposed_challenge", "scientific_question", "falsifiable_claim", "why_now", "input_signal_ids", "literature_context_ids", "reasoning_summary", "expected_contribution_type", "possible_target_venues", "cheap_falsifier", "main_risk"],
            "constraints": ["Do not copy examples or use static templates", "Each question and claim must be coherent and falsifiable", "Use only supplied signal and literature IDs", "Write a JSON array with at least minimum_candidates records"],
        }
        prompt_hash = hashlib.sha256(json.dumps(context, sort_keys=True, default=str).encode()).hexdigest()
        result = self.executor.run(TaskSpec(
            task_id=task_id, role=ResearchRole.SCOUT, capability=Capability.DISCOVER_CANDIDATES,
            objective=f"Generate at least {minimum} distinct research candidates and write the JSON array to {output}",
            workspace=str(self.workspace), input_refs=[str(output.parent)],
            acceptance_criteria=["All candidates use supplied evidence IDs", "No static template candidates", "Output is valid JSON at required_output_path"],
            context=context,
        ))
        if result.status != "SUCCEEDED" or not output.is_file():
            raise RuntimeError(f"Codex candidate generation failed: {result.error_code or result.summary}")
        rows = json.loads(output.read_text(encoding="utf-8"))
        if not isinstance(rows, list) or len(rows) < minimum:
            raise ValueError("Codex candidate generation returned fewer than the required candidates")
        timestamp = datetime.now(timezone.utc).isoformat()
        for row in rows:
            row.update(generation_model="codex-cli", prompt_hash=prompt_hash, generation_timestamp=timestamp)
        return rows


class RecordedCodexCandidateGenerator:
    """Resume a recorded Codex generation without invoking a second model run."""
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def generate(self, *, minimum: int, strategy: str, signals: list[dict], literature_context: list[dict], killed_memory: list[dict]) -> list[dict]:
        rows = json.loads(self.path.read_text(encoding="utf-8"))
        if len(rows) < minimum or any(row.get("generation_model") != "codex-cli" or not row.get("prompt_hash") or not row.get("generation_timestamp") for row in rows):
            raise ValueError("recorded candidates lack verified Codex generation provenance")
        return rows


class ExternalPriorExpander:
    def __init__(self, literature: LiteratureService, *, client: httpx.Client | None = None):
        self.literature = literature
        self.client = client or httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": "ai-scientist/0.1"})

    def expand(self, queries: str | list[str], limit: int = 20) -> dict[str, Any]:
        matrix = [queries] if isinstance(queries, str) else list(dict.fromkeys(queries))
        probes = {
            "crossref": ("https://api.crossref.org/works", {"query.bibliographic": matrix[0], "filter": "from-pub-date:2022-01-01", "rows": limit, "select": "DOI,title,author,abstract,published,URL,container-title"}),
            "openalex": ("https://api.openalex.org/works", {"search": matrix[min(1, len(matrix)-1)], "per-page": limit}),
            "semantic_scholar": ("https://api.semanticscholar.org/graph/v1/paper/search", {"query": matrix[min(2, len(matrix)-1)], "limit": limit, "fields": "title,abstract,year,externalIds,url"}),
            "arxiv": ("https://export.arxiv.org/api/query", {"search_query": f"all:{matrix[min(3, len(matrix)-1)]}", "max_results": limit}),
            "openreview": ("https://api2.openreview.net/notes/search", {"query": matrix[min(4, len(matrix)-1)], "limit": limit}),
        }
        source_results: dict[str, dict[str, Any]] = {}
        items = []
        for source, (url, params) in probes.items():
            try:
                response = self.client.get(url, params=params)
                response.raise_for_status()
                if source == "crossref":
                    items = response.json()["message"]["items"]
                    count = len(items)
                elif "json" in response.headers.get("content-type", ""):
                    payload = response.json()
                    count = len(payload.get("results") or payload.get("data") or payload.get("notes") or [])
                else:
                    count = response.text.count("<entry>")
                source_results[source] = {"status": "COMPLETE", "query": params, "result_count": count}
            except Exception as exc:
                source_results[source] = {"status": "FAILED", "query": params, "result_count": 0, "error": str(exc)}
        ingested = 0
        for item in items:
            title = " ".join(item.get("title") or [])
            if not title or not item.get("DOI"):
                continue
            parts = (item.get("published") or {}).get("date-parts") or [[]]
            year = parts[0][0] if parts and parts[0] else None
            abstract = item.get("abstract") or ""
            record = {
                "source": "crossref", "source_record_id": item["DOI"], "title": title,
                "abstract": abstract, "publication_year": year, "identifiers": {"doi": item["DOI"]},
                "authors": [{"name": " ".join(part for part in (author.get("given"), author.get("family")) if part), "position": index + 1} for index, author in enumerate(item.get("author") or [])],
                "version": {"version_label": "crossref-current", "source_url": item.get("URL") or f"https://doi.org/{item['DOI']}"},
            }
            paper = self.literature.ingest_record(record)
            if abstract:
                try:
                    self.literature.ingest_full_text(paper["paper_version_id"], f"Abstract\n{abstract}", source_url=record["version"]["source_url"], license_name="Crossref abstract metadata")
                except ValueError:
                    pass
            ingested += 1
        return {"status": "COMPLETE" if any(row["status"] == "COMPLETE" for row in source_results.values()) else "FAILED", "sources": source_results, "ingested": ingested}


class ProductionTopicPipeline:
    def __init__(self, opportunity_repository: OpportunityRepository, literature_repository: LiteratureRepository, embedding_provider, *, candidate_generator: CodexCandidateGenerator | None = None, output_root: str | Path = "reports/topic_discovery_hardening", live_sync: bool = True):
        if candidate_generator is None:
            raise ValueError("production requires an executor-backed candidate generator")
        self.opportunity_repository = opportunity_repository
        self.opportunities = OpportunityService(opportunity_repository)
        self.literature_repository = literature_repository
        self.literature = LiteratureService(literature_repository)
        self.search = HybridSearch(literature_repository, embedding_provider)
        self.novelty = NoveltyService(self.search)
        self.judge = NoveltyJudge()
        self.dedup = IdeaDeduplicator(opportunity_repository)
        self.external = ExternalPriorExpander(self.literature)
        self.output_root = Path(output_root)
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.live_sync = live_sync
        self.candidate_generator = candidate_generator
        self._signals: list[dict] = []
        self._wave = 0
        self.last_dossier: dict[str, Any] | None = None
        self._cheap_scores: dict[str, float] = {}
        self._evaluations: dict[str, tuple[GateEvidence, dict, dict]] = {}

    def sync(self):
        if self.live_sync and not self.opportunity_repository.list_opportunities():
            self.opportunities.sync(OFFICIAL_SOURCES)

    def signals(self):
        self._signals = self.opportunities.generate_signals(domain="Embodied AI and Robot Learning")
        return self._signals

    def candidates(self, minimum: int, strategy: str) -> list[CandidateIdea]:
        self._wave += 1
        signals = self._signals or [{"signal_id": "no-current-signal", "title": "Recent literature", "evidence_refs": []}]
        with self.literature_repository.engine.connect() as connection:
            literature_context = [dict(row._mapping) for row in connection.execute(
                select(literature_models.papers.c.paper_id, literature_models.papers.c.title, literature_models.papers.c.abstract, literature_models.papers.c.publication_year)
                .order_by(literature_models.papers.c.publication_year.desc().nulls_last()).limit(80)
            )]
        generated = self.candidate_generator.generate(
            minimum=minimum, strategy=strategy, signals=signals, literature_context=literature_context,
            killed_memory=self.opportunity_repository.list_killed_lineage(),
        )
        candidates = []
        for row in generated:
            idea_id = str(uuid.uuid4())
            candidate = CandidateIdea(
                idea_id=idea_id, title=row["title"], current_belief=row["current_belief"], proposed_challenge=row["proposed_challenge"],
                scientific_question=row["scientific_question"], falsifiable_claim=row["falsifiable_claim"], why_now=row["why_now"],
                origin_signal_ids=tuple(row["input_signal_ids"]), expected_contribution_type=row["expected_contribution_type"],
                possible_target_venues=tuple(row["possible_target_venues"]), cheap_falsifier=row["cheap_falsifier"], main_risk=row["main_risk"],
                generation_model=row["generation_model"], prompt_hash=row["prompt_hash"], input_signal_ids=tuple(row["input_signal_ids"]),
                literature_context_ids=tuple(row["literature_context_ids"]), reasoning_summary=row["reasoning_summary"], generation_timestamp=row["generation_timestamp"],
            )
            if self.dedup.is_duplicate(candidate):
                continue
            self.opportunity_repository.insert(
                opportunity_models.topic_candidates, candidate_row_id=new_id(), idea_id=idea_id, wave=self._wave,
                strategy=strategy, payload=asdict(candidate), state="CANDIDATE",
            )
            if not self.opportunity_repository.get_lineage(idea_id):
                self.opportunity_repository.insert(
                    opportunity_models.idea_lineage, idea_lineage_id=new_id(), idea_id=idea_id, parent_idea_id=None,
                    generation=0, origin_signal_ids=list(candidate.origin_signal_ids), normalized_question=normalize(candidate.scientific_question),
                    semantic_fingerprint=candidate.semantic_fingerprint, reframe_reason=None, kill_reason=None, killing_papers=[],
                    failed_gate=None, status="CANDIDATE", material_change_refs=[],
                )
            candidates.append(candidate)
        if len(candidates) < minimum:
            raise ValueError("executor-generated wave was reduced below 20 by killed-memory deduplication; generate a new wave")
        return candidates

    @staticmethod
    def _query_matrix(candidate: CandidateIdea, role: str) -> list[str]:
        core = candidate.scientific_question.removesuffix("?")
        claim = candidate.falsifiable_claim
        if role == "scout":
            return [core, claim, core.replace("whether", "relation between"), f"uncertainty calibration reliability {core}", f"robot learning benchmark {core}", f"reinforcement learning control {core}", f'"{claim}"']
        return [claim, f"failure identification {core}", f"causal measurement alternative terminology {core}", f"control theory {core}", f"NLP agents multimodal {core}", f"survey thesis preprint {core}", f'"{core}"']

    def _audit(self, candidate: CandidateIdea, role: str, *, external: bool) -> tuple[dict, Any]:
        matrix = self._query_matrix(candidate, role)
        if external:
            external_result = self.external.expand(matrix, limit=20)
        else:
            external_result = {"status": "NOT_REQUESTED", "sources": {}}
        result = self.search.search(matrix[0], actor_role=role, idea_ref=candidate.idea_id, query_variants=matrix, filters={"years": [2022, 2026], "external_expansion": external, "adjacent_domains": True}, limit=50)
        result["external_expansion"] = external_result
        priors = result["results"]
        graph_coverage = self._expand_evidence_graph(priors[:10])
        result["citation_expansion"] = graph_coverage
        decision = self.judge.decide(candidate, priors, search_complete=False)
        self.opportunity_repository.insert(
            opportunity_models.novelty_audits, novelty_audit_id=new_id(), idea_id=candidate.idea_id, actor_role=role,
            retrieval_run_id=result["retrieval_run_id"], decision=decision.decision.value, search_matrix=matrix,
            dangerous_priors=priors[:10], coverage={"years": [2022, 2026], "core": True, "external": external, "adjacent": True, "citation_expansion": graph_coverage},
        )
        return result, decision

    def cheap_screen(self, candidate: CandidateIdea) -> bool:
        variants = self._query_matrix(candidate, "scout")[:2]
        result = self.search.search(variants[0], actor_role="scout-cheap", idea_ref=candidate.idea_id, query_variants=variants, filters={"stage": "cheap"}, limit=20)
        decision = self.judge.decide(candidate, result["results"], search_complete=False)
        self._cheap_scores[candidate.idea_id] = sum(row.get("score", 0.0) for row in result["results"][:5])
        if decision.decision == GapDecision.KILLED_BY_PRIOR:
            self._kill(candidate, decision, "CHEAP_NOVELTY_SCREEN")
            return False
        return True

    def rank_survivors(self, candidates: list[CandidateIdea]) -> list[CandidateIdea]:
        return sorted(candidates, key=lambda item: (self._cheap_scores.get(item.idea_id, 0.0), item.idea_id))

    def select(self, ready: list[tuple[CandidateIdea, GateEvidence]]) -> tuple[CandidateIdea, GateEvidence]:
        ranked = sorted(ready, key=lambda item: (
            sum(bool(value.get("pass")) for value in (item[1].significance or {}).values() if isinstance(value, dict)),
            -(item[1].compute or {}).get("expected", {}).get("gpu_hours", 10**9),
        ), reverse=True)
        candidate, evidence = ranked[0]
        cached = self._evaluations[candidate.idea_id]
        self._save_dossier(candidate, evidence, cached[1], cached[2])
        return candidate, evidence

    def _expand_evidence_graph(self, priors: list[dict[str, Any]]) -> dict[str, Any]:
        expanded: set[str] = set()
        for prior in priors:
            paper_id = prior["paper_id"]
            expanded |= self.literature.expand_citations(paper_id, hops=2)
            expanded |= self.literature.co_citations(paper_id)
            expanded |= self.literature.bibliographic_coupling(paper_id)
            expanded |= self.literature.same_author_papers(paper_id)
        return {"performed": bool(priors), "seed_papers": len(priors), "expanded_paper_ids": sorted(expanded)}

    def _structured_deep_audit(self, priors: list[dict[str, Any]]) -> list[dict[str, Any]]:
        audits = []
        with self.literature_repository.engine.connect() as connection:
            for prior in priors[:10]:
                rows = connection.execute(
                    select(
                        literature_models.paper_versions.c.paper_version_id,
                        literature_models.artifacts.c.license,
                        literature_models.sections.c.section_type,
                        literature_models.sections.c.heading,
                        literature_models.chunks.c.chunk_id,
                        literature_models.chunks.c.content,
                    )
                    .select_from(literature_models.paper_versions)
                    .join(literature_models.documents, literature_models.documents.c.paper_version_id == literature_models.paper_versions.c.paper_version_id)
                    .join(literature_models.artifacts, literature_models.artifacts.c.literature_artifact_id == literature_models.documents.c.literature_artifact_id)
                    .join(literature_models.sections, literature_models.sections.c.document_id == literature_models.documents.c.document_id)
                    .join(literature_models.chunks, literature_models.chunks.c.section_id == literature_models.sections.c.section_id)
                    .where(literature_models.paper_versions.c.paper_id == prior["paper_id"])
                    .order_by(literature_models.sections.c.ordinal, literature_models.chunks.c.ordinal).limit(30)
                ).all()
                license_text = " ".join(str(row.license or "") for row in rows).lower()
                section_types = {str(row.section_type).lower() for row in rows}
                abstract_only = not rows or "abstract" in license_text or section_types <= {"abstract", "unknown"}
                spans = [] if abstract_only else [
                    {"section": row.heading or row.section_type, "chunk_id": row.chunk_id, "text": row.content[:600]}
                    for row in rows if str(row.section_type).lower() in {"abstract", "introduction", "related_work", "method", "experiments", "conclusion"}
                ]
                audits.append({
                    "paper_id": prior["paper_id"], "paper_version_id": rows[0].paper_version_id if rows else None,
                    "title": prior.get("title"), "full_text_status": "AVAILABLE" if spans else "UNAVAILABLE",
                    "source_chunk_ids": [span["chunk_id"] for span in spans], "source_spans": spans,
                    "scientific_question_overlap": "UNKNOWN", "claim_overlap": "UNKNOWN", "assumption_overlap": "UNKNOWN",
                    "method_overlap": "UNKNOWN", "measurement_overlap": "UNKNOWN", "setting_overlap": "UNKNOWN", "conclusion_overlap": "UNKNOWN",
                    "review_status": "UNRESOLVED: independent reviewer assessment required" if spans else "FULL_TEXT_UNAVAILABLE",
                })
        return audits

    def _mark_state(self, candidate: CandidateIdea, state: str, gate: str, reason: str) -> None:
        with self.opportunity_repository.engine.begin() as connection:
            connection.execute(update(opportunity_models.topic_candidates).where(
                opportunity_models.topic_candidates.c.idea_id == candidate.idea_id
            ).values(state=state))
            connection.execute(update(opportunity_models.idea_lineage).where(
                opportunity_models.idea_lineage.c.idea_id == candidate.idea_id
            ).values(status=state, failed_gate=gate, kill_reason=reason))

    def evaluate(self, candidate: CandidateIdea) -> GateEvidence | None:
        scout, scout_decision = self._audit(candidate, "scout", external=False)
        if scout_decision.decision == GapDecision.KILLED_BY_PRIOR:
            self._kill(candidate, scout_decision, "SCOUT_GAP_AUDIT")
            return None
        reviewer, _ = self._audit(candidate, "reviewer", external=True)
        dangerous = reviewer["results"][:10]
        deep_audit = self._structured_deep_audit(dangerous)
        external_sources = reviewer.get("external_expansion", {}).get("sources", {})
        search_complete = (
            scout.get("executed_query_count") == 7 and reviewer.get("executed_query_count") == 7
            and len(dangerous) >= 10 and any(row.get("status") == "COMPLETE" for row in external_sources.values())
        )
        reviewer_decision = self.judge.deep_decide(candidate, deep_audit, search_complete=search_complete)
        self.opportunity_repository.insert(
            opportunity_models.novelty_audits, novelty_audit_id=new_id(), idea_id=candidate.idea_id,
            actor_role="reviewer-deep", retrieval_run_id=reviewer["retrieval_run_id"], decision=reviewer_decision.decision.value,
            search_matrix=self._query_matrix(candidate, "reviewer"), dangerous_priors=dangerous,
            coverage={"query_executions": reviewer.get("query_executions", {}), "external_sources": external_sources,
                      "citation_expansion": reviewer.get("citation_expansion", {}), "structured_deep_audit": deep_audit},
        )
        if reviewer_decision.decision != GapDecision.NOVELTY_SURVIVES_AUDIT:
            state = reviewer_decision.decision.value
            if reviewer_decision.decision == GapDecision.KILLED_BY_PRIOR:
                self._kill(candidate, reviewer_decision, "REVIEWER_DEEP_AUDIT")
            else:
                self._mark_state(candidate, state, "REVIEWER_DEEP_AUDIT", reviewer_decision.reason)
            return None
        data = self._data_preflight()
        if data["status"] != "DATA_READY":
            self._record_feasibility(candidate.idea_id, "DATA", "BLOCKED", data)
            self._mark_state(candidate, "FEASIBILITY_UNCERTAIN", "DATA_FEASIBILITY", data["status"])
            return None
        dangerous = [row for row in reviewer["results"] if row.get("source_chunk_ids")][:10]
        deadline_fit = self._deadline_fit(candidate, p90_days=27, safety_buffer_days=14)
        evidence = GateEvidence(
            scientific_question=candidate.scientific_question, falsifiable_claim=candidate.falsifiable_claim,
            scout_retrieval_run_id=scout["retrieval_run_id"], reviewer_retrieval_run_id=reviewer["retrieval_run_id"],
            no_covering_prior=True, closest_prior_work=dangerous, adjacent_field_search=True,
            citation_expansion=bool(scout["citation_expansion"]["performed"] and reviewer["citation_expansion"]["performed"]),
            gap_statement="No inspected source-backed work jointly tests the declared relation, matched controls, and closed-loop outcome under the documented search matrix.",
            significance={name: {"pass": False, "reason": "Independent reviewer assessment has not resolved this gate.", "evidence_refs": [], "assessor": "reviewer"} for name in ("fundamental", "surprising", "broad", "actionable", "cheap_to_falsify", "hard_to_explain_away", "defensible_novelty", "value_over_cost")},
            critical_questions=self._critical_questions(candidate, dangerous), data=data,
            method={"research_type": "MEASUREMENT", "primary_method": "paired retrospective trajectory analysis", "baselines": ["open-loop likelihood", "calibration error", "ensemble disagreement"], "controls": ["task success", "task family", "trajectory length", "seed"], "metrics": ["AUROC", "AUPRC", "calibration error"], "analysis": "paired bootstrap with task-family stratification", "confounds": ["dataset policy bias", "action discretization"]},
            engineering={"status": "BLOCKED", "command": None, "artifact": None, "metric_computed": None, "reason": "Candidate-specific loader and metric smoke have not run."},
            compute={"candidate_id": candidate.idea_id, "assumptions": [], "calculation": None, "best_case": {}, "expected": {}, "worst_reasonable": {}},
            time_estimate={"candidate_id": candidate.idea_id, "assumptions": [], "calculation": None, "p90_days": 0},
            deadline=deadline_fit["deadline"], p90_completion_days=27, safety_buffer_days=14,
            future_cycle_target=deadline_fit["future_cycle_target"], venue_fit=deadline_fit["venue_fit"],
            killer_experiment={"candidate_id": candidate.idea_id, "data": data.get("dataset_name"), "kill_condition": None},
            reviewer_attacks=["The relation is a calibration restatement", "Dataset policy bias creates the effect", "Matched success does not match difficulty", "The metric does not identify intervention utility", "The result may not transfer across embodiments"],
            generation_provenance={"generation_model": candidate.generation_model, "prompt_hash": candidate.prompt_hash, "input_signal_ids": list(candidate.input_signal_ids), "literature_context_ids": list(candidate.literature_context_ids), "reasoning_summary": candidate.reasoning_summary, "generation_timestamp": candidate.generation_timestamp},
            deep_audit=deep_audit,
            coherence={"pass": False, "reason": "PI/Reviewer construct alignment has not been executed."},
            benchmark_status="PROVISIONAL",
        )
        verdict = TopicReadinessGate().evaluate(evidence)
        for audit_type, value in {
            "DATA": evidence.data, "METHOD": evidence.method, "ENGINEERING": evidence.engineering,
            "COMPUTE": evidence.compute, "TIME": evidence.time_estimate, "VENUE": evidence.venue_fit,
            "KILLER_EXPERIMENT": evidence.killer_experiment,
            "FINAL_REVIEW": {"ready": verdict.ready, "missing": list(verdict.missing)},
        }.items():
            self._record_feasibility(candidate.idea_id, audit_type, "PASS" if value and (audit_type != "FINAL_REVIEW" or verdict.ready) else "BLOCKED", value or {})
        if not verdict.ready:
            self._kill(candidate, None, "FINAL_TOPIC_REVIEW", ", ".join(verdict.missing))
            return None
        self._evaluations[candidate.idea_id] = (evidence, scout, reviewer)
        return evidence

    def _deadline_fit(self, candidate: CandidateIdea, *, p90_days: int, safety_buffer_days: int) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        active = [
            item for item in self.opportunities.upcoming(now=now)
            if item.get("venue_name") in candidate.possible_target_venues
        ]
        evaluated = []
        for item in active:
            days_remaining = (item["submission_deadline_utc"] - now).days
            slack = days_remaining - p90_days - safety_buffer_days
            evaluated.append({
                "venue": item["venue_name"], "opportunity_id": item["opportunity_id"],
                "submission_deadline": item["submission_deadline_utc"].isoformat(),
                "days_remaining": days_remaining, "p90_completion_days": p90_days,
                "safety_buffer_days": safety_buffer_days, "deadline_slack_days": slack,
                "targetable": slack >= 0, "official_url": item["official_url"],
            })
        targetable = [item for item in evaluated if item["targetable"]]
        if targetable:
            selected = max(targetable, key=lambda item: item["deadline_slack_days"])
            return {
                "deadline": datetime.fromisoformat(selected["submission_deadline"]), "future_cycle_target": False,
                "venue_fit": {
                    "primary": selected["venue"], "secondary": "CoRL", "workshop": "robot learning reliability",
                    "research_fit": "Embodied learning, planning, reliability, and uncertainty are in the official scope.",
                    "scope_evidence": selected["official_url"], "deadline_fit": selected,
                    "evaluated_current_opportunities": evaluated,
                },
            }
        return {
            "deadline": None, "future_cycle_target": True,
            "venue_fit": {
                "primary": candidate.possible_target_venues[0], "secondary": candidate.possible_target_venues[1],
                "workshop": "robot learning reliability",
                "research_fit": "Embodied learning, planning, reliability, and uncertainty match the recorded official CFP scope.",
                "scope_evidence": "Official opportunity snapshots in research.opportunities",
                "deadline_fit": "FUTURE_CYCLE: no currently open recorded deadline has p90 completion plus safety-buffer slack.",
                "evaluated_current_opportunities": evaluated,
            },
        }

    def _record_feasibility(self, idea_id: str, audit_type: str, status: str, evidence: dict[str, Any]) -> None:
        self.opportunity_repository.insert(
            opportunity_models.feasibility_audits,
            feasibility_audit_id=new_id(), idea_id=idea_id, audit_type=audit_type, status=status, evidence=evidence,
        )

    def _data_preflight(self) -> dict[str, Any]:
        url = "https://droid-dataset.github.io/droid/the-droid-dataset"
        try:
            response = httpx.get(url, timeout=20, follow_redirects=True)
            response.raise_for_status()
            evidence = {
                "http_status": response.status_code, "homepage_reachable": True, "dataset_name": "DROID",
                "official_docs": [url], "source": url, "actual_size": "1.7TB RLDS full; 2GB official 100-episode debug subset",
                "download_method": "gsutil -m cp -r gs://gresearch/robotics/droid_100 <path>",
                "license": "Terms require explicit confirmation before download", "schema": ["observation", "action", "language_instruction"],
                "target_variable": "closed-loop failure/intervention outcome", "target_variable_available": False,
                "metadata_load": {"status": "NOT_RUN", "command": None, "artifact": None},
                "preflight": f"Official documentation fetch {response.status_code}; {len(response.content)} bytes; no failure/intervention label documented",
            }
        except Exception as exc:
            evidence = {"status": "DATA_BLOCKED", "dataset_name": "DROID", "source": url, "error": str(exc), "preflight": str(exc)}
        return validate_dataset_preflight(evidence)

    @staticmethod
    def _critical_questions(candidate: CandidateIdea, priors: list[dict]) -> list[dict]:
        prompts = ("current belief", "closest prior scope", "irreducible difference", "benchmark-free meaning", "scientific-not-feature", "non-obvious outcome", "alternative explanation", "reviewer explanation", "fastest falsifier", "positive-result action", "negative-result value", "gap type", "simpler mechanism", "adjacent-field solution", "claim evidence threshold")
        refs = [row["paper_id"] for row in priors[:5]]
        return [{"question": prompt, "answer": None, "evidence_refs": refs, "counterarguments": [], "confidence_class": "LOW", "unresolved": ["PI and independent reviewer answer required"], "status": "UNRESOLVED", "answer_model": None, "prompt_hash": None} for prompt in prompts]

    def _kill(self, candidate: CandidateIdea, decision, gate: str, reason: str | None = None) -> None:
        killing = [decision.killing_paper_id] if decision and decision.killing_paper_id else []
        self.dedup.remember_killed(candidate, kill_reason=reason or (decision.reason if decision else gate), killing_papers=killing, failed_gate=gate)
        with self.opportunity_repository.engine.begin() as connection:
            connection.execute(update(opportunity_models.topic_candidates).where(opportunity_models.topic_candidates.c.idea_id == candidate.idea_id).values(state="KILLED_BY_PRIOR" if killing else "KILLED"))

    def _save_dossier(self, candidate: CandidateIdea, evidence: GateEvidence, scout: dict, reviewer: dict) -> dict[str, Any]:
        dossier = {
            "identity": {"title": candidate.title, "scientific_question": candidate.scientific_question, "falsifiable_claim": candidate.falsifiable_claim, "research_type": evidence.method["research_type"]},
            "why_now": {"origin_signal_ids": list(candidate.origin_signal_ids), "statement": candidate.why_now},
            "current_belief": candidate.current_belief, "proposed_challenge": candidate.proposed_challenge,
            "gap_statement": evidence.gap_statement, "closest_prior_work": evidence.closest_prior_work,
            "independent_novelty_audit": {"scout_retrieval_run_id": scout["retrieval_run_id"], "reviewer_retrieval_run_id": reviewer["retrieval_run_id"], "coverage": {"years": "2022-2026", "adjacent_fields": True, "external": True, "scout_graph_expansion": scout.get("citation_expansion", {}), "reviewer_graph_expansion": reviewer.get("citation_expansion", {})}},
            "novelty_boundary": "NOVELTY_SURVIVES_AUDIT is protocol-bounded; it does not claim that no related work exists.",
            "scientific_value": evidence.significance, "data": evidence.data, "method": evidence.method,
            "killer_experiment": evidence.killer_experiment, "compute": evidence.compute, "time": evidence.time_estimate,
            "target_venue": evidence.venue_fit, "reviewer_risks": evidence.reviewer_attacks,
            "kill_conditions": [evidence.killer_experiment["kill_condition"], "A newly found prior fully covers the claim", "Data license blocks the declared analysis"],
            "gate_evidence": asdict(evidence), "final_decision": "TOPIC_READY",
        }
        topic_id = str(uuid.uuid4())
        self.opportunity_repository.insert(opportunity_models.topic_dossiers, topic_id=topic_id, idea_id=candidate.idea_id, status="TOPIC_READY", dossier=dossier, content_hash=canonical_hash(dossier))
        with self.opportunity_repository.engine.begin() as connection:
            connection.execute(update(opportunity_models.topic_candidates).where(
                opportunity_models.topic_candidates.c.idea_id == candidate.idea_id
            ).values(state="TOPIC_READY"))
            connection.execute(update(opportunity_models.idea_lineage).where(
                opportunity_models.idea_lineage.c.idea_id == candidate.idea_id
            ).values(status="TOPIC_READY"))
        json_path = self.output_root / f"{topic_id}.json"
        md_path = self.output_root / f"{topic_id}.md"
        json_path.write_text(json.dumps(dossier, indent=2, default=str), encoding="utf-8")
        md_path.write_text(self._markdown(dossier), encoding="utf-8")
        (self.output_root / "final_topic_dossier.json").write_text(json.dumps(dossier, indent=2, default=str), encoding="utf-8")
        (self.output_root / "final_topic_dossier.md").write_text(self._markdown(dossier), encoding="utf-8")
        self.last_dossier = {"topic_id": topic_id, "idea_id": candidate.idea_id, "json": str(json_path), "markdown": str(md_path), **dossier}
        return self.last_dossier

    @staticmethod
    def _markdown(dossier: dict[str, Any]) -> str:
        identity = dossier["identity"]
        sections = [
            "# Topic Dossier", f"\n## Identity\n\n**Title:** {identity['title']}\n\n**Scientific question:** {identity['scientific_question']}\n\n**Falsifiable claim:** {identity['falsifiable_claim']}\n\n**Research type:** {identity['research_type']}",
            f"\n## Why Now\n\n{dossier['why_now']['statement']}", f"\n## Current Belief\n\n{dossier['current_belief']}",
            f"\n## Proposed Challenge\n\n{dossier['proposed_challenge']}", f"\n## Gap Statement\n\n{dossier['gap_statement']}",
            f"\n## Closest Prior Work\n\n```json\n{json.dumps(dossier['closest_prior_work'], indent=2, default=str)}\n```",
            f"\n## Independent Novelty Audit\n\n```json\n{json.dumps(dossier['independent_novelty_audit'], indent=2)}\n```",
            f"\n## Novelty Boundary\n\n{dossier['novelty_boundary']}", f"\n## Data\n\n```json\n{json.dumps(dossier['data'], indent=2)}\n```",
            f"\n## Method\n\n```json\n{json.dumps(dossier['method'], indent=2)}\n```", f"\n## Killer Experiment\n\n```json\n{json.dumps(dossier['killer_experiment'], indent=2)}\n```",
            f"\n## Compute\n\n```json\n{json.dumps(dossier['compute'], indent=2)}\n```", f"\n## Time\n\n```json\n{json.dumps(dossier['time'], indent=2)}\n```",
            f"\n## Target Venue\n\n```json\n{json.dumps(dossier['target_venue'], indent=2)}\n```", f"\n## Reviewer Risks\n\n" + "\n".join(f"- {risk}" for risk in dossier["reviewer_risks"]),
            f"\n## Kill Conditions\n\n" + "\n".join(f"- {item}" for item in dossier["kill_conditions"]), "\n## Final Decision\n\nTOPIC_READY\n",
        ]
        return "\n".join(sections)


class TopicDiscoveryService:
    def __init__(self, pipeline: ProductionTopicPipeline, program: ResearchProgram | None = None):
        self.pipeline = pipeline
        self.program = program or ResearchProgram.production_default()

    def run_until_ready(self, *, max_waves: int | None = None) -> dict[str, Any]:
        with self.pipeline.opportunity_repository.engine.begin() as connection:
            previous = connection.execute(select(opportunity_models.topic_dossiers.c.idea_id).where(opportunity_models.topic_dossiers.c.status == "TOPIC_READY")).all()
            if previous:
                idea_ids = [row.idea_id for row in previous]
                connection.execute(update(opportunity_models.topic_dossiers).where(opportunity_models.topic_dossiers.c.idea_id.in_(idea_ids)).values(status="NOVELTY_UNCERTAIN"))
                connection.execute(update(opportunity_models.topic_candidates).where(opportunity_models.topic_candidates.c.idea_id.in_(idea_ids)).values(state="NOVELTY_UNCERTAIN"))
                connection.execute(update(opportunity_models.idea_lineage).where(opportunity_models.idea_lineage.c.idea_id.in_(idea_ids)).values(status="NOVELTY_UNCERTAIN", failed_gate="HARDENING_REAUDIT"))
                for idea_id in idea_ids:
                    connection.execute(opportunity_models.feasibility_audits.insert().values(
                        feasibility_audit_id=new_id(), idea_id=idea_id, audit_type="HARDENING_REAUDIT",
                        status="FEASIBILITY_UNCERTAIN", evidence={"reason": "Previous readiness used abstract-only novelty evidence and homepage-only data preflight."},
                    ))
        run = self.pipeline.opportunity_repository.insert(opportunity_models.discovery_runs, discovery_run_id=new_id(), program=asdict(self.program), status="RUNNING", wave=0, counts={})
        try:
            result = DiscoveryLoop(self.pipeline, self.program, max_waves=max_waves).run_until_topic_ready()
            values = {"status": result.status, "wave": result.waves_run, "counts": {"ideas_generated": result.ideas_generated, "ideas_killed": result.ideas_killed, "candidates_screened": result.candidates_screened, "candidates_deep_audited": result.candidates_deep_audited, "topic_ready_survivors": len(result.ready_candidates)}, "completed_at": datetime.now(timezone.utc), "topic_id": self.pipeline.last_dossier["topic_id"] if self.pipeline.last_dossier else None}
            with self.pipeline.opportunity_repository.engine.begin() as connection:
                connection.execute(update(opportunity_models.discovery_runs).where(opportunity_models.discovery_runs.c.discovery_run_id == run["discovery_run_id"]).values(**values))
            return {"discovery_run_id": run["discovery_run_id"], **values, "dossier": self.pipeline.last_dossier}
        except Exception as exc:
            with self.pipeline.opportunity_repository.engine.begin() as connection:
                connection.execute(update(opportunity_models.discovery_runs).where(opportunity_models.discovery_runs.c.discovery_run_id == run["discovery_run_id"]).values(status="FAILED", error=str(exc), completed_at=datetime.now(timezone.utc)))
            raise

    def list(self) -> list[dict]:
        with self.pipeline.opportunity_repository.engine.connect() as connection:
            return [dict(row._mapping) for row in connection.execute(select(opportunity_models.topic_candidates).order_by(opportunity_models.topic_candidates.c.created_at.desc()))]

    def show(self, idea_id: str) -> dict | None:
        with self.pipeline.opportunity_repository.engine.connect() as connection:
            row = connection.execute(select(opportunity_models.topic_candidates).where(opportunity_models.topic_candidates.c.idea_id == idea_id)).first()
        return dict(row._mapping) if row else None

    def audits(self, idea_id: str) -> list[dict]:
        with self.pipeline.opportunity_repository.engine.connect() as connection:
            return [dict(row._mapping) for row in connection.execute(select(opportunity_models.novelty_audits).where(opportunity_models.novelty_audits.c.idea_id == idea_id).order_by(opportunity_models.novelty_audits.c.created_at))]

    def lineage(self, idea_id: str) -> list[dict]:
        output = []
        current = self.pipeline.opportunity_repository.get_lineage(idea_id)
        while current:
            output.append(current)
            current = self.pipeline.opportunity_repository.get_lineage(current["parent_idea_id"]) if current.get("parent_idea_id") else None
        return output

    def dossier(self, idea_id: str) -> dict | None:
        with self.pipeline.opportunity_repository.engine.connect() as connection:
            row = connection.execute(select(opportunity_models.topic_dossiers).where(opportunity_models.topic_dossiers.c.idea_id == idea_id)).first()
        return dict(row._mapping) if row else None

    def status(self) -> dict | None:
        with self.pipeline.opportunity_repository.engine.connect() as connection:
            row = connection.execute(select(opportunity_models.discovery_runs).order_by(opportunity_models.discovery_runs.c.started_at.desc()).limit(1)).first()
        return dict(row._mapping) if row else None
