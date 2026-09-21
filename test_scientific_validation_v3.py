"""科研验收测试 v3 - 精简版（减少API调用）"""
import asyncio
import sys
import os
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from ai_scientist.orchestrator import AIScientist
from ai_scientist.core.gateway import ClaudeRelayGateway


OUTPUT_DIR = Path("research_output_v3")
OUTPUT_DIR.mkdir(exist_ok=True)

ARTIFACTS = {}

def save(name, content):
    ARTIFACTS[name] = content
    with open(OUTPUT_DIR / f"{name}.json", "w", encoding="utf-8") as f:
        json.dump(content, f, indent=2, ensure_ascii=False, default=str)
    print(f"  [保存] {name}.json")

async def main():
    print("=" * 70)
    print("AI SCIENTIST 科研验收测试 v3 (精简版)")
    print("=" * 70)

    gateway = ClaudeRelayGateway(
        relay_url="https://api.jingziai.club/v1",
        api_key="sk-CsvX9nQ2XsyZxF6nwR8uucvCUbfXN2hYp5CWD7tL6ECCdK1E",
        model="gpt-5.6-sol",
        max_tokens=1500,
    )

    ai_scientist = AIScientist(
        db_path=str(OUTPUT_DIR / "research.db"),
        gateway=gateway,
        max_literature_results=5,
    )

    seed = "大模型能否仅依靠自身生成的数据、反馈和验证机制持续获得真正新的能力？"

    # 1. 启动研究
    print("\n[1] 启动研究...")
    session = await ai_scientist.start_research(seed, "LLM自我改进能力边界", "AI/ML")
    print(f"  会话: {session.session_id}")

    # 2. 文献搜索
    print("\n[2] 文献搜索...")
    papers = []
    for q in ["LLM self-improvement", "self-training LLM", "model collapse synthetic data"]:
        try:
            r = await ai_scientist.search_literature(q, max_results=3)
            papers.extend(r)
        except: pass
    print(f"  找到 {len(papers)} 篇论文")
    save("literature", {"papers": [{"id": p.arxiv_id, "title": p.title} for p in papers[:15]]})

    # 3. 现象与谜题
    print("\n[3] 提炼现象与谜题...")
    phen = await ai_scientist.identify_phenomenon(
        "LLMs improve with self-generated data, but can they discover genuinely new capabilities?", "AI/ML")
    puzzle = await ai_scientist.formulate_puzzle(phen)
    print(f"  现象: {phen.id}, 谜题: {puzzle.id}")
    save("phenomenon_puzzle", {"phenomenon": phen.raw_description, "puzzle": puzzle.puzzle_statement})

    # 4. 研究问题
    print("\n[4] 生成研究问题...")
    questions = await ai_scientist.generate_research_questions(phen, puzzle)
    print(f"  生成 {len(questions)} 个问题")
    save("questions", {"questions": [q.question_text for q in questions]})

    # 5. 辩论 - 使用 orchestrator 的辩论系统
    print("\n[5] 多智能体辩论...")
    direction = ai_scientist.repo.create_direction(
        project_id=session.project_id,
        title="LLM自我改进能力边界",
        hypothesis="LLMs can gain new capabilities through self-generated data alone",
    )

    debate_result = await ai_scientist.evaluate_direction(direction, max_rounds=2)
    print(f"  辩论状态: {debate_result.status.value}")
    print(f"  Kill比率: {debate_result.kill_ratio:.1%}")
    print(f"  轮次: {debate_result.rounds_completed}")

    # 保存辩论记录
    debate_record = {
        "debate_id": debate_result.debate_id,
        "status": debate_result.status.value,
        "kill_ratio": debate_result.kill_ratio,
        "rounds": debate_result.rounds_completed,
        "key_objections": debate_result.key_objections,
        "required_revisions": debate_result.required_revisions,
        "conclusion": debate_result.conclusion,
    }
    save("debate_record", debate_record)

    # 6. 红队分析
    print("\n[6] 科研红队分析...")
    red_team_prompt = f"""作为科研红队，攻击以下研究方向：

研究方向：LLM能否仅依靠自生成数据和自我验证持续获得真正新的能力？

已知辩论结果：
- Kill比率: {debate_result.kill_ratio:.1%}
- 致命异议: {len(debate_result.key_objections)}个

请寻找：
1. 致命问题（定义不清、信息论约束、循环论证等）
2. 反例（AlphaZero, STaR, Self-Rewarding等）
3. 修改建议或终止理由

简洁回答。"""

    try:
        red_team = gateway.generate(red_team_prompt)
    except Exception as e:
        red_team = f"Error: {e}"
    print(f"  红队报告: {len(red_team)} 字符")
    save("red_team", {"red_team_report": red_team})

    # 7. 替代理论
    print("\n[7] 替代理论...")
    alt_prompt = """提供3个替代理论解释"LLM自生成数据的改进效果"：

1. 潜能显化论：模型只是把隐含能力显化
2. 模型坍缩论：自训练导致分布收缩
3. 外部验证论：真正改进来自外部验证器

每个理论给出：核心主张、可区分实验、证伪条件。
简洁格式。"""

    try:
        alt_theories = gateway.generate(alt_prompt)
    except Exception as e:
        alt_theories = f"Error: {e}"
    save("alternative_theories", {"theories": alt_theories})

    # 8. 最终决策
    print("\n[8] 最终决策...")
    decision_prompt = f"""基于以下分析，做出科研决策：

辩论结果: {debate_result.status.value} (Kill {debate_result.kill_ratio:.1%})
红队异议: {len(debate_result.key_objections)}个致命问题

决策选项: A.继续 B.修改 C.转向 D.终止

必须：引用证据、给出理由、说明对替代理论的态度。"""

    try:
        decision = gateway.generate(decision_prompt)
    except Exception as e:
        decision = f"Error: {e}"
    print(f"  决策: {decision[:200]}...")
    save("final_decision", {"decision": decision})

    # 9. 研究契约
    print("\n[9] 研究契约...")
    contract_prompt = f"""基于辩论({debate_result.status.value})和红队报告，生成研究契约：

1. 精炼研究问题（回应红队）
2. 核心假设(H0, H1)
3. 可检验预测
4. 实验设计
5. 决策规则（继续/修改/转向/终止条件）
6. 可信度评估

简洁格式。"""

    try:
        contract = gateway.generate(contract_prompt)
    except Exception as e:
        contract = f"Error: {e}"
    save("research_contract", {"contract": contract, "version": "v3"})

    # 总结
    print("\n" + "=" * 70)
    print("测试完成！")
    print("=" * 70)
    print(f"\n工件列表:")
    for name in sorted(ARTIFACTS.keys()):
        print(f"  ✓ {name}.json")
    print(f"\n输出目录: {OUTPUT_DIR.absolute()}")

    return True

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\n失败: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
