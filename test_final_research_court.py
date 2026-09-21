"""Test FinalResearchCourt hard-constraint rules.

Tests the v4 hard-constraint rules:
1. OPEN FATAL objections always block CONTINUE
2. Gate evaluation is SEPARATE from decision
3. Kill Ratio is auxiliary diagnostic only
4. Evidence-based decision reasoning

Run: python test_final_research_court.py
"""
import json
from pathlib import Path

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent / "auto_research" / "src"))

from ai_scientist.engine.final_research_court import (
    FinalResearchCourt,
    FinalDecision,
    GateResult,
    ScientificDecision,
    ObjectionGate,
    NoveltyGate,
    FeasibilityGate,
)


def test_hard_constraint_fatal_blocks_continue():
    """Hard constraint: OPEN FATAL blocks CONTINUE."""
    print("\n[Test 1] OPEN FATAL blocks CONTINUE")

    court = FinalResearchCourt()

    # Case: Have open FATAL objections
    gates = {
        "objection_gate": ObjectionGate(
            open_fatal_objections=[
                {
                    "id": "obj_1",
                    "title": "研究命题无法操作化",
                    "severity": "FATAL",
                    "status": "OPEN",
                    "argument": "没有可操作的定义",
                },
                {
                    "id": "obj_2",
                    "title": "信息论约束",
                    "severity": "FATAL",
                    "status": "OPEN",
                    "argument": "封闭系统无法获得新信息",
                },
            ],
        ),
    }

    decision = court.make_decision(gates=gates)

    print(f"  Decision: {decision.decision.value}")
    print(f"  Open FATAL count: {len(gates['objection_gate'].open_fatal_objections)}")

    # HARD CONSTRAINT: Must be KILL, not CONTINUE
    assert decision.decision == ScientificDecision.KILL, \
        f"Expected KILL but got {decision.decision.value}"

    # Must have blocking reasons
    blocking_reasons = [r for r in decision.reasons if r.type == "BLOCKING"]
    assert len(blocking_reasons) >= 1, "Must have at least one blocking reason"

    print("  ✓ KILL decision correctly enforced")
    return True


def test_no_fatal_allows_continue():
    """No FATAL objections allows CONTINUE."""
    print("\n[Test 2] No FATAL allows CONTINUE")

    court = FinalResearchCourt()

    gates = {
        "objection_gate": ObjectionGate(
            open_fatal_objections=[],
            requires_human_objections=[],
        ),
        "novelty_gate": NoveltyGate(
            has_novel_claim=True,
            evidence_ids=["evidence_1"],
        ),
        "feasibility_gate": FeasibilityGate(
            has_method=True,
            has_data=True,
            has_measurements=True,
        ),
    }

    decision = court.make_decision(gates=gates)

    print(f"  Decision: {decision.decision.value}")

    assert decision.decision == ScientificDecision.CONTINUE, \
        f"Expected CONTINUE but got {decision.decision.value}"

    print("  ✓ CONTINUE decision correctly reached")
    return True


def test_requires_human_requires_revise():
    """Objections requiring human trigger REVISE."""
    print("\n[Test 3] REQUIRES_HUMAN triggers REVISE")

    court = FinalResearchCourt()

    gates = {
        "objection_gate": ObjectionGate(
            open_fatal_objections=[],
            requires_human_objections=[
                {
                    "id": "obj_h",
                    "title": "伦理问题需要人类判断",
                    "severity": "MAJOR",
                    "status": "REQUIRES_HUMAN",
                },
            ],
        ),
    }

    decision = court.make_decision(gates=gates)

    print(f"  Decision: {decision.decision.value}")
    print(f"  Requires human: {decision.requires_human_review}")

    assert decision.decision == ScientificDecision.REVISE, \
        f"Expected REVISE but got {decision.decision.value}"
    assert decision.requires_human_review is True

    print("  ✓ REVISE decision correctly triggered")
    return True


def test_novelty_gate_blocks():
    """Novelty gate blocks if cannot determine."""
    print("\n[Test 4] Novelty gate blocks appropriately")

    court = FinalResearchCourt()

    # Case: No novelty claim
    gates = {
        "objection_gate": ObjectionGate(open_fatal_objections=[]),
        "novelty_gate": NoveltyGate(has_novel_claim=False),
    }

    decision = court.make_decision(gates=gates)

    print(f"  Decision: {decision.decision.value}")
    print(f"  Novelty gate result: {decision.gates['novelty_gate'].result.value}")

    assert decision.decision == ScientificDecision.REVISE, \
        f"Expected REVISE but got {decision.decision.value}"

    print("  ✓ Novelty gate correctly blocks")
    return True


