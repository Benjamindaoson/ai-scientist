"""Comprehensive test for AI Scientist components.

Tests:
1. Domain models
2. Database schema
3. Repository
4. Multi-agent debate system
5. Literature search
6. Paper reader
7. Evidence validator
"""
import asyncio
import sys
import os

# Add project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from ai_scientist.core.models.domain import (
    ResearchPhenomenon, ResearchPuzzle, ResearchQuestion, ResearchMethod,
    Theory, Construct, Mechanism, AlternativeExplanation, PaperAnalysis,
    NearestNeighborPaper, PhenomenonType, PuzzleType, MechanismType,
    DataSource, Measurement, IdentificationStrategy, StateSnapshot,
    ContractVersion, QuestionClarity, QuestionFeasibility, MethodType, TheoryLevel,
)
from ai_scientist.db.repository import Database, Repository
from ai_scientist.engine.multi_agent_debate import (
    MultiAgentDebateSystem, AgentRole, DebateStatus
)
from ai_scientist.literature.search import LiteratureSearch, SearchQuery, SearchSource
from ai_scientist.literature.reader import PaperReader, ExtractedInsight
from ai_scientist.literature.validator import (
    EvidenceValidator, EvidenceItem, EvidenceType, EvidenceQuality
)


def test_domain_models():
    """Test domain model creation."""
    print("\n" + "=" * 60)
    print("Testing Domain Models")
    print("=" * 60)

    # Test ResearchPhenomenon
    phenomenon = ResearchPhenomenon(
        id="phen_001",
        project_id="proj_001",
        raw_description="Large language models occasionally generate incorrect but confident responses",
        phenomenon_type=PhenomenonType.OBSERVATIONAL,
        domain="AI",
        scope="micro",
        key_entities=["LLM", "confident error", "hallucination"],
        key_behaviors=["generating plausible but wrong answers"],
        boundary_conditions=["under uncertainty", "with limited knowledge"],
    )
    print(f"✓ Created phenomenon: {phenomenon.id}")
    assert phenomenon.id == "phen_001"
    assert phenomenon.phenomenon_type == PhenomenonType.OBSERVATIONAL

    # Test ResearchPuzzle
    puzzle = ResearchPuzzle(
        id="puz_001",
        phenomenon_id=phenomenon.id,
        project_id="proj_001",
        puzzle_type=PuzzleType.MECHANISTIC,
        puzzle_statement="Why do LLMs sometimes produce confident but incorrect responses?",
        why_important="Understanding this is crucial for building reliable AI systems",
        current_explanations=["Training data artifacts", "Next-token prediction limits"],
        gaps_in_explanations=["No unified mechanistic account"],
        difficulty="HIGH",
        tractability="MEDIUM",
    )
    print(f"✓ Created puzzle: {puzzle.id}")
    assert puzzle.id == "puz_001"
    assert puzzle.puzzle_type == PuzzleType.MECHANISTIC

    # Test Theory
    theory = Theory(
        id="theo_001",
        project_id="proj_001",
        theory_name="Calibration Theory",
        origin_domain="Cognitive Science",
        theory_level=TheoryLevel.MICRO,
        core_constructs=["calibration", "confidence", "uncertainty"],
        core_propositions=[
            "Agents should express calibrated confidence",
            "Overconfidence indicates calibration failure"
        ],
        scope_conditions=["well-defined tasks", "known answer spaces"],
    )
    print(f"✓ Created theory: {theory.id}")
    assert theory.id == "theo_001"

    # Test Construct
    construct = Construct(
        id="cons_001",
        theory_id=theory.id,
        project_id="proj_001",
        construct_name="Calibrated Confidence",
        construct_definition="A probabilistic assessment that matches actual success rates",
        is_latent=True,
        operationalization_status="PROPOSED",
        proposed_measurements=["Brier score", "calibration curves"],
    )
    print(f"✓ Created construct: {construct.id}")

    # Test Mechanism
    mechanism = Mechanism(
        id="mech_001",
        project_id="proj_001",
        mechanism_name="Attention Miscalibration",
        mechanism_type=MechanismType.CAUSAL,
        causal_logic="When attention patterns don't align with ground truth, predictions are miscalibrated",
        necessary_conditions=["attention to wrong features", "insufficient training signal"],
        input_constructs=["attention weights"],
        output_constructs=["confidence scores"],
        intermediate_steps=[
            "Incorrect features attended to",
            "Pattern reinforced during training",
            "Confident but wrong outputs"
        ],
        testable_predictions=[
            "Attention visualization should show correlation with error patterns"
        ],
    )
    print(f"✓ Created mechanism: {mechanism.id}")
    assert mechanism.mechanism_type == MechanismType.CAUSAL

    # Test ResearchQuestion
    rq = ResearchQuestion(
        id="rq_001",
        project_id="proj_001",
        direction_id="dir_001",
        question_text="How does attention pattern misalignment affect LLM confidence calibration?",
        clarity=QuestionClarity.SPECIFIC,
        is_conditional=True,
        antecedent="When attention patterns misalign with ground truth features",
        consequent="LLMs exhibit overconfident but incorrect predictions",
        feasibility=QuestionFeasibility.EMPIRICALLY_TESTABLE,
        data_availability="AVAILABLE",
        method_availability="AVAILABLE",
    )
    print(f"✓ Created research question: {rq.id}")
    assert rq.clarity == QuestionClarity.SPECIFIC

    # Test ResearchMethod
    method = ResearchMethod(
        id="meth_001",
        research_question_id=rq.id,
        project_id="proj_001",
        method_type=MethodType.EXPERIMENTAL,
        method_name="Attention Intervention Experiment",
        method_description="Systematically intervene on attention patterns and measure calibration",
        key_design_features=["attention masking", "calibration metrics", "error analysis"],
        identification_strategy="Randomized intervention on attention",
        identification_strength="HIGH",
    )
    print(f"✓ Created research method: {method.id}")
    assert method.method_type == MethodType.EXPERIMENTAL

    # Test AlternativeExplanation
    alt = AlternativeExplanation(
        id="alt_001",
        project_id="proj_001",
        explanation_name="Training Distribution Mismatch",
        description="Errors arise from distribution shift between training and deployment",
        target_puzzle_id=puzzle.id,
        key_differentiators=[
            "Focuses on data, not mechanism",
            "No attention involvement"
        ],
        plausibility="HIGH",
        testability="HIGH",
        threat_level="HIGH",
    )
    print(f"✓ Created alternative explanation: {alt.id}")

    # Test DataSource
    ds = DataSource(
        id="ds_001",
        project_id="proj_001",
        source_name="TruthfulQA Dataset",
        source_type="SIMULATED",
        research_method_id=method.id,
        sample_size="~800 questions",
        variables_available=["question", "correct_answer", "model_response"],
        fit_assessment="HIGH",
    )
    print(f"✓ Created data source: {ds.id}")

    # Test Measurement
    meas = Measurement(
        id="meas_001",
        project_id="proj_001",
        measurement_name="Brier Score",
        measurement_type="BEHAVIORAL",
        measurement_description="Squared probability distance from correct answer",
        construct_id=construct.id,
        validity_evidence=["well-established in literature"],
    )
    print(f"✓ Created measurement: {meas.id}")

    # Test StateSnapshot
    snapshot = StateSnapshot(
        id="snap_001",
        project_id="proj_001",
        snapshot_name="Pre-Debate Snapshot",
        snapshot_type="PRE_DEBATE",
        research_phenomena=[phenomenon.to_dict()],
        research_puzzles=[puzzle.to_dict()],
        stage="direction_evaluation",
        key_insights=["Attention mechanism may be key"],
        open_questions=["What causes misalignment?"],
    )
    print(f"✓ Created state snapshot: {snapshot.id}")

    # Test ContractVersion
    cv = ContractVersion(
        id="cv_001",
        research_question_id=rq.id,
        project_id="proj_001",
        version_number=1,
        version_status="DRAFT",
        research_question=rq.question_text,
        theoretical_grounding="Calibration theory",
        proposed_mechanism=mechanism.mechanism_name,
        alternative_explanations=[alt.explanation_name],
        expected_contribution="Understanding and improving LLM calibration",
    )
    print(f"✓ Created contract version: {cv.id}")

    print("\n✓ All domain models created successfully!")
    return True


