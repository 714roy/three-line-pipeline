"""
三省节点：秘书处（分拣）、方案总（方案）、门下省（审核·三模型交叉验证）

Fable 5 质量标准：每句prompt必须明确、可验证、防幻觉。
诚实规则：只引用数据中实际存在的内容，没有的数据声称"不可达"而非编造。
"""
from lib.state import TaskState, reasonix_call, json_from_llm, consilium_cross_validate

MAX_REVIEW_ROUNDS = 3  # 防死循环

# ═══════════════════════════════════════════
# 诚实指令（所有reasonix prompt前均注入）
# ═══════════════════════════════════════════
TRUTHFUL_DIRECTIVE = (
    "\n\n诚实报告规则（严格执行，违反即不合格）：\n"
    "1. 只引用输入数据中实际存在的内容。没有的数据、未知的数值、不确定的结论——"
    "直接写'不可达'、'无数据'、'未知'，绝不编造数字或细节。\n"
    "2. 如果某个数据源不可访问，输出'[不可达]'并说明原因，不得用推测填充。\n"
    "3. 不得添加输入数据中未出现的指标（如'完成率80%''评分92分'——除非这些数字明确写在数据里）。\n"
    "4. 得出结论时必须附证据来源（哪一行数据支撑的）。无从验证的陈述=不合格。\n"
    "5. 可以提出改进建议，但必须标注'[建议]'前缀以示与事实的区别。\n"
)


# ─── 秘书处 · 意图分拣 ───

def node_秘书处(state: TaskState) -> dict:
    """秘书处（收件分拣）：分类任务意图 + 路由决策"""
    prompt = f"""{TRUTHFUL_DIRECTIVE}

你是三总六科AI朝廷的秘书处，收受四方奏章、分门别类。

用户任务：{state['task']}
用户补充：{state.get('user_context', '')}

路由规则（按任务类型分派到对应部司）：
- 知识蒸馏/文档分析 → 工程科(Reasonix) + 审计总(核验)
- 代码开发/系统管理 → 工程科(Reasonix) + 审计总(审查)
- 求职评估/JD评估 → 审计总(Claude Code career-ops 6-Block)
- 求职搜岗/搜索岗位 → 工程科(猎聘MCP搜岗) + 审计总(Claude Code评估)
- 内容生成/写作 → 工程科(Reasonix) + 内容科(格式校验)
- 数据查询 → 工程科(Reasonix)
- 三镜分析/玄学/命理/深度分析 → 情报科(三镜融合) + 审计总(核验)

输出任务分类JSON（仅基于用户任务文本判断，不要编造不存在的细节）："""
    result = json_from_llm(prompt + """
{{
  "intent": "任务类型",
  "params": {{
    "target": "目标/主题",
    "scope": "范围描述",
    "urgency": 1-5,
    "estimated_difficulty": "简单/中等/困难",
    "route": {{
      "tool": "reasonix/claude/liepin/三镜",
      "lead_dept": "工程科/审计总/内容科/情报科",
      "support_depts": ["核验用"],
      "reason": "为什么这样路由"
    }}
  }},
  "brief": "一句话任务概括"
}}""", "flash")
    return {
        "intent": result.get("intent", "其他"),
        "params": result.get("params", {}),
    }


# ─── 方案总 · 出方案 ───

def node_方案总(state: TaskState) -> dict:
    """拆解任务为可执行步骤"""
    params_str = "\n".join(f"  {k}: {v}" for k, v in state.get("params", {}).items())

    prompt = f"""{TRUTHFUL_DIRECTIVE}

你是三总六科AI朝廷的方案总，制定执行方案。

任务意图：{state['intent']}
任务详情：{state['task']}
关键参数：
{params_str}

可选部门（只选必要的，不需要全上）：
- 人事科：工具管理、资源分配
- 数据科：成本核算、token预算
- 内容科：格式校验、模板检查
- 研发科：安全审查、重试策略
- 审计总：质量验证（含Claude Code 6-Block深度评估）
- 工程科：实际生产（代码/分析/内容）
- 情报科：三镜分析（命理/玄学/深度分析）

输出方案JSON（只基于任务类型和参数判断，不编造不存在的信息）："""
    result = json_from_llm(prompt + """
{{
  "rationale": "方案的总体思路（1-2句）",
  "steps": [
    {{
      "step": "01",
      "dept": "对应部门",
      "action": "具体做什么",
      "prompt_suggestion": "执行指令提示",
      "depends_on": []
    }}
  ],
  "estimated_risk": "低/中/高"
}}""", "flash")
    return {
        "plan": result.get("steps", []),
        "plan_rationale": result.get("rationale", ""),
    }


