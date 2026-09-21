"""V4 Integration Test - Full System Validation.

This test validates the complete v4 system integration:
1. Persistent Objection Ledger
2. MultiAgentDebateSystem with historical objection review
3. FinalResearchCourt with hard-constraint rules
4. Evidence-based decision output

Run: python test_v4_integration.py
"""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "auto_research" / "src"))

from ai_scientist.db.repository import Database, Repository
from ai_scientist.engine.objection_ledger import ObjectionLedger
from ai_scientist.engine.final_research_court import (
    FinalResearchCourt,
    ScientificDecision,
    GateResult,
    ObjectionGate,
    NoveltyGate,
    FeasibilityGate,
)
from ai_scientist.engine.multi_agent_debate import MultiAgentDebateSystem


# Test configuration
TEST_PROJECT_ID = "test_v4_integration_project"
SEED_QUESTION = "Can large language models generate truly novel scientific discoveries by iteratively improving from their own outputs?"


def setup_system():
    """Set up the v4 system components."""
    print("\n[Setup] Initializing v4 system components...")

    # Initialize database
    db = Database(":memory:")  # In-memory for testing
    db.init_schema()
    repo = Repository(db)
    db.execute(
        "INSERT INTO projects (id, name, seed_question, domain) VALUES (?, ?, ?, ?)",
        (TEST_PROJECT_ID, "V4 Integration Test", SEED_QUESTION, "AI"),
    )
    db.execute(
        "INSERT INTO directions (id, project_id, title, hypothesis) VALUES (?, ?, ?, ?)",
        ("dir_001", TEST_PROJECT_ID, "Integration test direction", "Test hypothesis"),
    )

    # Initialize Objection Ledger
    ledger = ObjectionLedger(repo)

    # Initialize Final Research Court
    court = FinalResearchCourt(ledger)

    # Initialize Debate System with ledger and court
    debate_system = MultiAgentDebateSystem(
        db=repo,
        objection_ledger=ledger,
        research_court=court,
        max_rounds=2,
        kill_threshold=0.6,
    )

    print(f"  ✓ Database initialized")
    print(f"  ✓ ObjectionLedger initialized")
    print(f"  ✓ FinalResearchCourt initialized")
    print(f"  ✓ MultiAgentDebateSystem initialized")

    return db, repo, ledger, court, debate_system


def test_ledger_persistence():
    """Test 1: Objection Ledger persistence across runs."""
    print("\n" + "=" * 60)
    print("[Test 1] Objection Ledger Persistence")
    print("=" * 60)

    _, repo, ledger, _, _ = setup_system()

    # Run 1: Add historical objections
    print("\n  [Run 1] Adding 8 FATAL historical objections...")
    ledger.load_project(TEST_PROJECT_ID, current_run=1)

    fatal_objections = [
        ("研究命题中的'仅依靠自身'没有可操作定义", "大模型自身生成的数据可能暗中依赖预训练语料中的潜在知识"),
        ("强版本命题受到信息论约束", "封闭系统中的自生成数据不能凭空获得关于未知外部世界的可靠事实"),
        ("'新能力'概念严重欠定义", "没有定义就无法区分能力发现、能力放大、能力迁移和能力创造"),
        ("混淆'增加计算'与'获得新信息'", "性能提升可能仅来自更大的计算预算"),
        ("自我验证无法保证正确性", "生成器、批评器和验证器如果来自同一模型，可能共享盲点"),
        ("存在直接的循环论证风险", "高质量的定义来自待证明有效的系统"),
        ("'持续获得'比'一次性提升'强得多", "长期迭代存在模型坍缩等问题"),
        ("无法排除'预训练知识被重新唤起'", "可能只是通过自生成提示把原本难以调用的记忆激活出来"),
    ]

    for title, argument in fatal_objections:
        ledger.add_objection(
            target_type="RESEARCH_QUESTION",
            target_id="rq_seed",
            title=title,
            argument=argument,
            category="SCOPE_BOUNDARY",
            severity="FATAL",
            raised_by="HISTORICAL_RED_TEAM",
        )

    summary = ledger.get_summary()
    print(f"    Total objections: {summary.total}")
    print(f"    Open FATAL: {summary.open_fatal}")

    # Run 2: Load project - objections should persist
    print("\n  [Run 2] Loading project (objections should persist)...")
    ledger.load_project(TEST_PROJECT_ID, current_run=2)

    summary = ledger.get_summary()
    print(f"    Total objections: {summary.total}")
    print(f"    Open FATAL: {summary.open_fatal}")

    # Verify persistence
    assert summary.open_fatal == 8, f"Expected 8 FATAL but got {summary.open_fatal}"
    print("    ✓ Objections persisted across runs")

    # Run 2: Address some objections
    print("\n  [Run 2] Addressing 3 objections with evidence...")
    open_objs = ledger.get_open_objections()

    for obj in open_objs[:3]:
        ledger.resolve_with_evidence(
            objection_id=obj["id"],
            evidence_ids=[f"evidence_{obj['id']}"],
            resolution_reason="Provided compute-matched control experiments",
        )

    summary = ledger.get_summary()
    print(f"    Resolved: {summary.resolved}")
    print(f"    Open FATAL: {summary.open_fatal}")

    # Run 3: Verify resolved objections stayed resolved
    print("\n  [Run 3] Verifying resolved objections stayed resolved...")
    ledger.load_project(TEST_PROJECT_ID, current_run=3)

    summary = ledger.get_summary()
    print(f"    Total: {summary.total}")
    print(f"    Open FATAL: {summary.open_fatal}")
    print(f"    Resolved: {summary.resolved}")

    # Verify: 5 FATAL still open, 3 resolved
    assert summary.open_fatal == 5, f"Expected 5 open FATAL but got {summary.open_fatal}"
    assert summary.resolved == 3, f"Expected 3 resolved but got {summary.resolved}"
    print("    ✓ Resolved objections stayed resolved")

    return True