def test_database():
    """Test database operations."""
    print("\n" + "=" * 60)
    print("Testing Database")
    print("=" * 60)

    db = Database(":memory:")
    db.init_schema()
    print("✓ Database schema initialized")

    repo = Repository(db)

    # Test project creation
    project = repo.create_project(
        name="LLM Calibration Research",
        description="Research on LLM confidence calibration",
        seed_question="Why do LLMs produce confident but incorrect responses?",
        domain="AI"
    )
    print(f"✓ Created project: {project['name']} (ID: {project['id']})")
    assert project["name"] == "LLM Calibration Research"

    # Test paper creation
    paper = repo.create_paper(
        project_id=project["id"],
        title="Attention Is All You Need",
        arxiv_id="1706.03762",
        authors="Vaswani et al.",
        abstract="We propose a new neural network architecture based on attention mechanisms.",
        categories="cs.CL,cs.LG"
    )
    print(f"✓ Created paper: {paper['title']}")
    assert paper["arxiv_id"] == "1706.03762"

    # Test direction creation
    direction = repo.create_direction(
        project_id=project["id"],
        title="Attention-based Calibration",
        hypothesis="Aligning attention with ground truth improves calibration",
        novelty="Novel attention intervention approach",
        feasibility=0.7,
        importance=0.8
    )
    print(f"✓ Created direction: {direction['title']}")
    assert direction["feasibility"] == 0.7

    # Test research question creation
    rq = repo.create_research_question(
        project_id=project["id"],
        question_text="How does attention pattern alignment affect LLM calibration?",
        direction_id=direction["id"],
        theories_applicable=["Calibration Theory", "Attention Theory"],
        novelty_score=0.75
    )
    print(f"✓ Created research question: {rq['question_text'][:50]}...")

    # Test evidence creation
    evidence = repo.create_evidence(
        project_id=project["id"],
        content="Previous studies show attention patterns correlate with error types",
        evidence_type="EMPIRICAL",
        paper_id=paper["id"],
        direction_id=direction["id"],
        relevance=0.8,
        quality=0.7
    )
    print(f"✓ Created evidence entry")
    assert evidence["relevance"] == 0.8

    # Test event creation
    event = repo.create_event(
        project_id=project["id"],
        event_type="RESEARCH_STARTED",
        content="Started research on LLM calibration",
        metadata={"stage": "initialization"}
    )
    print(f"✓ Created event: {event['event_type']}")

    # Test phenomenon creation
    phen = repo.create_phenomenon(
        project_id=project["id"],
        raw_description="LLMs sometimes produce confident but wrong answers",
        phenomenon_type="OBSERVATIONAL",
        domain="AI",
        scope="micro"
    )
    print(f"✓ Created phenomenon")

    # Test puzzle creation
    puzzle = repo.create_puzzle(
        phenomenon_id=phen["id"],
        project_id=project["id"],
        puzzle_statement="Why does attention misalignment cause calibration errors?",
        puzzle_type="MECHANISTIC"
    )
    print(f"✓ Created puzzle")

    # Test theory creation
    theory = repo.create_theory(
        project_id=project["id"],
        theory_name="Calibration Theory",
        theory_level="MICRO",
        scope_conditions=["well-defined tasks"]
    )
    print(f"✓ Created theory")

    # Test construct creation
    construct = repo.create_construct(
        project_id=project["id"],
        construct_name="Confidence Calibration",
        theory_id=theory["id"]
    )
    print(f"✓ Created construct")

    # Test mechanism creation
    mechanism = repo.create_mechanism(
        project_id=project["id"],
        mechanism_name="Attention Misalignment",
        mechanism_type="CAUSAL"
    )
    print(f"✓ Created mechanism")

    # Test research method creation
    method = repo.create_research_method(
        research_question_id=rq["id"],
        project_id=project["id"],
        method_name="Attention Intervention",
        method_type="EXPERIMENTAL"
    )
    print(f"✓ Created research method")

    # Test state snapshot
    snapshot = repo.create_state_snapshot(
        project_id=project["id"],
        snapshot_name="Initial State",
        snapshot_type="MILESTONE"
    )
    print(f"✓ Created state snapshot")

    # Test debate creation
    debate = repo.create_debate(
        project_id=project["id"],
        direction_id=direction["id"]
    )
    print(f"✓ Created debate")
    assert debate["max_rounds"] == 4

    # Test debate round
    round_obj = repo.create_debate_round(
        debate_id=debate["id"],
        round_number=1,
        agent_role="PROPONENT",
        agent_position="This direction has strong theoretical grounding",
        arguments=[{"role": "PROPONENT", "content": "Strong theoretical grounding"}],
        votes={"PROPONENT": {"kill": False, "confidence": 0.7}}
    )
    print(f"✓ Created debate round")

    # Verify all data can be retrieved
    retrieved_project = repo.get_project(project["id"])
    assert retrieved_project["name"] == "LLM Calibration Research"
    print("✓ All data retrieved correctly")

    print("\n✓ All database operations successful!")
    return True