# ─── 门下省 · 方案审核（三模型交叉验证版） ───

def node_门下省(state: TaskState) -> dict:
    """审核方案总方案，有封驳权。重要方案走Consilium三模型交叉验证"""
    steps_str = "\n".join(
        f"  {s.get('step','?')}. [{s.get('dept','?')}] {s.get('action','')}"
        for s in state.get("plan", [])
    )

    is_important = (
        state.get("estimated_risk") == "高" or
        state.get("intent") in ("三镜分析", "求职评估") or
        state.get("review_round", 0) > 0  # 被驳回过
    )

    if is_important:
        # ── 重要任务：Consilium 三模型交叉验证 ──
        review_prompt = f"""{TRUTHFUL_DIRECTIVE}

你是三总六科门下省评审御史。审核以下方案，给出1-10分和具体问题。

用户原始任务：{state['task']}
方案思路：{state.get('plan_rationale', '')}
方案步骤：
{steps_str}
审核轮次：{state.get('review_round', 0) + 1}

审核标准：
1. 部司覆盖是否完整
2. 步骤顺序是否合理
3. 成本是否合理
4. 有无冗余步骤
5. 是否符合用户偏好

评分说明：8分以上=通过，5-7分=边缘通过带建议，5分以下=驳回。"""

        cv_result = consilium_cross_validate(review_prompt, budget=0.04)

        avg_score = cv_result.get("avg_score", 6.0)
        has_issues = len(cv_result.get("issues", [])) > 0

        if avg_score >= 8.0 and not has_issues:
            return {"review_passed": True, "review_feedback": f"三模型交叉验证通过（均分{avg_score:.1f}/10）"}
        elif avg_score >= 5.0:
            feedback = f"三模型交叉验证边缘通过（均分{avg_score:.1f}/10）"
            if has_issues:
                feedback += "。建议关注：\n" + "\n".join(cv_result["issues"][:3])
            return {"review_passed": True, "review_feedback": feedback}
        else:
            return {
                "review_passed": False,
                "review_feedback": f"三模型交叉验证未通过（均分{avg_score:.1f}/10）：\n" + "\n".join(cv_result.get("issues", [])[:5]),
                "review_round": state.get("review_round", 0) + 1,
            }
    else:
        # ── 常规任务：单模型Pro审核 ──
        prompt = f"""{TRUTHFUL_DIRECTIVE}

你是门下省御史，有封驳权。审核方案总方案是否符合要求。

用户任务：{state['task']}
方案思路：{state.get('plan_rationale', '')}
方案步骤：
{steps_str}
轮次：{state.get('review_round', 0) + 1}

审核要点：
1. 用最少的部完成目标
2. 步骤依赖正确
3. 工具选型匹配难度
4. 无冗余步骤（能合并的合并）
5. 大文件I/O走Reasonix不经过Hermes

只输出JSON："""
        result = json_from_llm(prompt + """
{"passed": true/false, "reason": "如果驳回，说明原因和改进建议", "suggested_fixes": ["改进1"]}""", "pro")
        passed = result.get("passed", False)
        if passed:
            return {"review_passed": True, "review_feedback": ""}
        else:
            return {
                "review_passed": False,
                "review_feedback": result.get("reason", "方案不合要求"),
                "review_round": state.get("review_round", 0) + 1,
            }


def should_approve(state: TaskState) -> str:
    """门下省审核的条件路由"""
    if state["review_round"] >= MAX_REVIEW_ROUNDS:
        return "approve"
    return "approve" if state["review_passed"] else "reject"