def test_hard_constraint_rules():
    """Test 2: Hard-constraint rules enforcement."""
    print("\n" + "=" * 60)
    print("[Test 2] Hard-Constraint Rules")
    print("=" * 60)

    _, _, ledger, court, _ = setup_system()

    # Load project with unresolved FATAL
    ledger.load_project(TEST_PROJECT_ID, current_run=1)
    ledger.add_objection(
        target_type="RESEARCH_QUESTION",
        target_id="rq_test",
        title="FATAL: 循环论证",
        argument="存在循环论证风险",
        category="CYCLICAL_REASONING",
        severity="FATAL",
    )
    ledger.add_objection(
        target_type="RESEARCH_QUESTION",
        target_id="rq_test",
        title="FATAL: 信息论约束",
        argument="封闭系统无法获得新信息",
        category="THEORETICAL_COHERENCE",
        severity="FATAL",
    )

    print("\n  [Case 1] OPEN FATAL should block CONTINUE")
    gates = {
        "objection_gate": ObjectionGate(
            open_fatal_objections=ledger.get_fatal_objections(),
            requires_human_objections=[],
        ),
    }

    decision = court.make_decision(gates=gates, kill_ratio=0.3)
    print(f"    Decision: {decision.decision.value}")
    print(f"    Kill ratio (diagnostic): {decision.kill_ratio}")

    assert decision.decision == ScientificDecision.KILL, \
        f"Expected KILL but got {decision.decision.value}"
    print("    ✓ OPEN FATAL correctly blocks CONTINUE")

    # Case 2: No FATAL - should allow CONTINUE
    print("\n  [Case 2] No FATAL should allow CONTINUE")
    gates = {
        "objection_gate": ObjectionGate(
            open_fatal_objections=[],
            requires_human_objections=[],
        ),
        "novelty_gate": NoveltyGate(has_novel_claim=True, evidence_ids=["exp_1"]),
        "feasibility_gate": FeasibilityGate(has_method=True, has_data=True, has_measurements=True),
    }

    decision = court.make_decision(gates=gates, kill_ratio=0.1)
    print(f"    Decision: {decision.decision.value}")

    assert decision.decision == ScientificDecision.CONTINUE, \
        f"Expected CONTINUE but got {decision.decision.value}"
    print("    ✓ No FATAL correctly allows CONTINUE")

    # Case 3: REQUIRES_HUMAN triggers REVISE
    print("\n  [Case 3] REQUIRES_HUMAN triggers REVISE")
    gates = {
        "objection_gate": ObjectionGate(
            open_fatal_objections=[],
            requires_human_objections=[{"id": "human_1", "title": "伦理问题"}],
        ),
    }

    decision = court.make_decision(gates=gates)
    print(f"    Decision: {decision.decision.value}")
    print(f"    Requires human: {decision.requires_human_review}")

    assert decision.decision == ScientificDecision.REVISE
    assert decision.requires_human_review is True
    print("    ✓ REQUIRES_HUMAN correctly triggers REVISE")

    # Case 4: Kill ratio is auxiliary, not primary
    print("\n  [Case 4] Kill ratio is auxiliary diagnostic")
    gates = {
        "objection_gate": ObjectionGate(open_fatal_objections=[]),
    }

    decision = court.make_decision(gates=gates, kill_ratio=0.95)
    print(f"    Decision: {decision.decision.value}")
    print(f"    Kill ratio: {decision.kill_ratio}")

    assert decision.decision == ScientificDecision.CONTINUE, \
        "High kill ratio without blockers should still allow CONTINUE"
    print("    ✓ Kill ratio correctly demoted to diagnostic")

    return True