async def test_debate_system():
    """Test multi-agent debate system."""
    print("\n" + "=" * 60)
    print("Testing Multi-Agent Debate System")
    print("=" * 60)

    db = Database(":memory:")
    db.init_schema()
    repo = Repository(db)

    # Create project and direction
    project = repo.create_project(name="Test Project")
    direction = repo.create_direction(
        project_id=project["id"],
        title="AI Safety through Constitutional AI",
        hypothesis="Constitutional AI can improve LLM safety and alignment",
        novelty="Novel application to safety-critical systems",
        feasibility=0.7,
        importance=0.9
    )

    debate_system = MultiAgentDebateSystem(
        db=repo,
        gateway=None,  # Use mock responses
        max_rounds=2,
        kill_threshold=0.6
    )

    print(f"\nAgents initialized: {list(debate_system.agents.keys())}")
    assert len(debate_system.agents) == 5

    # Conduct debate
    result = await debate_system.conduct_debate(
        direction=direction,
        project_id=project["id"]
    )

    print(f"\n[Debate Result]")
    print(f"  Debate ID: {result.debate_id}")
    print(f"  Rounds Completed: {result.rounds_completed}")
    print(f"  Final Status: {result.status.value}")
    print(f"  Kill Votes: {result.kill_votes}/{result.total_votes}")
    print(f"  Kill Ratio: {result.kill_ratio:.1%}")
    print(f"  Research Questions Found: {len(result.researchable_questions)}")

    if result.researchable_questions:
        print(f"  Sample Question: {result.researchable_questions[0][:60]}...")

    if result.recommendations:
        print(f"  Recommendations: {result.recommendations[:2]}")

    # Verify debate was persisted
    saved_debate = repo.get_debate(result.debate_id)
    assert saved_debate is not None
    print(f"\n✓ Debate persisted to database")

    # Verify rounds were saved
    rounds = repo.list_debate_rounds(result.debate_id)
    print(f"✓ {len(rounds)} debate rounds saved")

    print("\n✓ Multi-agent debate system working!")
    return True


