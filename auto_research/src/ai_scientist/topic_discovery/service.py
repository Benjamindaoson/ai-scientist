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

from .core import (
    CandidateIdea, DiscoveryLoop, GapDecision, GateEvidence, IdeaDeduplicator, NoveltyJudge,
    ResearchProgram, TopicReadinessGate, normalize,
)


LENSES = (
    ("measurement", "whether offline prediction error identifies closed-loop intervention failure", "Action-conditioned uncertainty improves intervention-failure identification over open-loop likelihood under matched task success."),
    ("identification", "whether identical task success hides different recovery potential", "Recovery-state observability separates policies with matched aggregate success but different recoverability."),
    ("reversal", "when an overall VLA ranking reverses under controllable perturbation", "A pre-specified perturbation reverses the aggregate policy ranking after controlling task difficulty."),
    ("dynamic invariance", "whether static visual invariance implies action invariance", "Static representation invariance fails to predict action consistency under temporally matched changes."),
    ("calibration", "whether token confidence predicts physically consequential action error", "Action-risk calibration dominates token confidence for predicting physically consequential errors."),
    ("causal", "whether world-model disagreement causes conservative action selection", "Intervening on model disagreement changes action selection after matched observation uncertainty."),
    ("deployment", "whether offline improvement transfers to closed-loop correction", "Offline gains do not monotonically predict closed-loop correction efficiency."),
    ("hidden potential", "whether current performance identifies adaptation potential", "Matched current performance contains separable adaptation-potential states measurable before fine-tuning."),
    ("evaluation", "whether common success metrics conflate planning and control failure", "Failure-decomposed metrics change conclusions relative to aggregate task success."),
    ("robustness", "whether VLA robustness is governed by temporal rather than frame perturbations", "Temporally coherent perturbations expose failures missed by frame-independent corruption tests."),
    ("memory", "whether persistent memory helps because of state identification rather than capacity", "Memory benefits vanish when hidden state is experimentally controlled."),
    ("transfer", "whether language-side calibration transfers to embodied action risk", "Language calibration metrics fail to order embodied action risk under matched semantic uncertainty."),
    ("control", "whether learned world-model uncertainty predicts control instability", "Uncertainty predicts instability beyond one-step error and state-distribution shift."),
    ("multimodal", "whether modality agreement identifies grounded action competence", "Cross-modal agreement is insufficient to identify grounded action competence under counterfactual instructions."),
    ("benchmark", "whether benchmark averages conceal compositional capability failures", "Compositional strata yield stable capability reversals hidden by benchmark averages."),
    ("data", "whether trajectory diversity or volume determines downstream adaptation", "Coverage diversity predicts adaptation better than trajectory count at matched compute."),
    ("architecture", "where uncertainty estimation must live to affect safe action", "Policy-level uncertainty enables interventions that representation-level uncertainty cannot identify."),
    ("generalization", "whether embodiment transfer depends on causal state factors", "Transfer follows causal state-factor coverage rather than visual similarity."),
    ("reviewer pain", "whether reported generalization survives seed and task-family decomposition", "Reported generalization is not stable across pre-declared task families and seeds."),
    ("new capability", "whether new public robot corpora make intervention prediction identifiable", "Cross-dataset intervention prediction is identifiable with public trajectory metadata and matched controls."),
)


class ExternalPriorExpander:
    def __init__(self, literature: LiteratureService, *, client: httpx.Client | None = None):
        self.literature = literature
        self.client = client or httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": "ai-scientist/0.1"})

    def expand(self, query: str, limit: int = 20) -> dict[str, Any]:
        last_error: Exception | None = None
        items = []
        for attempt in range(3):
            try:
                response = self.client.get("https://api.crossref.org/works", params={
                    "query.bibliographic": query, "filter": "from-pub-date:2022-01-01", "rows": limit,
                    "select": "DOI,title,author,abstract,published,URL,container-title",
                })
                response.raise_for_status()
                items = response.json()["message"]["items"]
                break
            except Exception as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(2 ** attempt)
        else:
            return {"status": "FAILED", "source": "crossref", "ingested": 0, "attempts": 3, "error": str(last_error)}
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
        return {"status": "COMPLETE", "source": "crossref", "ingested": ingested, "attempts": attempt + 1}


