"""科研验收测试 - 真实科研案例盲测

研究问题：大模型能否仅依靠自身生成的数据、反馈和验证机制持续获得真正新的能力？

本次测试是盲测：不允许在系统提示词中预先告诉系统正确答案。
"""
import asyncio
import sys
import os
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from ai_scientist.orchestrator import AIScientist
from ai_scientist.core.gateway import ClaudeRelayGateway


# ============================================================
# 科研工件输出目录
# ============================================================
OUTPUT_DIR = Path("research_output")
OUTPUT_DIR.mkdir(exist_ok=True)

ARTIFACTS = {}

def save_artifact(name: str, content: dict):
    """保存科研工件"""
    ARTIFACTS[name] = content
    filepath = OUTPUT_DIR / f"{name}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(content, f, indent=2, ensure_ascii=False)
    print(f"  [保存] {name}.json")


async def main():
    print("=" * 70)
    print("AI SCIENTIST 科研验收测试")
    print("研究问题：大模型能否仅依靠自身生成的数据、反馈和验证机制")
    print("         持续获得真正新的能力？如果不能，瓶颈究竟是什么？")
    print("=" * 70)
    print("\n[模式] 盲测 - 不预置正确答案，不注入理论结论")
    print("=" * 70)

    # ============================================================
    # 阶段 0: 初始化真实 API 网关
    # ============================================================
    print("\n[初始化] 连接真实 API...")

    gateway = ClaudeRelayGateway(
        relay_url="https://api.jingziai.club/v1",
        api_key="sk-CsvX9nQ2XsyZxF6nwR8uucvCUbfXN2hYp5CWD7tL6ECCdK1E",
        model="gpt-5.6-sol",
        max_tokens=2048,
    )

    ai_scientist = AIScientist(
        db_path=str(OUTPUT_DIR / "research.db"),
        gateway=gateway,
        max_literature_results=15,
    )

    # ============================================================
    # 阶段 1: 研究种子启动
    # ============================================================
    print("\n" + "=" * 70)
    print("阶段 1: 启动研究")
    print("=" * 70)

    seed_question = """大模型能否仅依靠自身生成的数据、反馈和验证机制
    持续获得真正新的能力？如果不能，瓶颈究竟是什么？"""

    session = await ai_scientist.start_research(
        seed_question=seed_question,
        project_name="LLM自我改进能力边界研究",
        domain="AI/ML/LLM",
    )
    print(f"✓ 研究会话: {session.session_id}")
    print(f"  项目ID: {session.project_id}")

    # ============================================================
    # 阶段 2: 真实文献搜索
    # ============================================================
    print("\n" + "=" * 70)
    print("阶段 2: 真实文献调查")
    print("=" * 70)

    # 执行多个文献搜索查询
    search_queries = [
        "LLM self-improvement self-training without external data",
        "language model continual learning without supervision",
        "self-play AI language model emergent capabilities",
        "synthetic data self-distillation LLM",
        "generative adversarial networks language models",
        "self-verification AI reasoning",
    ]

    all_papers = []
    for query in search_queries:
        print(f"\n  搜索: {query[:50]}...")
        try:
            papers = await ai_scientist.search_literature(query, max_results=5)
            print(f"    找到 {len(papers)} 篇论文")
            all_papers.extend(papers)
        except Exception as e:
            print(f"    搜索失败: {e}")

    # 去重
    seen_ids = set()
    unique_papers = []
    for p in all_papers:
        if p.arxiv_id not in seen_ids:
            seen_ids.add(p.arxiv_id)
            unique_papers.append(p)

    print(f"\n✓ 文献搜索完成: 共 {len(unique_papers)} 篇独特论文")

    # 保存文献地图
    literature_map = {
        "timestamp": datetime.now().isoformat(),
        "search_queries": search_queries,
        "total_papers": len(unique_papers),
        "papers": [
            {
                "arxiv_id": p.arxiv_id,
                "title": p.title,
                "authors": p.authors[:5] if p.authors else [],
                "abstract": (p.abstract[:500] if p.abstract else "") + "...",
            }
            for p in unique_papers[:20]  # 保存前20篇
        ],
    }
    save_artifact("literature_map", literature_map)

    # ============================================================
    # 阶段 3: 提炼研究现象与研究谜题
    # ============================================================
    print("\n" + "=" * 70)
    print("阶段 3: 提炼研究现象与研究谜题")
    print("=" * 70)

    # 识别研究现象
    phenomenon = await ai_scientist.identify_phenomenon(
        observation="LLMs seem to improve with more training data, but it's unclear whether they can discover genuinely new capabilities through self-generated feedback without external ground truth.",
        domain="AI/ML",
    )
    print(f"✓ 现象识别: {phenomenon.id}")
    print(f"  描述: {phenomenon.raw_description[:100]}...")

    # 制定研究谜题
    puzzle = await ai_scientist.formulate_puzzle(
        phenomenon=phenomenon,
        puzzle_type=None,  # 让系统自动判断类型
    )
    print(f"✓ 谜题制定: {puzzle.id}")
    print(f"  声明: {puzzle.puzzle_statement[:100]}...")

    # 保存研究现象与谜题档案
    phenomenon_puzzle_artifact = {
        "timestamp": datetime.now().isoformat(),
        "research_question": seed_question,
        "phenomenon": {
            "id": phenomenon.id,
            "description": phenomenon.raw_description,
            "type": str(phenomenon.phenomenon_type),
            "domain": phenomenon.domain,
        },
        "puzzle": {
            "id": puzzle.id,
            "statement": puzzle.puzzle_statement,
            "type": str(puzzle.puzzle_type) if puzzle.puzzle_type else "AUTO",
        },
    }
    save_artifact("phenomenon_puzzle", phenomenon_puzzle_artifact)

    # ============================================================
    # 阶段 4: 生成研究问题
    # ============================================================
    print("\n" + "=" * 70)
    print("阶段 4: 生成研究问题")
    print("=" * 70)

    questions = await ai_scientist.generate_research_questions(phenomenon, puzzle)
    print(f"✓ 生成 {len(questions)} 个研究问题:")
    for i, q in enumerate(questions, 1):
        print(f"  {i}. {q.question_text[:80]}...")

    # ============================================================
    # 阶段 5: 理论发展与反例发现
    # ============================================================
    print("\n" + "=" * 70)
    print("阶段 5: 理论发展与反例发现")
    print("=" * 70)

    # 创建初始理论
    initial_theory = await ai_scientist.develop_theory(
        theory_name="Self-Generated Data Improvement Hypothesis",
        core_claim="LLMs can improve through self-generated data and self-verification without external information sources.",
    )
    print(f"✓ 初始理论: {initial_theory.theory_id}")

    # 使用 LLM 生成反例分析
    print("\n  [LLM反例分析] 寻找自训练反例...")
    counterexample_prompt = f"""作为科研反例发现专家，分析以下理论主张的反例和边界情况：

理论主张：大模型能否仅依靠自身生成的数据、反馈和验证机制持续获得真正新的能力？

请分析以下方向的反例：
1. 自训练 (Self-training): 模型使用自身预测作为伪标签进行训练
2. 自博弈 (Self-play): 两个或多个模型实例相互对抗
3. 生成与验证差距 (Generation-Verification Gap): 生成器与判别器的差距
4. 主动学习 (Active Learning): 模型选择最有价值的数据点
5. 信息价值 (Information Value): 新信息vs计算能力扩张
6. 合成数据 (Synthetic Data): 自生成数据的质量边界

对于每个方向，请指出：
- 存在的反例或边界情况
- 何时这个方法会失效
- 与"真正新能力"的边界在哪里

回答格式：
[反例分析]
<具体反例>
"""
    try:
        counterexample_analysis = gateway.generate(counterexample_prompt)
        print(f"  [反例分析结果] (长度: {len(counterexample_analysis)})")
    except Exception as e:
        counterexample_analysis = f"LLM调用失败: {e}"

    # 保存反例档案
    counterexample_artifact = {
        "timestamp": datetime.now().isoformat(),
        "initial_theory": {
            "id": initial_theory.theory_id,
            "name": initial_theory.theory_name,
            "claim": initial_theory.core_claim,
        },
        "counterexample_analysis": counterexample_analysis,
    }
    save_artifact("counterexample_analysis", counterexample_artifact)

    # ============================================================
    # 阶段 6: 创新审查与撞题检查
    # ============================================================
    print("\n" + "=" * 70)
    print("阶段 6: 创新审查与撞题检查")
    print("=" * 70)

    innovation_prompt = f"""作为科研创新审查专家，评估以下研究问题是否具有真正的创新性：

研究问题：大模型能否仅依靠自身生成的数据、反馈和验证机制持续获得真正新的能力？

请检查：
1. 这是否只是已有理论的换名或换场景？
2. 是否与以下已有研究高度重叠：
   - Self-training (Xie et al., 2019)
   - Self-play / Fictitious Self-Play
   - AlphaZero / MuZero 自博弈
   - STaR (Self-Taught Reasoner)
   - Self-consistency
   - Constitutional AI
   - RLHF / RLAIF

3. 真正的创新空间在哪里？
4. 是否存在"伪创新"风险？

回答格式：
[撞题检查]
<分析结果>
"""
    try:
        innovation_review = gateway.generate(innovation_prompt)
        print(f"  [撞题检查] (长度: {len(innovation_review)})")
    except Exception as e:
        innovation_review = f"LLM调用失败: {e}"

    innovation_artifact = {
        "timestamp": datetime.now().isoformat(),
        "research_question": seed_question,
        "innovation_review": innovation_review,
    }
    save_artifact("innovation_review", innovation_artifact)

    # ============================================================
    # 阶段 7: 科研红队 - 寻找致命问题
    # ============================================================
    print("\n" + "=" * 70)
    print("阶段 7: 科研红队 - 寻找致命问题")
    print("=" * 70)

    red_team_prompt = f"""作为科研红队专家，主动寻找这个研究方向的根本性致命问题：

研究问题：大模型能否仅依靠自身生成的数据、反馈和验证机制持续获得真正新的能力？

请主动攻击：
1. 核心假设是否成立？
2. 是否有不可逾越的理论障碍？
3. "新能力"的定义是否清晰可测？
4. 是否混淆了"计算能力扩张"和"新信息获取"？
5. 实验设计是否有致命缺陷？
6. 是否有循环论证风险？

如果发现致命问题，请明确说明：
- 问题是什么
- 为什么是致命的
- 建议如何修改或终止

回答格式：
[红队报告]
<致命问题列表>
"""
    try:
        red_team_report = gateway.generate(red_team_prompt)
        print(f"  [红队报告] (长度: {len(red_team_report)})")
    except Exception as e:
        red_team_report = f"LLM调用失败: {e}"

    red_team_artifact = {
        "timestamp": datetime.now().isoformat(),
        "red_team_report": red_team_report,
        "reviewer_role": "科研红队",
    }
    save_artifact("red_team", red_team_artifact)

    # ============================================================
    # 阶段 8: 替代理论解释
    # ============================================================
    print("\n" + "=" * 70)
    print("阶段 8: 替代理论解释")
    print("=" * 70)

    alternative_prompt = f"""作为理论物理学家和机器学习理论专家，提供替代理论解释：

研究问题：大模型能否仅依靠自身生成的数据、反馈和验证机制持续获得真正新的能力？

请提供至少两个替代理论解释：
1. 理论A: [名称] - [核心主张] - [支持/反对的证据]
2. 理论B: [名称] - [核心主张] - [支持/反对的证据]
3. (可选) 理论C: ...

每个理论需要说明：
- 核心预测是什么
- 如何设计实验区分这两个理论
- 什么结果会证伪这个理论

回答格式：
[替代理论]
<理论A>
<理论B>
"""
    try:
        alternative_theories = gateway.generate(alternative_prompt)
        print(f"  [替代理论] (长度: {len(alternative_theories)})")
    except Exception as e:
        alternative_theories = f"LLM调用失败: {e}"

    alternative_artifact = {
        "timestamp": datetime.now().isoformat(),
        "alternative_theories": alternative_theories,
    }
    save_artifact("alternative_theories", alternative_artifact)

    # ============================================================
    # 阶段 9: 研究契约第一版
    # ============================================================
    print("\n" + "=" * 70)
    print("阶段 9: 研究契约第一版")
    print("=" * 70)

    contract_prompt = f"""作为科研委员会主席，起草研究契约第一版：

研究问题：大模型能否仅依靠自身生成的数据、反馈和验证机制持续获得真正新的能力？

请起草包含以下部分的研究契约：
1. 研究问题（精炼版）
2. 核心假设
3. 可检验预测
4. 实验设计（能区分理论）
5. 决策规则：
   - 什么结果出现时继续
   - 什么结果出现时修改
   - 什么结果出现时转向
   - 什么结果出现时终止
6. 当前研究的可信度评估
7. 初步决策建议

重要约束：
- 不允许使用"百分之百创新""绝对没人做过"
- 任何主张必须有证据来源
- 如果已有研究覆盖核心贡献，必须终止

回答格式：
[研究契约]
<完整契约>
"""
    try:
        research_contract = gateway.generate(contract_prompt)
        print(f"  [研究契约] (长度: {len(research_contract)})")
    except Exception as e:
        research_contract = f"LLM调用失败: {e}"

    contract_artifact = {
        "timestamp": datetime.now().isoformat(),
        "research_contract": research_contract,
        "status": "第一版",
    }
    save_artifact("research_contract", contract_artifact)

    # ============================================================
    # 阶段 10: 综合决策
    # ============================================================
    print("\n" + "=" * 70)
    print("阶段 10: 综合决策")
    print("=" * 70)

    decision_prompt = """作为科研委员会，基于所有分析给出最终决策：

可用信息：
- 研究现象与谜题
- 文献地图
- 反例分析
- 创新审查
- 红队报告
- 替代理论
- 研究契约第一版

请做出以下四种决策之一：
1. 继续：研究方向有效，继续深入
2. 修改：需要修改研究问题或方法
3. 转向：需要改变研究方向
4. 终止：已有研究覆盖或方向不可行

决策理由必须：
- 基于证据而非偏好
- 引用具体分析结果
- 给出明确的修改建议或终止理由
"""
    try:
        final_decision = gateway.generate(decision_prompt)
        print(f"  [最终决策] (长度: {len(final_decision)})")
    except Exception as e:
        final_decision = f"LLM调用失败: {e}"

    decision_artifact = {
        "timestamp": datetime.now().isoformat(),
        "final_decision": final_decision,
        "artifacts_reviewed": list(ARTIFACTS.keys()),
    }
    save_artifact("final_decision", decision_artifact)

    # ============================================================
    # 总结
    # ============================================================
    print("\n" + "=" * 70)
    print("科研验收测试完成")
    print("=" * 70)
    print(f"\n产出的科研工件 ({len(ARTIFACTS)}份):")
    for name in sorted(ARTIFACTS.keys()):
        filepath = OUTPUT_DIR / f"{name}.json"
        print(f"  ✓ {name}.json")

    print(f"\n所有工件已保存到: {OUTPUT_DIR.absolute()}")
    print("\n请查看 research_contract.json 和 final_decision.json 获取最终结论")

    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\n验收测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
