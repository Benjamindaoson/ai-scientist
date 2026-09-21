"""Phase 6: End-to-End Vertical Test

Research seed: "人工智能智能体从失败中学习"
(AI agents learning from failures)

This test runs the full research pipeline from seed to research questions.
"""
import asyncio
import sys
import os

# Add project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from ai_scientist.orchestrator import AIScientist
from ai_scientist.core.gateway import MockGateway, ClaudeRelayGateway


async def main():
    """Run the end-to-end research pipeline."""
    print("=" * 70)
    print("AI SCIENTIST - PHASE 6 END-TO-END VERTICAL TEST")
    print("Research Seed: 人工智能智能体从失败中学习")
    print("(AI Agents Learning from Failures)")
    print("=" * 70)

    # Force correct configuration
    os.environ["ANTHROPIC_API_KEY"] = "sk-CsvX9nQ2XsyZxF6nwR8uucvCUbfXN2hYp5CWD7tL6ECCdK1E"
    os.environ["ANTHROPIC_BASE_URL"] = "https://api.jingziai.club/v1"
    os.environ["DEFAULT_MODEL"] = "gpt-5.6-sol"

    # Use real API gateway
    gateway = ClaudeRelayGateway(
        relay_url="https://api.jingziai.club/v1",
        api_key="sk-CsvX9nQ2XsyZxF6nwR8uucvCUbfXN2hYp5CWD7tL6ECCdK1E",
        model="gpt-5.6-sol",
        max_tokens=1024,
    )

    # Create AI Scientist instance
    ai_scientist = AIScientist(
        db_path=":memory:",
        gateway=gateway,
        max_literature_results=10,
    )

    # Run the full pipeline
    seed_question = "人工智能智能体从失败中学习"

    print("\n[1/6] Starting research session...")
    session = await ai_scientist.start_research(
        seed_question=seed_question,
        project_name="AI Agent Learning from Failures",
        domain="AI/ML",
    )
    print(f"✓ Session started: {session.session_id}")
    print(f"  Project ID: {session.project_id}")

    print("\n[2/6] Searching literature...")
    papers = await ai_scientist.search_literature(seed_question, max_results=5)
    print(f"✓ Found {len(papers)} papers")
    for i, paper in enumerate(papers[:3], 1):
        print(f"  {i}. {paper.title[:60]}...")
        print(f"     Authors: {', '.join(paper.authors) if paper.authors else 'Unknown'}")

    print("\n[3/6] Identifying research phenomenon...")
    phenomenon = await ai_scientist.identify_phenomenon(
        observation="AI agents often repeat mistakes without learning from failures",
        domain="AI/ML",
    )
    print(f"✓ Phenomenon identified: {phenomenon.id}")
    print(f"  Description: {phenomenon.raw_description}")

    print("\n[4/6] Formulating research puzzle...")
    from ai_scientist.core.models.domain import PuzzleType
    puzzle = await ai_scientist.formulate_puzzle(
        phenomenon=phenomenon,
        puzzle_type=PuzzleType.MECHANISTIC,
    )
    print(f"✓ Puzzle formulated: {puzzle.id}")
    print(f"  Statement: {puzzle.puzzle_statement}")

    print("\n[5/6] Generating research questions...")
    questions = await ai_scientist.generate_research_questions(phenomenon, puzzle)
    print(f"✓ Generated {len(questions)} research questions")
    for i, q in enumerate(questions, 1):
        print(f"  {i}. {q.question_text[:70]}...")

    print("\n[6/6] Developing theory...")
    theory = await ai_scientist.develop_theory(
        theory_name="Failure-Aware Learning Theory",
        core_claim="AI agents can improve through explicit failure analysis and adaptation",
    )
    print(f"✓ Theory started: {theory.theory_id}")
    print(f"  Name: {theory.theory_name}")
    print(f"  Status: {theory.status.value}")

    # Test theory engine
    from ai_scientist.engine.theory_engine import TheoryComponentType
    ai_scientist.theory_engine.add_component(
        theory_id=theory.theory_id,
        component_type=TheoryComponentType.CONSTRUCT,
        name="Failure Pattern",
        description="Recurring patterns in agent failures",
    )
    ai_scientist.theory_engine.add_component(
        theory_id=theory.theory_id,
        component_type=TheoryComponentType.CONSTRUCT,
        name="Recovery Strategy",
        description="Methods for recovering from failures",
    )
    ai_scientist.theory_engine.add_mechanism_pathway(
        theory_id=theory.theory_id,
        pathway_name="Failure Learning Loop",
        steps=[
            "Detect failure state",
            "Analyze failure patterns",
            "Formulate recovery strategy",
            "Execute and validate",
        ],
        input_conditions=["Agent in failure state", "Failure data available"],
        output_predictions=["Improved agent performance", "Reduced failure rate"],
    )

    # Evaluate theory
    evaluation = ai_scientist.theory_engine.evaluate_theory(theory.theory_id)
    print(f"\n  Theory Evaluation:")
    print(f"    Overall Score: {evaluation.overall_score:.2f}")
    print(f"    Coherence: {evaluation.coherence:.2f}")
    print(f"    Testability: {evaluation.testability:.2f}")
    print(f"    Explanatory Power: {evaluation.explanatory_power:.2f}")
    print(f"    Predictive Power: {evaluation.predictive_power:.2f}")

    # Test debate system
    print("\n" + "-" * 70)
    print("Testing Multi-Agent Debate System")
    print("-" * 70)

    direction = {
        "id": "dir_test",
        "title": "Failure-Aware Reinforcement Learning",
        "hypothesis": "Agents that explicitly analyze failures learn faster",
        "novelty": "Novel integration of failure analysis in RL",
        "feasibility": 0.7,
        "importance": 0.9,
    }

    debate_result = await ai_scientist.evaluate_direction(direction, max_rounds=2)
    print(f"\n  Debate Result:")
    print(f"    Status: {debate_result.status.value}")
    print(f"    Rounds: {debate_result.rounds_completed}")
    print(f"    Kill Ratio: {debate_result.kill_ratio:.1%}")
    print(f"    Questions Found: {len(debate_result.researchable_questions)}")

    # Test evidence validation
    print("\n" + "-" * 70)
    print("Testing Evidence Validation")
    print("-" * 70)

    from ai_scientist.literature.validator import EvidenceType
    evidence_result = await ai_scientist.validate_evidence(
        evidence_content="Studies show that agents with explicit failure memory perform 15% better",
        evidence_type=EvidenceType.EMPIRICAL,
    )
    print(f"\n  Validation Result:")
    print(f"    Quality: {evidence_result.overall_quality.value}")
    print(f"    Score: {evidence_result.quality_score:.2f}")
    print(f"    Validity: {evidence_result.validity_score:.2f}")
    print(f"    Relevance: {evidence_result.relevance_score:.2f}")
    print(f"    Threats: {len(evidence_result.threats)}")

    # Summary
    print("\n" + "=" * 70)
    print("PHASE 6 TEST COMPLETE")
    print("=" * 70)
    print(f"""
Summary:
- Session: {session.session_id}
- Project: {session.project_id}
- Literature: {len(papers)} papers found
- Phenomenon: {phenomenon.id}
- Puzzle: {puzzle.id}
- Research Questions: {len(questions)} generated
- Theory: {theory.theory_id} (Score: {evaluation.overall_score:.2f})
- Debate: {debate_result.status.value} ({debate_result.kill_ratio:.1%} kill)
- Evidence Validated: {evidence_result.overall_quality.value}

All Phase 6 components are working!
    """)

    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        if result:
            print("\n✅ Phase 6 END-TO-END TEST PASSED")
            sys.exit(0)
        else:
            print("\n❌ Phase 6 END-TO-END TEST FAILED")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during Phase 6 test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
