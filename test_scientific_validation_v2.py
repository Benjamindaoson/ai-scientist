"""科研验收测试 v2 - 真实科研案例盲测 + 辩论记录 + 多模型验证

研究问题：大模型能否仅依靠自身生成的数据、反馈和验证机制持续获得真正新的能力？
"""
import asyncio
import sys
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from ai_scientist.orchestrator import AIScientist
from ai_scientist.core.gateway import ClaudeRelayGateway
from ai_scientist.engine.multi_agent_debate import (
    MultiAgentDebateSystem, AgentRole, DebateStatus, ObjectionSeverity
)


# ============================================================
# 科研工件输出目录
# ============================================================
OUTPUT_DIR = Path("research_output_v2")
OUTPUT_DIR.mkdir(exist_ok=True)

ARTIFACTS = {}


def save_artifact(name: str, content: dict, force: bool = False):
    """保存科研工件"""
    if name in ARTIFACTS and not force:
        # Merge content
        if isinstance(ARTIFACTS[name], dict) and isinstance(content, dict):
            ARTIFACTS[name].update(content)
        elif isinstance(ARTIFACTS[name], list) and isinstance(content, list):
            ARTIFACTS[name].extend(content)
    else:
        ARTIFACTS[name] = content

    filepath = OUTPUT_DIR / f"{name}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(ARTIFACTS[name] if isinstance(ARTIFACTS[name], (dict, list)) else {"content": ARTIFACTS[name]},
                  f, indent=2, ensure_ascii=False, default=str)
    print(f"  [保存] {name}.json")


def print_round(round_obj, stage_name: str):
    """打印辩论轮次详情"""
    print(f"\n  === {stage_name} ===")
    for role, arg in round_obj.agent_arguments.items():
        vote = round_obj.agent_votes.get(role)
        vote_str = "🔴 KILL" if (vote and vote.kill_vote) else "🟢 PURSUE" if vote else "❓"
        print(f"  {role.value}: {vote_str}")
        print(f"    立场: {arg.content[:200]}...")
        if vote:
            print(f"    置信度: {vote.confidence:.1%}")
    if round_obj.objections:
        fatal = [o for o in round_obj.objections if o.severity == ObjectionSeverity.FATAL]
        if fatal:
            print(f"  ⚠️  致命异议: {len(fatal)}个")


# ============================================================
# 多模型验证器
# ============================================================
class MultiModelValidator:
    """使用多个模型进行交叉验证"""

    def __init__(self, base_url: str, api_key: str, models: list[str]):
        self.base_url = base_url
        self.api_key = api_key
        self.models = models
        self.gateways = {
            model: ClaudeRelayGateway(
                relay_url=base_url,
                api_key=api_key,
                model=model,
                max_tokens=1024,
            )
            for model in models
        }

    def generate_all(self, prompt: str) -> dict[str, str]:
        """所有模型生成响应"""
        results = {}
        for model in self.models:
            try:
                response = self.gateways[model].generate(prompt)
                results[model] = response
            except Exception as e:
                results[model] = f"ERROR: {e}"
        return results

    def cross_validate(self, prompt: str, check_agreement: bool = True) -> dict:
        """交叉验证并检查一致性"""
        results = self.generate_all(prompt)

        # 提取关键结论（简单方式：取前100字符）
        conclusions = {m: r[:100] for m, r in results.items()}

        # 计算一致性（简单方式：检查是否都包含某些关键词）
        agreement_score = 0.0
        if check_agreement:
            keywords = ["终止", "terminate", "reject", "modif", "修改", "创新", "innovation",
                       "撞题", "overlap", "self-training", "坍缩", "collapse"]
            scores = []
            for model, response in results.items():
                text = response.lower()
                found = sum(1 for kw in keywords if kw.lower() in text)
                scores.append(found)
            if scores:
                max_score = max(scores)
                min_score = min(scores)
                agreement_score = 1.0 - (max_score - min_score) / max(max_score, 1)

        return {
            "model_responses": results,
            "conclusions": conclusions,
            "agreement_score": agreement_score,
            "model_count": len([r for r in results.values() if not r.startswith("ERROR")]),
        }