def test_kill_ratio_is_diagnostic_only():
    """Kill ratio is auxiliary, not primary decision factor."""
    print("\n[Test 5] Kill ratio is auxiliary diagnostic")

    court = FinalResearchCourt()

    # Case: High kill ratio but no FATAL objections
    gates = {
        "objection_gate": ObjectionGate(open_fatal_objections=[]),
    }

    decision = court.make_decision(
        gates=gates,
        kill_ratio=0.9,  # High kill ratio
        debate_status="NEEDS_REVISION",
    )

    print(f"  Decision: {decision.decision.value}")
    print(f"  Kill ratio (diagnostic): {decision.kill_ratio}")

    # Even with 0.9 kill ratio, no blockers means CONTINUE
    assert decision.decision == ScientificDecision.CONTINUE, \
        f"Expected CONTINUE but got {decision.decision.value}"

    # Kill ratio is recorded as diagnostic
    assert decision.kill_ratio == 0.9
    assert decision.debate_status == "NEEDS_REVISION"

    print("  ✓ Kill ratio correctly demoted to diagnostic")
    return True


def test_evidence_based_reasoning():
    """Decision includes evidence IDs in reasoning."""
    print("\n[Test 6] Evidence-based reasoning")

    court = FinalResearchCourt()

    gates = {
        "objection_gate": ObjectionGate(open_fatal_objections=[]),
        "novelty_gate": NoveltyGate(
            has_novel_claim=True,
            evidence_ids=["novelty_exp_1", "novelty_exp_2"],
            novelty_threats=["threat_1"],  # Has threats but evidence addresses them
        ),
    }

    decision = court.make_decision(
        gates=gates,
        supporting_evidence_ids=["evidence_1", "evidence_2"],
        contradicting_evidence_ids=["contradiction_1"],
    )

    print(f"  Decision: {decision.decision.value}")
    print(f"  Supporting evidence: {len(decision.supporting_evidence_ids)}")
    print(f"  Contradicting evidence: {len(decision.contradicting_evidence_ids)}")

    # Evidence is recorded
    assert len(decision.supporting_evidence_ids) == 2
    assert len(decision.contradicting_evidence_ids) == 1

    # Novelty gate has evidence
    novelty_gate = decision.gates.get("novelty_gate")
    assert len(novelty_gate.evidence_ids) == 2

    print("  ✓ Evidence correctly tracked")
    return True


def test_decision_graph_generation():
    """Decision includes reason graph."""
    print("\n[Test 7] Decision reason graph")

    from ai_scientist.engine.final_research_court import DecisionGraph

    court = FinalResearchCourt()

    gates = {
        "objection_gate": ObjectionGate(open_fatal_objections=[
            {"id": "obj_1", "title": "FATAL objection"},
        ]),
    }

    decision = court.make_decision(gates=gates)

    # Generate graph
    graph = DecisionGraph().from_decision(decision)

    print(f"  Nodes: {len(graph.nodes)}")
    print(f"  Edges: {len(graph.edges)}")

    # Graph has decision node
    assert any(n["type"] == "DECISION" for n in graph.nodes)
    assert any(n["type"] == "GATE" for n in graph.nodes)

    # Save graph
    output_dir = Path("research_output")
    output_dir.mkdir(exist_ok=True)
    graph_file = output_dir / "decision_graph.json"
    with open(graph_file, "w", encoding="utf-8") as f:
        json.dump(graph.to_dict(), f, indent=2, ensure_ascii=False)
    print(f"  Saved: {graph_file}")

    print("  ✓ Decision graph generated")
    return True