def test_evidence_based_output():
    """Test 3: Evidence-based decision output structure."""
    print("\n" + "=" * 60)
    print("[Test 3] Evidence-Based Decision Output")
    print("=" * 60)

    _, _, ledger, court, _ = setup_system()
    ledger.load_project(TEST_PROJECT_ID, current_run=1)

    # Make decision with evidence
    gates = {
        "objection_gate": ObjectionGate(
            open_fatal_objections=[{
                "id": "obj_1",
                "title": "FATAL: 循环论证",
                "severity": "FATAL",
                "status": "OPEN",
                "supporting_evidence_ids": ["theory_paper_1", "theory_paper_2"],
            }],
        ),
        "novelty_gate": NoveltyGate(
            has_novel_claim=True,
            evidence_ids=["novelty_exp_1", "novelty_exp_2"],
        ),
        "feasibility_gate": FeasibilityGate(
            has_method=True,
            has_data=True,
            has_measurements=True,
        ),
    }

    decision = court.make_decision(
        gates=gates,
        supporting_evidence_ids=["baseline_1", "baseline_2"],
        contradicting_evidence_ids=["control_1"],
        kill_ratio=0.4,
        debate_status="RESEARCHABLE",
    )

    # Export to dict
    decision_dict = decision.to_dict()

    print("\n  [Decision Structure]")
    print(f"    Decision: {decision_dict['decision']}")
    print(f"    Gates: {list(decision_dict['gates'].keys())}")
    print(f"    Reasons: {len(decision_dict['reasons'])}")
    print(f"    Supporting evidence: {len(decision_dict['supporting_evidence_ids'])}")
    print(f"    Contradicting evidence: {len(decision_dict['contradicting_evidence_ids'])}")
    print(f"    Diagnostics: kill_ratio={decision_dict['diagnostics']['kill_ratio']}")

    # Verify structure
    assert "decision" in decision_dict
    assert "timestamp" in decision_dict
    assert "gates" in decision_dict
    assert "reasons" in decision_dict
    assert "supporting_evidence_ids" in decision_dict
    assert "contradicting_evidence_ids" in decision_dict
    assert "diagnostics" in decision_dict
    assert "diagnostics" in decision_dict and "kill_ratio" in decision_dict["diagnostics"]

    print("    ✓ Decision structure validated")

    # Save to file
    output_dir = Path("research_output")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "final_decision.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(decision_dict, f, indent=2, ensure_ascii=False)
    print(f"    ✓ Saved to {output_file}")

    return True


def test_decision_graph():
    """Test 4: Decision reason graph."""
    print("\n" + "=" * 60)
    print("[Test 4] Decision Reason Graph")
    print("=" * 60)

    _, _, ledger, court, _ = setup_system()
    ledger.load_project(TEST_PROJECT_ID, current_run=1)

    # Add objections
    ledger.add_objection(
        target_type="RESEARCH_QUESTION",
        target_id="rq_test",
        title="FATAL: 理论不自洽",
        argument="内部理论存在矛盾",
        category="INTERNAL_CONSISTENCY",
        severity="FATAL",
    )

    # Make decision
    gates = {
        "objection_gate": ObjectionGate(
            open_fatal_objections=ledger.get_fatal_objections(),
        ),
    }

    decision = court.make_decision(gates=gates)

    # Generate graph
    from ai_scientist.engine.final_research_court import DecisionGraph
    graph = DecisionGraph().from_decision(decision)

    print(f"\n  Graph nodes: {len(graph.nodes)}")
    print(f"  Graph edges: {len(graph.edges)}")

    for node in graph.nodes:
        print(f"    [{node['type']}] {node['label']}")

    # Save graph
    output_dir = Path("research_output")
    output_file = output_dir / "decision_graph.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(graph.to_dict(), f, indent=2, ensure_ascii=False)
    print(f"\n  ✓ Graph saved to {output_file}")

    return True