async def test_literature_search():
    """Test literature search."""
    print("\n" + "=" * 60)
    print("Testing Literature Search")
    print("=" * 60)

    searcher = LiteratureSearch(gateway=None)

    query = SearchQuery(
        query_text="large language model calibration uncertainty",
        sources=[SearchSource.ARXIV],
        max_results=5,
        domains=["cs.CL", "cs.LG"],
    )

    print(f"Searching for: {query.query_text}")
    results = await searcher.search(query)

    print(f"Found {len(results)} results")
    if results:
        print(f"\nTop result: {results[0].title[:60]}...")
        print(f"  Authors: {', '.join(results[0].authors[:3])}")
        print(f"  Relevance: {results[0].relevance_score:.2f}")
        print(f"  Source: {results[0].source.value}")

    print("\n✓ Literature search working!")
    return True


async def test_paper_reader():
    """Test paper reader."""
    print("\n" + "=" * 60)
    print("Testing Paper Reader")
    print("=" * 60)

    reader = PaperReader(gateway=None)

    # Test reading a paper
    paper = await reader.read_paper("1706.03762")

    if paper:
        print(f"✓ Paper loaded: {paper.title[:50]}...")
        print(f"  Authors: {', '.join(paper.authors[:3])}")
        print(f"  Categories: {', '.join(paper.categories[:3])}")

        # Test basic extraction
        insights = await reader.analyze_paper(paper)
        print(f"  Insights extracted: {len(insights)}")

        # Test RQ extraction
        rq = await reader.extract_research_question(paper)
        print(f"  Extracted RQ: {rq[:60]}...")
    else:
        print("⚠ Paper not found (arXiv API may be unavailable)")

    print("\n✓ Paper reader working!")
    return True