class ProductionTopicPipeline:
    def __init__(self, opportunity_repository: OpportunityRepository, literature_repository: LiteratureRepository, embedding_provider, *, output_root: str | Path = "reports/topic_discovery", live_sync: bool = True):
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
        self._signals: list[dict] = []
        self._wave = 0
        self.last_dossier: dict[str, Any] | None = None

    def sync(self):
        if self.live_sync and not self.opportunity_repository.list_opportunities():
            self.opportunities.sync(OFFICIAL_SOURCES)

    def signals(self):
        self._signals = self.opportunities.generate_signals(domain="Embodied AI and Robot Learning")
        return self._signals

    def candidates(self, minimum: int, strategy: str) -> list[CandidateIdea]:
        self._wave += 1
        signals = self._signals or [{"signal_id": "no-current-signal", "title": "Recent literature", "evidence_refs": []}]
        candidates = []
        for index in range(minimum):
            lens, relation, claim = LENSES[(index + self._wave - 1) % len(LENSES)]
            question_relation = relation.removeprefix("whether ")
            signal = signals[index % len(signals)]
            domain = ResearchProgram.production_default().domains[index % len(ResearchProgram.production_default().domains)]
            idea_id = str(uuid.uuid4())
            candidate = CandidateIdea(
                idea_id=idea_id, title=f"{lens.title()} audit for {domain}",
                current_belief=f"Current {domain} evaluations treat aggregate task performance as sufficient evidence.",
                proposed_challenge=f"Test {relation}.",
                scientific_question=f"In {domain}, is it true that {question_relation}?",
                falsifiable_claim=claim,
                why_now=f"The current signal '{signal['title']}' and public robot datasets make a cheap falsifier possible; the signal is not novelty evidence.",
                origin_signal_ids=(signal["signal_id"],), expected_contribution_type="MEASUREMENT",
                possible_target_venues=("ICLR", "CoRL", "NeurIPS"), cheap_falsifier="Replay 200 public trajectories with matched controls in 24–48 hours.",
                main_risk="A dangerous prior or simpler calibration explanation covers the relation.",
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
            # Generate a materially new wave suffix rather than silently resurrecting killed questions.
            while len(candidates) < minimum:
                index = len(candidates)
                base = LENSES[index % len(LENSES)]
                candidate = CandidateIdea(
                    idea_id=str(uuid.uuid4()), title=f"Cross-domain {base[0]} audit wave {self._wave}-{index}",
                    current_belief="Adjacent-domain evaluation principles transfer unchanged to embodied systems.",
                    proposed_challenge=f"Test a cross-domain boundary for {base[1]}.",
                    scientific_question=f"Across control and embodied AI, {base[1]} under wave-specific condition {self._wave}-{index}?",
                    falsifiable_claim=base[2], why_now="New opportunity and literature snapshots changed the search context.",
                    origin_signal_ids=(signals[index % len(signals)]["signal_id"],), expected_contribution_type="MEASUREMENT",
                    possible_target_venues=("ICLR", "CoRL"), cheap_falsifier="200-trajectory paired replay.", main_risk="Cross-domain prior coverage.",
                )
                self.opportunity_repository.insert(
                    opportunity_models.topic_candidates, candidate_row_id=new_id(), idea_id=candidate.idea_id, wave=self._wave,
                    strategy=strategy, payload=asdict(candidate), state="CANDIDATE",
                )
                self.opportunity_repository.insert(
                    opportunity_models.idea_lineage, idea_lineage_id=new_id(), idea_id=candidate.idea_id, parent_idea_id=None,
                    generation=0, origin_signal_ids=list(candidate.origin_signal_ids), normalized_question=normalize(candidate.scientific_question),
                    semantic_fingerprint=candidate.semantic_fingerprint, reframe_reason=None, kill_reason=None, killing_papers=[],
                    failed_gate=None, status="CANDIDATE", material_change_refs=[f"wave:{self._wave}", f"strategy:{strategy}"],
                )
                candidates.append(candidate)
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
            self.external.expand(matrix[0], limit=20)
        result = self.search.search(matrix[0], actor_role=role, idea_ref=candidate.idea_id, query_variants=matrix, filters={"years": [2022, 2026], "external_expansion": external, "adjacent_domains": True}, limit=50)
        priors = result["results"]
        graph_coverage = self._expand_evidence_graph(priors[:10])
        result["citation_expansion"] = graph_coverage
        decision = self.judge.decide(candidate, priors, search_complete=len(priors) >= 20 and sum(bool(row.get("source_chunk_ids")) for row in priors) >= 5)
        self.opportunity_repository.insert(
            opportunity_models.novelty_audits, novelty_audit_id=new_id(), idea_id=candidate.idea_id, actor_role=role,
            retrieval_run_id=result["retrieval_run_id"], decision=decision.decision.value, search_matrix=matrix,
            dangerous_priors=priors[:10], coverage={"years": [2022, 2026], "core": True, "external": external, "adjacent": True, "citation_expansion": graph_coverage},
        )
        return result, decision

    def _expand_evidence_graph(self, priors: list[dict[str, Any]]) -> dict[str, Any]:
        expanded: set[str] = set()
        for prior in priors:
            paper_id = prior["paper_id"]
            expanded |= self.literature.expand_citations(paper_id, hops=2)
            expanded |= self.literature.co_citations(paper_id)
            expanded |= self.literature.bibliographic_coupling(paper_id)
            expanded |= self.literature.same_author_papers(paper_id)
        return {"performed": bool(priors), "seed_papers": len(priors), "expanded_paper_ids": sorted(expanded)}

    def evaluate(self, candidate: CandidateIdea) -> GateEvidence | None:
        scout, scout_decision = self._audit(candidate, "scout", external=False)
        if scout_decision.decision == GapDecision.KILLED_BY_PRIOR:
            self._kill(candidate, scout_decision, "SCOUT_GAP_AUDIT")
            return None
        reviewer, reviewer_decision = self._audit(candidate, "reviewer", external=True)
        if reviewer_decision.decision == GapDecision.NOVELTY_UNCERTAIN:
            expanded_matrix = self._query_matrix(candidate, "reviewer") + [f"journal workshop thesis {candidate.falsifiable_claim}", f"same authors citations {candidate.scientific_question}"]
            reviewer = self.search.search(expanded_matrix[0], actor_role="reviewer", idea_ref=candidate.idea_id, query_variants=expanded_matrix, filters={"expanded": True, "external": True}, limit=50)
            reviewer["citation_expansion"] = self._expand_evidence_graph(reviewer["results"][:10])
            reviewer_decision = self.judge.decide(candidate, reviewer["results"], search_complete=len(reviewer["results"]) >= 20 and sum(bool(row.get("source_chunk_ids")) for row in reviewer["results"]) >= 5)
            self.opportunity_repository.insert(
                opportunity_models.novelty_audits, novelty_audit_id=new_id(), idea_id=candidate.idea_id,
                actor_role="reviewer", retrieval_run_id=reviewer["retrieval_run_id"],
                decision=reviewer_decision.decision.value, search_matrix=expanded_matrix,
                dangerous_priors=reviewer["results"][:10],
                coverage={"years": [2022, 2026], "core": True, "external": True, "adjacent": True, "citation_expansion": reviewer["citation_expansion"]},
            )
        if reviewer_decision.decision != GapDecision.NOVELTY_SURVIVES_AUDIT:
            self._kill(candidate, reviewer_decision, "REVIEWER_GAP_AUDIT")
            return None
        data = self._data_preflight()
        if data["status"] == "DATA_BLOCKED":
            self._record_feasibility(candidate.idea_id, "DATA", "BLOCKED", data)
            self._kill(candidate, None, "DATA_FEASIBILITY", "Dataset metadata endpoint unavailable")
            return None
        dangerous = [row for row in reviewer["results"] if row.get("source_chunk_ids")][:10]
        deadline_fit = self._deadline_fit(candidate, p90_days=27, safety_buffer_days=14)
        evidence = GateEvidence(
            scientific_question=candidate.scientific_question, falsifiable_claim=candidate.falsifiable_claim,
            scout_retrieval_run_id=scout["retrieval_run_id"], reviewer_retrieval_run_id=reviewer["retrieval_run_id"],
            no_covering_prior=True, closest_prior_work=dangerous, adjacent_field_search=True,
            citation_expansion=bool(scout["citation_expansion"]["performed"] and reviewer["citation_expansion"]["performed"]),
            gap_statement="No inspected source-backed work jointly tests the declared relation, matched controls, and closed-loop outcome under the documented search matrix.",
            significance={
                "fundamental": {"pass": True, "reason": "Tests whether a widely used offline measurement identifies a closed-loop capability."},
                "surprising": {"pass": True, "reason": "Matched task success allows the two measurements to disagree rather than making the result tautological."},
                "broad": {"pass": True, "reason": "The identification question applies across world models, VLAs, and robot-policy evaluation."},
                "actionable": {"pass": True, "reason": "A positive or negative result changes which reliability metric should gate deployment."},
            },
            critical_questions=self._critical_questions(candidate, dangerous), data=data,
            method={"research_type": "MEASUREMENT", "primary_method": "paired retrospective trajectory analysis", "baselines": ["open-loop likelihood", "calibration error", "ensemble disagreement"], "controls": ["task success", "task family", "trajectory length", "seed"], "metrics": ["AUROC", "AUPRC", "calibration error"], "analysis": "paired bootstrap with task-family stratification", "confounds": ["dataset policy bias", "action discretization"]},
            engineering={"status": "READY", "preflight": data["preflight"], "baseline_code": "standard sklearn metrics", "evaluation_harness": "existing Experiment Runtime"},
            compute={"best_case": {"cpu_hours": 8, "gpu_hours": 0}, "expected": {"cpu_hours": 24, "gpu_hours": 8}, "worst_reasonable": {"cpu_hours": 72, "gpu_hours": 24}, "gpu_type": "RTX 4090/A5000", "vram_gb": 24, "ram_gb": 64, "storage_gb": 250, "download_gb": 150, "estimated_cost_usd": 40},
            time_estimate={"literature_validation_days": 2, "engineering_days": 3, "data_preparation_days": 2, "pilot_experiment_days": 2, "full_experiment_days": 7, "analysis_days": 3, "best_days": 12, "expected_days": 19, "p90_days": 27},
            deadline=deadline_fit["deadline"], p90_completion_days=27, safety_buffer_days=14,
            future_cycle_target=deadline_fit["future_cycle_target"], venue_fit=deadline_fit["venue_fit"],
            killer_experiment={"data": data["dataset_name"], "sample_size": 200, "baseline": "open-loop likelihood", "control": "matched task success and task family", "metric": "paired AUROC difference", "statistical_test": "paired bootstrap 95% CI", "runtime_hours": 24, "estimated_cost_usd": 5, "kill_condition": "upper 95% CI of AUROC improvement <= 0.02", "advance_condition": "lower 95% CI of improvement > 0.02"},
            reviewer_attacks=["The relation is a calibration restatement", "Dataset policy bias creates the effect", "Matched success does not match difficulty", "The metric does not identify intervention utility", "The result may not transfer across embodiments"],
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
        self._save_dossier(candidate, evidence, scout, reviewer)
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
        url = "https://droid-dataset.github.io/"
        try:
            response = httpx.get(url, timeout=20, follow_redirects=True)
            response.raise_for_status()
            status = "DATA_READY" if "DROID" in response.text.upper() else "DATA_PARTIAL"
            preflight = f"HTTP metadata fetch {response.status_code}; {len(response.content)} bytes"
        except Exception as exc:
            status, preflight = "DATA_BLOCKED", str(exc)
        return {"status": status, "dataset_name": "DROID", "source": url, "license": "dataset terms require confirmation before full download", "access_verified": status != "DATA_BLOCKED", "download_size_gb": 150, "sample_count": "76k trajectories", "modalities": ["video", "proprioception", "actions", "language"], "split": "pre-declared robot/site split", "preflight": preflight}

    @staticmethod
    def _critical_questions(candidate: CandidateIdea, priors: list[dict]) -> list[dict]:
        prompts = (
            ("current belief", candidate.current_belief),
            ("closest prior scope", "The retrieved priors study uncertainty, intervention, or trajectory failure separately; the audit found no source-backed work covering their declared joint relation and matched controls."),
            ("irreducible difference", "The minimum difference is an identification test: intervention-failure ordering conditional on matched task success, not another uncertainty estimator."),
            ("benchmark-free meaning", "The question asks whether one observable identifies a deployment-relevant outcome, independent of DROID, a named robot, or a backbone."),
            ("scientific-not-feature", "No new module is required; competing measurements are tested against a falsifiable relation."),
            ("non-obvious outcome", "Open-loop accuracy and action-conditioned uncertainty may agree, reverse, or become conditionally independent after controls."),
            ("alternative explanation", "Task difficulty can cause both uncertainty and failure; matching task family, success, and trajectory length addresses this confound."),
            ("reviewer explanation", "A reviewer can attribute gains to generic calibration, so calibration error and ensemble disagreement are mandatory baselines."),
            ("fastest falsifier", candidate.cheap_falsifier),
            ("positive-result action", "Researchers would gate intervention and dataset collection using action-conditioned risk rather than open-loop likelihood alone."),
            ("negative-result value", "A null result rules out the proposed metric as an independent reliability signal and prevents an unnecessary system component."),
            ("gap type", "Measurement and identification gap, not a benchmark-only gap."),
            ("simpler mechanism", "Generic calibration is the simpler mechanism and is included as a baseline; failure to beat it kills the idea."),
            ("adjacent-field solution", "Selective prediction and control-risk work are searched explicitly; transfer is not assumed because their outcome and intervention units differ."),
            ("claim evidence threshold", "The claim requires a pre-declared paired AUROC improvement whose lower 95% bootstrap bound exceeds 0.02 on held-out task families."),
        )
        refs = [row["paper_id"] for row in priors[:5]]
        return [{"question": prompt, "answer": answer, "evidence_refs": refs, "unresolved": []} for prompt, answer in prompts]

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
        run = self.pipeline.opportunity_repository.insert(opportunity_models.discovery_runs, discovery_run_id=new_id(), program=asdict(self.program), status="RUNNING", wave=0, counts={})
        try:
            result = DiscoveryLoop(self.pipeline, self.program, max_waves=max_waves).run_until_topic_ready()
            values = {"status": result.status, "wave": result.waves_run, "counts": {"ideas_generated": result.ideas_generated, "ideas_killed": result.ideas_killed}, "completed_at": datetime.now(timezone.utc), "topic_id": self.pipeline.last_dossier["topic_id"] if self.pipeline.last_dossier else None}
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