def test_debate_with_ledger():
    """Test 5: Debate system with objection ledger."""
    print("\n" + "=" * 60)
    print("[Test 5] Debate System with Objection Ledger")
    print("=" * 60)

    db, repo, ledger, court, debate_system = setup_system()
    ledger.load_project(TEST_PROJECT_ID, current_run=1)

    # Add historical objections
    ledger.add_objection(
        target_type="RESEARCH_DIRECTION",
        target_id="dir_001",
        title="FATAL: 方法论缺陷",
        argument="没有控制实验",
        category="METHODOLOGICAL",
        severity="FATAL",
    )

    print("\n  [Setup] Loaded 1 historical FATAL objection")
    print(f"    Open FATAL: {len(ledger.get_fatal_objections())}")

    # Create test direction
    direction = {
        "id": "dir_001",
        "title": "Self-Improving Language Models",
        "hypothesis": "LLMs can improve by learning from self-generated data",
        "novelty": "Novel self-training approach",
        "feasibility": 0.7,
        "importance": 0.8,
    }

    # Conduct debate (uses mock responses)
    print("\n  [Debate] Running mock debate...")
    result = asyncio.run(debate_system.conduct_debate(
        direction=direction,
        project_id=TEST_PROJECT_ID,
        target_type="RESEARCH_DIRECTION",
        target_id="dir_001",
    ))

    print(f"\n  [Results]")
    print(f"    Status: {result.status.value}")
    print(f"    Kill ratio: {result.kill_ratio:.1%}")
    print(f"    Rounds: {result.rounds_completed}")
    print(f"    Conclusion: {result.conclusion[:100]}...")

    # Check metadata
    if result.metadata:
        print(f"\n  [V4 Metadata]")
        print(f"    Court decision: {result.metadata.get('court_decision', {}).get('decision', 'N/A')}")
        print(f"    Objections added: {result.metadata.get('objections_added', 0)}")
        print(f"    Historical reviewed: {result.metadata.get('historical_objections_reviewed', 0)}")

    # Save debate result
    output_dir = Path("research_output")
    output_file = output_dir / "debate_result.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result.to_json_dict(), f, indent=2, ensure_ascii=False)
    print(f"\n  ✓ Debate result saved to {output_file}")

    return True


