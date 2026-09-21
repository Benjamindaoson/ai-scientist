"""Quick API test - validates core pipeline without slow debate system."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from ai_scientist.orchestrator import AIScientist
from ai_scientist.core.gateway import ClaudeRelayGateway


async def main():
    print("=" * 60)
    print("Quick API Test - Core Pipeline")
    print("=" * 60)

    # Use real API gateway
    gateway = ClaudeRelayGateway(
        relay_url="https://api.jingziai.club/v1",
        api_key="sk-CsvX9nQ2XsyZxF6nwR8uucvCUbfXN2hYp5CWD7tL6ECCdK1E",
        model="gpt-5.6-sol",
        max_tokens=512,
    )

    ai_scientist = AIScientist(
        db_path=":memory:",
        gateway=gateway,
        max_literature_results=5,
    )

    seed_question = "人工智能智能体从失败中学习"

    print("\n[1/5] Starting research session...")
    session = await ai_scientist.start_research(
        seed_question=seed_question,
        project_name="Quick API Test",
        domain="AI/ML",
    )
    print(f"  Session: {session.session_id}")

    print("\n[2/5] Identifying phenomenon...")
    phenomenon = await ai_scientist.identify_phenomenon(
        observation="AI agents often repeat mistakes",
        domain="AI/ML",
    )
    print(f"  Phenomenon: {phenomenon.id}")

    print("\n[3/5] Formulating puzzle...")
    puzzle = await ai_scientist.formulate_puzzle(phenomenon)
    print(f"  Puzzle: {puzzle.id}")

    print("\n[4/5] Generating research questions (LLM call)...")
    questions = await ai_scientist.generate_research_questions(phenomenon, puzzle)
    print(f"  Generated {len(questions)} questions")
    for i, q in enumerate(questions[:2], 1):
        print(f"    {i}. {q.question_text[:60]}...")

    print("\n[5/5] Developing theory...")
    theory = await ai_scientist.develop_theory(
        theory_name="Failure Learning Theory",
        core_claim="Agents can improve through failure analysis",
    )
    print(f"  Theory: {theory.theory_id} ({theory.status.value})")

    print("\n" + "=" * 60)
    print("QUICK API TEST PASSED!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