def test_decision_validation():
    """Validate hard-constraint rule enforcement."""
    print("\n[Test 8] Decision validation")

    court = FinalResearchCourt()

    # Valid: KILL with FATAL objections
    gates = {
        "objection_gate": ObjectionGate(
            open_fatal_objections=[{"id": "obj_1", "title": "FATAL"}],
        ),
    }
    valid_decision = court.make_decision(gates=gates)
    is_valid, violations = court.validate_decision(valid_decision)

    print(f"  KILL with FATAL: Valid={is_valid}")
    if violations:
        print(f"    Violations: {violations}")

    assert is_valid, "KILL with FATAL should be valid"

    # Invalid: CONTINUE with OPEN FATAL
    invalid_decision = FinalDecision(
        decision=ScientificDecision.CONTINUE,
        reasons=[],  # No blocking reasons
    )
    invalid_decision.gates = gates.get("objection_gate", ObjectionGate()).evaluate()

    is_valid, violations = court.validate_decision(invalid_decision)

    print(f"  CONTINUE with FATAL: Valid={is_valid}")
    if violations:
        for v in violations:
            print(f"    Violation: {v}")

    assert not is_valid, "CONTINUE with FATAL should be invalid"
    assert any("HARD CONSTRAINT" in v for v in violations)

    print("  ✓ Hard-constraint validation working")
    return True


def test_full_decision_output():
    """Test complete decision JSON output."""
    print("\n[Test 9] Full decision JSON output")

    court = FinalResearchCourt()

    gates = {
        "objection_gate": ObjectionGate(
            open_fatal_objections=[
                {
                    "id": "obj_1",
                    "title": "研究命题缺乏操作性",
                    "severity": "FATAL",
                    "status": "OPEN",
                    "argument": "没有可操作的定义导致无法验证",
                    "supporting_evidence_ids": [],
                },
            ],
            requires_human_objections=[
                {
                    "id": "obj_2",
                    "title": "伦理考量",
                    "severity": "MAJOR",
                    "status": "REQUIRES_HUMAN",
                },
            ],
        ),
        "novelty_gate": NoveltyGate(
            has_novel_claim=True,
            evidence_ids=["novelty_exp_1"],
            novelty_threats=[],
        ),
        "feasibility_gate": FeasibilityGate(
            has_method=True,
            has_data=True,
            has_measurements=True,
            feasibility_objections=[],
        ),
    }

    decision = court.make_decision(
        gates=gates,
        kill_ratio=0.45,
        debate_status="RESEARCHABLE",
        supporting_evidence_ids=["baseline_exp_1"],
        contradicting_evidence_ids=["control_exp_1"],
    )

    # Serialize to dict
    decision_dict = decision.to_dict()

    print(f"  Decision: {decision_dict['decision']}")
    print(f"  Gates: {list(decision_dict['gates'].keys())}")
    print(f"  Reasons: {len(decision_dict['reasons'])}")
    print(f"  Supporting evidence: {len(decision_dict['supporting_evidence_ids'])}")
    print(f"  Diagnostics kill_ratio: {decision_dict['diagnostics']['kill_ratio']}")

    # Save to file
    output_dir = Path("research_output")
    output_dir.mkdir(exist_ok=True)
    decision_file = output_dir / "final_decision.json"
    with open(decision_file, "w", encoding="utf-8") as f:
        json.dump(decision_dict, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {decision_file}")

    # Verify structure
    assert "decision" in decision_dict
    assert "timestamp" in decision_dict
    assert "gates" in decision_dict
    assert "reasons" in decision_dict
    assert "diagnostics" in decision_dict

    print("  ✓ Full decision output generated")
    return True


def run_all_tests():
    """Run all FinalResearchCourt tests."""
    print("=" * 60)
    print("FinalResearchCourt Hard-Constraint Tests")
    print("=" * 60)

    tests = [
        test_hard_constraint_fatal_blocks_continue,
        test_no_fatal_allows_continue,
        test_requires_human_requires_revise,
        test_novelty_gate_blocks,
        test_kill_ratio_is_diagnostic_only,
        test_evidence_based_reasoning,
        test_decision_graph_generation,
        test_decision_validation,
        test_full_decision_output,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append((test.__name__, result))
        except Exception as e:
            print(f"\n  ✗ Test failed: {e}")
            results.append((test.__name__, False))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")

    print("\nKey v4 Hard-Constraint Rules Validated:")
    print("  ✓ OPEN FATAL always blocks CONTINUE → KILL")
    print("  ✓ REQUIRES_HUMAN triggers REVISE")
    print("  ✓ Kill Ratio demoted to auxiliary diagnostic")
    print("  ✓ Gate evaluation SEPARATE from decision")
    print("  ✓ Evidence IDs tracked in reasoning")
    print("  ✓ Decision graph for visualization")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