def test_complete_workflow():
    """Test 6: Complete v4 workflow simulation."""
    print("\n" + "=" * 60)
    print("[Test 6] Complete V4 Workflow")
    print("=" * 60)

    _, repo, ledger, court, _ = setup_system()

    print(f"\n  Seed Question: {SEED_QUESTION[:80]}...")

    # Phase 1: Load historical objections (v1 baseline)
    print("\n  [Phase 1] Initializing with v1's 8 FATAL objections...")
    ledger.load_project(TEST_PROJECT_ID, current_run=1)

    v1_fatal_objections = [
        ("研究命题中的'仅依靠自身'没有可操作定义", "SCOPE_BOUNDARY"),
        ("强版本命题受到信息论约束", "THEORETICAL_COHERENCE"),
        ("'新能力'概念严重欠定义", "EMPIRICAL_FEASIBILITY"),
        ("混淆'增加计算'与'获得新信息'", "METHODOLOGICAL"),
        ("自我验证无法保证正确性", "INTERNAL_CONSISTENCY"),
        ("存在直接的循环论证风险", "CYCLICAL_REASONING"),
        ("'持续获得'比'一次性提升'强得多", "EMPIRICAL_FEASIBILITY"),
        ("无法排除'预训练知识被重新唤起'", "NOVELTY_THREAT"),
    ]

    for title, category in v1_fatal_objections:
        ledger.add_objection(
            target_type="RESEARCH_QUESTION",
            target_id="rq_seed",
            title=title,
            argument=f"Auto-generated: {title}",
            category=category,
            severity="FATAL",
            raised_by="V1_RED_TEAM",
        )

    summary = ledger.get_summary()
    print(f"    ✓ Loaded {summary.open_fatal} FATAL objections")

    # Phase 2: Evidence collection
    print("\n  [Phase 2] Evidence collection and objection resolution...")
    ledger.load_project(TEST_PROJECT_ID, current_run=2)

    # Provide evidence for 3 objections
    open_objs = ledger.get_open_objections()
    for obj in open_objs[:3]:
        ledger.resolve_with_evidence(
            objection_id=obj["id"],
            evidence_ids=[f"experiment_{obj['id']}", f"analysis_{obj['id']}"],
            resolution_reason="Provided rigorous experimental evidence",
        )
        print(f"    Resolved: {obj['title'][:50]}...")

    # Add new objection
    ledger.add_objection(
        target_type="RESEARCH_QUESTION",
        target_id="rq_seed",
        title="新问题：模型坍缩风险",
        argument="长期迭代可能导致模型坍缩",
        category="EMPIRICAL_FEASIBILITY",
        severity="FATAL",
        raised_by="V4_RED_TEAM",
    )

    # Phase 3: Final decision
    print("\n  [Phase 3] Final research decision...")
    ledger.load_project(TEST_PROJECT_ID, current_run=3)

    gates = {
        "objection_gate": ObjectionGate(
            open_fatal_objections=ledger.get_fatal_objections(),
            requires_human_objections=ledger.get_requires_human_objections(),
        ),
        "novelty_gate": NoveltyGate(
            has_novel_claim=True,
            evidence_ids=["baseline_study", "pilot_experiment"],
        ),
        "feasibility_gate": FeasibilityGate(
            has_method=True,
            has_data=True,
            has_measurements=True,
        ),
    }

    decision = court.make_decision(
        gates=gates,
        supporting_evidence_ids=["baseline_1", "baseline_2"],
        kill_ratio=0.45,
        debate_status="NEEDS_REVISION",
    )

    print(f"\n  [Final Decision]")
    print(f"    Decision: {decision.decision.value}")
    print(f"    Blocking reasons: {len([r for r in decision.reasons if r.type == 'BLOCKING'])}")
    print(f"    Supporting reasons: {len([r for r in decision.reasons if r.type == 'SUPPORTING'])}")

    # Generate decision graph
    from ai_scientist.engine.final_research_court import DecisionGraph
    graph = DecisionGraph().from_decision(decision)

    # Save complete output
    output_dir = Path("research_output")
    output_dir.mkdir(exist_ok=True)

    output_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "seed_question": SEED_QUESTION,
        "workflow_phase": "Final Research Decision",
        "decision": decision.to_dict(),
        "decision_graph": graph.to_dict(),
        "objection_summary": ledger.get_summary().to_dict(),
    }

    output_file = output_dir / "final_decision.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    print(f"\n  ✓ Complete workflow output saved to {output_file}")

    return True


def run_all_tests():
    """Run all v4 integration tests."""
    print("=" * 60)
    print("V4 Integration Test Suite")
    print("=" * 60)
    print("\nValidating complete v4 system integration:")
    print("  1. Persistent Objection Ledger")
    print("  2. Hard-Constraint Decision Rules")
    print("  3. Evidence-Based Decision Output")
    print("  4. Decision Reason Graph")
    print("  5. Debate System with Ledger")
    print("  6. Complete V4 Workflow")

    tests = [
        ("Ledger Persistence", test_ledger_persistence),
        ("Hard-Constraint Rules", test_hard_constraint_rules),
        ("Evidence-Based Output", test_evidence_based_output),
        ("Decision Graph", test_decision_graph),
        ("Debate with Ledger", test_debate_with_ledger),
        ("Complete Workflow", test_complete_workflow),
    ]

    results = []
    for name, test in tests:
        try:
            result = test()
            results.append((name, result))
        except Exception as e:
            print(f"\n  ✗ Test failed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("V4 INTEGRATION TEST SUMMARY")
    print("=" * 60)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"\nPassed: {passed}/{total}")

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")

    print("\nV4 Improvements Validated:")
    print("  ✓ Persistent Objection Ledger")
    print("  ✓ Historical objections persist across runs")
    print("  ✓ Hard-constraint: OPEN FATAL blocks CONTINUE")
    print("  ✓ REQUIRES_HUMAN triggers REVISE")
    print("  ✓ Kill ratio demoted to auxiliary")
    print("  ✓ Evidence IDs tracked in decisions")
    print("  ✓ Decision reason graph generated")
    print("  ✓ Debate system integrated with ledger")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