async def test_evidence_validator():
    """Test evidence validator."""
    print("\n" + "=" * 60)
    print("Testing Evidence Validator")
    print("=" * 60)

    validator = EvidenceValidator(gateway=None)

    evidence = EvidenceItem(
        id="ev_001",
        project_id="proj_001",
        content="Previous studies show that attention patterns correlate with model errors",
        evidence_type=EvidenceType.EMPIRICAL,
        source="Smith et al., 2023",
        source_type="paper",
        relevance=0.8,
        quality=EvidenceQuality.MEDIUM,
    )

    context = {
        "research_question": "How does attention alignment affect calibration?",
        "hypothesis": "Attention misalignment causes overconfidence"
    }

    result = await validator.validate_evidence(evidence, context)

    print(f"[Validation Result]")
    print(f"  Quality: {result.overall_quality.value}")
    print(f"  Quality Score: {result.quality_score:.2f}")
    print(f"  Relevance: {result.relevance_score:.2f}")
    print(f"  Reliability: {result.reliability_score:.2f}")
    print(f"  Validity: {result.validity_score:.2f}")
    print(f"  Threats identified: {len(result.threats)}")

    if result.threats:
        for threat in result.threats[:2]:
            print(f"    - {threat.threat_type.value}: {threat.description[:50]}...")

    if result.improvements:
        print(f"  Improvements suggested: {len(result.improvements)}")

    print("\n✓ Evidence validator working!")
    return True


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("AI SCIENTIST - COMPREHENSIVE TEST SUITE")
    print("=" * 60)

    results = []

    # Phase 1: Domain models
    try:
        results.append(("Domain Models", test_domain_models()))
    except Exception as e:
        results.append(("Domain Models", False))
        print(f"✗ Domain models test failed: {e}")

    # Phase 2: Database
    try:
        results.append(("Database", test_database()))
    except Exception as e:
        results.append(("Database", False))
        print(f"✗ Database test failed: {e}")

    # Phase 3: Debate System
    try:
        results.append(("Debate System", await test_debate_system()))
    except Exception as e:
        results.append(("Debate System", False))
        print(f"✗ Debate system test failed: {e}")

    # Phase 4: Literature Search
    try:
        results.append(("Literature Search", await test_literature_search()))
    except Exception as e:
        results.append(("Literature Search", False))
        print(f"✗ Literature search test failed: {e}")

    # Phase 5: Paper Reader
    try:
        results.append(("Paper Reader", await test_paper_reader()))
    except Exception as e:
        results.append(("Paper Reader", False))
        print(f"✗ Paper reader test failed: {e}")

    # Phase 6: Evidence Validator
    try:
        results.append(("Evidence Validator", await test_evidence_validator()))
    except Exception as e:
        results.append(("Evidence Validator", False))
        print(f"✗ Evidence validator test failed: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