# ============================================================
# 主测试函数
# ============================================================
async def main():
    print("=" * 70)
    print("AI SCIENTIST 科研验收测试 v2")
    print("研究问题：大模型能否仅依靠自身生成的数据、反馈和验证机制")
    print("         持续获得真正新的能力？如果不能，瓶颈究竟是什么？")
    print("=" * 70)
    print("\n[模式] 盲测 + 辩论记录 + 多模型验证")
    print("=" * 70)

    # ============================================================
    # 阶段 0: 初始化
    # ============================================================
    print("\n[初始化] 连接 API...")

    BASE_URL = "https://api.jingziai.club/v1"
    API_KEY = "sk-CsvX9nQ2XsyZxF6nwR8uucvCUbfXN2hYp5CWD7tL6ECCdK1E"

    # 多模型验证器
    models = ["gpt-5.6-sol", "gpt-5.6-terra"]
    multi_validator = MultiModelValidator(BASE_URL, API_KEY, models)

    # 单一网关（用于主流程）
    gateway = ClaudeRelayGateway(
        relay_url=BASE_URL,
        api_key=API_KEY,
        model="gpt-5.6-sol",
        max_tokens=2048,
    )

    ai_scientist = AIScientist(
        db_path=str(OUTPUT_DIR / "research.db"),
        gateway=gateway,
        max_literature_results=10,
    )

    # 初始化辩论系统
    debate_system = MultiAgentDebateSystem(
        db=ai_scientist.repo,
        gateway=gateway,
    )
    debate_system.max_rounds = 3
    debate_system.kill_threshold = 0.6

    # ============================================================
    # 阶段 1: 研究种子启动
    # ============================================================
    print("\n" + "=" * 70)
    print("阶段 1: 启动研究")
    print("=" * 70)

    seed_question = "大模型能否仅依靠自身生成的数据、反馈和验证机制持续获得真正新的能力？如果不能，瓶颈究竟是什么？"

    session = await ai_scientist.start_research(
        seed_question=seed_question,
        project_name="LLM自我改进能力边界研究",
        domain="AI/ML/LLM",
    )
    print(f"✓ 研究会话: {session.session_id}")

    save_artifact("session_info", {
        "session_id": session.session_id,
        "project_id": session.project_id,
        "seed_question": seed_question,
        "timestamp": datetime.now().isoformat(),
    })

    # ============================================================
    # 阶段 2: 真实文献搜索
    # ============================================================
    print("\n" + "=" * 70)
    print("阶段 2: 真实文献调查")
    print("=" * 70)

    search_queries = [
        "LLM self-improvement self-training without external data",
        "language model continual learning without supervision",
        "self-play AI language model emergent capabilities",
        "synthetic data self-distillation LLM",
        "self-verification AI reasoning",
        "model collapse synthetic data training",
    ]

    all_papers = []
    for query in search_queries:
        print(f"\n  搜索: {query[:50]}...")
        try:
            papers = await ai_scientist.search_literature(query, max_results=5)
            print(f"    找到 {len(papers)} 篇")
            all_papers.extend(papers)
        except Exception as e:
            print(f"    失败: {e}")

    seen_ids = set()
    unique_papers = []
    for p in all_papers:
        if p.arxiv_id not in seen_ids:
            seen_ids.add(p.arxiv_id)
            unique_papers.append(p)

    print(f"\n✓ 文献搜索完成: {len(unique_papers)} 篇独特论文")

    save_artifact("literature_map", {
        "search_queries": search_queries,
        "total_papers": len(unique_papers),
        "papers": [
            {
                "arxiv_id": p.arxiv_id,
                "title": p.title,
                "authors": p.authors[:5] if p.authors else [],
            }
            for p in unique_papers[:30]
        ],
    }, force=True)

    # ============================================================
    # 阶段 3: 提炼研究现象与谜题
    # ============================================================
    print("\n" + "=" * 70)
    print("阶段 3: 提炼研究现象与谜题")
    print("=" * 70)

    phenomenon = await ai_scientist.identify_phenomenon(
        observation="LLMs seem to improve with self-generated data, but it's unclear whether they can discover genuinely new capabilities without external ground truth.",
        domain="AI/ML",
    )
    print(f"✓ 现象: {phenomenon.id}")

    puzzle = await ai_scientist.formulate_puzzle(phenomenon)
    print(f"✓ 谜题: {puzzle.id}")

    save_artifact("phenomenon_puzzle", {
        "phenomenon": {"id": phenomenon.id, "description": phenomenon.raw_description},
        "puzzle": {"id": puzzle.id, "statement": puzzle.puzzle_statement},
    }, force=True)

    # ============================================================
    # 阶段 4: 生成研究问题
    # ============================================================
    print("\n" + "=" * 70)
    print("阶段 4: 生成研究问题")
    print("=" * 70)

    questions = await ai_scientist.generate_research_questions(phenomenon, puzzle)
    print(f"✓ 生成 {len(questions)} 个研究问题:")
    for i, q in enumerate(questions, 1):
        print(f"  {i}. {q.question_text[:70]}...")

    save_artifact("research_questions", {
        "questions": [{"id": q.id, "text": q.question_text} for q in questions]
    }, force=True)

    # ============================================================
    # 阶段 5: 多模型交叉验证 - 初步假设检验
    # ============================================================
    print("\n" + "=" * 70)
    print("阶段 5: 多模型交叉验证（初步假设）")
    print("=" * 70)

    initial_hypothesis_prompt = """评估以下研究假设的合理性：

假设：大模型可以通过自生成数据和自我验证机制持续获得真正新的能力。

请分析：
1. 这个假设的主要支撑证据
2. 这个假设的主要反驳证据
3. 假设成立的必要条件
4. 假设可能被推翻的关键反例

回答要客观，基于机器学习的理论基础。"""

    print("  运行多模型验证...")
    validation = multi_validator.cross_validate(initial_hypothesis_prompt)
    print(f"\n  模型一致性分数: {validation['agreement_score']:.1%}")
    print(f"  有效模型数: {validation['model_count']}/{len(models)}")

    for model, response in validation['model_responses'].items():
        print(f"\n  [{model}]")
        print(f"    {response[:300]}...")

    save_artifact("multi_model_validation_initial", validation, force=True)

    # ============================================================
    # 阶段 6: 创建研究方向用于辩论
    # ============================================================
    print("\n" + "=" * 70)
    print("阶段 6: 创建研究方向并启动辩论")
    print("=" * 70)

    # 创建研究方向
    direction = ai_scientist.repo.create_direction(
        project_id=session.project_id,
        title="LLM自我改进能力边界研究",
        hypothesis="LLMs can continuously gain genuinely new capabilities through self-generated data and self-verification alone",
    )
    direction_id = direction["id"]
    print(f"✓ 方向创建: {direction_id}")

    # 保存初始研究方向
    save_artifact("research_direction", {
        "direction_id": direction_id,
        "title": direction["title"],
        "hypothesis": direction["hypothesis"],
        "initial_assessment": "待辩论评估",
    }, force=True)

    # ============================================================
    # 阶段 7: 多轮辩论（核心部分！）
    # ============================================================
    print("\n" + "=" * 70)
    print("阶段 7: 多智能体辩论")
    print("=" * 70)

    debate_result = await debate_system.conduct_debate(
        direction=direction,
        project_id=session.project_id,
    )

    print(f"\n辩论完成:")
    print(f"  轮次: {debate_result.rounds_completed}")
    print(f"  Kill比率: {debate_result.kill_ratio:.1%}")
    print(f"  状态: {debate_result.status.value}")
    print(f"  致命异议: {len(debate_result.key_objections)}个")
    print(f"  必要修改: {len(debate_result.required_revisions)}项")

    # 打印每轮详情
    print("\n--- 辩论轮次详情 ---")
    debate_rounds_detail = []
    for i, round_obj in enumerate(debate_result.rounds, 1):
        stage_name = f"第{i}轮 (最终轮)" if round_obj.is_final else f"第{i}轮"
        print_round(round_obj, stage_name)

        round_detail = {
            "round_number": i,
            "is_final": round_obj.is_final,
            "arguments": {
                role.value: {
                    "content": arg.content,
                    "vote": "KILL" if round_obj.agent_votes.get(role, None) and round_obj.agent_votes[role].kill_vote else "PURSUE",
                    "confidence": round_obj.agent_votes.get(role, None).confidence if round_obj.agent_votes.get(role) else None,
                }
                for role, arg in round_obj.agent_arguments.items()
            },
            "objections": [
                {
                    "text": o.objection_text,
                    "severity": o.severity.value,
                    "objector": o.objector_role.value,
                }
                for o in round_obj.objections
            ],
        }
        debate_rounds_detail.append(round_detail)

    print("\n--- 致命异议 ---")
    for obj in debate_result.key_objections:
        print(f"  ⚠️ [{obj['objector']}] {obj['text'][:100]}...")

    print("\n--- 必要修改 ---")
    for i, rev in enumerate(debate_result.required_revisions[:5], 1):
        print(f"  {i}. {rev[:100]}...")

    print("\n--- 辩论建议 ---")
    if debate_result.recommendations:
        for rec in debate_result.recommendations[:3]:
            print(f"  • {rec[:100]}...")

    # 保存辩论完整记录
    save_artifact("debate_record", {
        "debate_id": debate_result.debate_id,
        "direction_id": debate_result.direction_id,
        "status": debate_result.status.value,
        "rounds_completed": debate_result.rounds_completed,
        "kill_votes": debate_result.kill_votes,
        "total_votes": debate_result.total_votes,
        "kill_ratio": debate_result.kill_ratio,
        "conclusion": debate_result.conclusion,
        "key_objections": debate_result.key_objections,
        "required_revisions": debate_result.required_revisions,
        "recommendations": debate_result.recommendations,
        "rounds_detail": debate_rounds_detail,
        "full_arguments": [
            {
                "round": i + 1,
                "role": role.value,
                "content": arg.content,
                "vote": "KILL" if round.agent_votes.get(role, None) and round.agent_votes[role].kill_vote else "PURSUE",
            }
            for i, round in enumerate(debate_result.rounds)
            for role, arg in round.agent_arguments.items()
        ],
    }, force=True)

    # ============================================================
    # 阶段 8: 红队深度分析（补充辩论）
    # ============================================================
    print("\n" + "=" * 70)
    print("阶段 8: 科研红队深度分析")
    print("=" * 70)

    red_team_prompt = """作为科研红队专家，对以下研究问题进行深度攻击：

研究问题：LLM能否仅依靠自生成数据、反馈和验证机制持续获得真正新的能力？

针对辩论结果（已知异议：{}）：

请主动寻找以下致命问题：
1. "仅依靠自身"的系统边界是否清晰可操作？
2. 信息论约束：封闭系统能否产生新信息？
3. "新能力"的定义是否可测量、可证伪？
4. 是否混淆了计算能力扩张与新信息获取？
5. 自我验证是否会形成闭环共识而非真实进步？
6. 是否存在循环论证风险？

对于每个问题，说明：
- 问题本质
- 为什么是致命的
- 如何在实验设计中解决
- 如果无法解决，对研究方向意味着什么

最终给出：修改建议或终止建议。""".format(
        [o['text'][:50] for o in debate_result.key_objections[:3]]
    )

    try:
        red_team_report = gateway.generate(red_team_prompt)
        print(f"\n红队报告长度: {len(red_team_report)} 字符")
    except Exception as e:
        red_team_report = f"LLM调用失败: {e}"

    save_artifact("red_team_deep", {
        "red_team_report": red_team_report,
        "debate_objections_addressed": [o['text'] for o in debate_result.key_objections],
    }, force=True)

    # ============================================================
    # 阶段 9: 替代理论生成
    # ============================================================
    print("\n" + "=" * 70)
    print("阶段 9: 替代理论解释")
    print("=" * 70)

    alternative_prompt = """基于辩论结果和红队报告，提供替代理论解释：

辩论发现的关键异议：
- {}

红队发现的致命问题：
- {}

请提供至少3个替代理论：
1. 理论A：潜能显化论
2. 理论B：模型坍缩论
3. 理论C：外部验证论

每个理论需要：
- 核心主张
- 支持证据
- 可区分实验设计
- 证伪条件"""

    try:
        alt_theories = gateway.generate(alternative_prompt)
        print(f"替代理论长度: {len(alt_theories)} 字符")
    except Exception as e:
        alt_theories = f"LLM调用失败: {e}"

    save_artifact("alternative_theories", {
        "alternative_theories": alt_theories,
        "based_on_debate": True,
    }, force=True)

    # ============================================================
    # 阶段 10: 多模型最终决策
    # ============================================================
    print("\n" + "=" * 70)
    print("阶段 10: 多模型最终决策")
    print("=" * 70)

    decision_prompt = f"""作为科研委员会，基于以下所有分析给出最终决策：

1. 辩论结果：
   - 状态: {debate_result.status.value}
   - Kill比率: {debate_result.kill_ratio:.1%}
   - 致命异议: {len(debate_result.key_objections)}个
   - 必要修改: {len(debate_result.required_revisions)}项

2. 红队发现: 多个致命问题

3. 替代理论: 3个可区分理论待验证

请做出决策：
A. 继续：研究方向有效，继续深入
B. 修改：需要修改研究问题或方法
C. 转向：需要改变研究方向
D. 终止：已有研究覆盖或方向不可行

决策必须：
- 基于证据而非偏好
- 引用具体分析结果
- 给出明确的修改建议或终止理由
- 说明对替代理论的态度"""

    print("  运行多模型决策...")
    decision_validation = multi_validator.cross_validate(decision_prompt)
    print(f"\n  模型一致性分数: {decision_validation['agreement_score']:.1%}")

    for model, response in decision_validation['model_responses'].items():
        print(f"\n  [{model}]")
        print(f"    {response[:200]}...")

    # 最终决策（使用主模型）
    try:
        final_decision = gateway.generate(decision_prompt)
    except Exception as e:
        final_decision = f"LLM调用失败: {e}"

    save_artifact("final_decision", {
        "decision": final_decision,
        "multi_model_validation": {
            "agreement_score": decision_validation['agreement_score'],
            "model_responses": decision_validation['model_responses'],
        },
        "debate_summary": {
            "status": debate_result.status.value,
            "kill_ratio": debate_result.kill_ratio,
            "rounds": debate_result.rounds_completed,
        },
    }, force=True)

    # ============================================================
    # 阶段 11: 生成研究契约
    # ============================================================
    print("\n" + "=" * 70)
    print("阶段 11: 研究契约")
    print("=" * 70)

    contract_prompt = f"""基于以下所有分析，生成正式研究契约：

辩论结论：
- 状态: {debate_result.status.value}
- Kill比率: {debate_result.kill_ratio:.1%}
- 致命异议: {len(debate_result.key_objections)}个

最终决策：
{final_decision[:500]}

请生成包含以下部分的研究契约：
1. 研究问题（精炼版，必须回应红队异议）
2. 核心假设（H0, H1, H2）
3. 可检验预测
4. 实验设计（能区分理论）
5. 决策规则（继续/修改/转向/终止的明确条件）
6. 可信度评估

重要约束：
- 必须解决"新能力"的可操作定义
- 必须区分"计算扩张"和"新信息获取"
- 必须处理自我验证的循环论证风险"""

    try:
        research_contract = gateway.generate(contract_prompt)
    except Exception as e:
        research_contract = f"LLM调用失败: {e}"

    save_artifact("research_contract", {
        "contract": research_contract,
        "version": "v2",
        "includes_debate": True,
        "includes_red_team": True,
        "includes_multi_model": True,
    }, force=True)

    # ============================================================
    # 保存所有工件
    # ============================================================
    print("\n" + "=" * 70)
    print("科研验收测试完成")
    print("=" * 70)

    print(f"\n产出的科研工件 ({len(ARTIFACTS)}份):")
    for name in sorted(ARTIFACTS.keys()):
        print(f"  ✓ {name}.json")

    # 生成汇总报告
    summary = {
        "timestamp": datetime.now().isoformat(),
        "research_question": seed_question,
        "literature_count": len(unique_papers),
        "debate_summary": {
            "rounds": debate_result.rounds_completed,
            "kill_ratio": debate_result.kill_ratio,
            "status": debate_result.status.value,
            "fatal_objections": len(debate_result.key_objections),
            "required_revisions": len(debate_result.required_revisions),
        },
        "multi_model_validation": {
            "models_used": models,
            "agreement_score": decision_validation['agreement_score'],
        },
        "artifacts_count": len(ARTIFACTS),
        "artifacts": list(ARTIFACTS.keys()),
    }

    with open(OUTPUT_DIR / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n所有工件已保存到: {OUTPUT_DIR.absolute()}")
    print("\n关键文件:")
    print("  - debate_record.json  (辩论完整记录)")
    print("  - research_contract.json  (研究契约)")
    print("  - final_decision.json  (最终决策)")
    print("  - summary.json  (汇总报告)")

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
