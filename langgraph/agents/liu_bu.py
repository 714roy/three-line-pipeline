"""
执行总（调度） + 七部（并行执行：吏户礼兵刑工 + 情报科）

Fable 5 质量标准：诚实报告、只引数据、不编数字。
"""
from lib.state import TaskState, Subtask, reasonix_call, json_from_llm, qmd_search, consilium_cross_validate
import json, subprocess, os

# 诚实指令（注入所有执行prompt）
TRUTHFUL_DIRECTIVE = (
    "\n\n=== 诚实报告规则（违反=不合格） ===\n"
    "1. 只引用输入数据中实际存在的内容。不在数据里的数字/指标/结论→写'不可达'或'无数据'。\n"
    "2. 不可用推测填充未知数据。不知道就说不知道。\n"
    "3. 所有陈述必须附证据来源（哪行数据支撑的）。\n"
    "4. 改进建议用[建议]标注，与事实区分。\n"
    "5. 报告做完了就说做完了，没做完就说没做完。不润色不修饰。"
)


# ─── 执行总 · 派发任务 ───

def node_执行总(state: TaskState) -> dict:
    """把方案总的方案计划拆成可执行的子任务。复盘类任务统一采一次数据"""
    plan = state.get("plan", [])
    subtasks = []
    
    task_str = state['task']
    is_review = any(w in task_str for w in ["复盘", "回顾", "周报", "日报", "汇总", "分析"])
    
    # 复盘/分析任务：统一采一次数据，塞给所有部
    collected_data = ""
    if is_review:
        collected_data = "\n\n=== 三总六科自采数据（来自本机shell，供各部引用） ===\n"
        collected_data += _collect_review_data()
        collected_data += "\n\n=== 数据结束 ==="
    
    # 文件整合类任务：读取指定路径的.md文件
    is_file_task = any(w in task_str for w in ["整合", "读", "文件", "复盘", "每日复盘"])
    if is_file_task:
        file_data = "\n\n=== 三总六科自动读取的每日复盘文件 ===\n"
        import glob as _glob
        review_dir = os.path.expanduser("~/Nutstore Files/知屿/存档库/复盘/")
        review_files = sorted(_glob.glob(os.path.join(review_dir, "每日复盘_2026-06-1*.md")))
        for fpath in review_files:
            fname = os.path.basename(fpath)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                file_data += f"\n--- {fname} ---\n{content[:3000]}\n"
            except Exception as e:
                file_data += f"\n--- {fname} ---\n[读取失败: {e}]\n"
        file_data += "\n=== 文件结束 ==="
        collected_data += file_data

    for i, step in enumerate(plan):
        dept = step.get("dept", "工程科")
        dept_prompts = {
            "人事科": f"资源分配任务：{step.get('prompt_suggestion', step.get('action', ''))}\n检查哪些工具/技能可用，分配最合适的执行方式。",
            "数据科": f"成本核算任务：{step.get('prompt_suggestion', step.get('action', ''))}\n估算token消耗和费用，给出预算建议。",
            "内容科": f"格式校验任务：{step.get('prompt_suggestion', step.get('action', ''))}\n检查格式、模板、风格。",
            "研发科": f"安全检查任务：{step.get('prompt_suggestion', step.get('action', ''))}\n检查敏感操作、failover策略。",
            "审计总": f"质量审查任务：{step.get('prompt_suggestion', step.get('action', ''))}\n验证正确性、检查遗漏。",
            "工程科": f"生产执行任务：{step.get('prompt_suggestion', step.get('action', ''))}\n实际执行{state['task']}的相关工作。",
            "情报科": f"三镜分析任务：{step.get('prompt_suggestion', step.get('action', ''))}\n执行三镜融合分析：一镜(mingyu MCP排盘)→二镜(QMD思维模型)→三镜(全库佐证+Consilium验证)",
        }

        actual_prompt = dept_prompts.get(dept, step.get('prompt_suggestion', step.get('action', '')))
        full_prompt = f"用户任务：{state['task']}\n上下文：{state.get('plan_rationale', '')}\n\n{actual_prompt}\n\n{TRUTHFUL_DIRECTIVE}{collected_data}\n\n请输出执行结果。"

        subtask = Subtask(
            id=f"{dept}_{i+1:02d}",
            dept=dept,
            desc=step.get("action", ""),
            prompt=full_prompt,
            depends_on=step.get("depends_on", []),
            result="",
            cost=0.0,
            model="flash" if dept not in ("门下省", "审计总", "情报科") else "pro",
            status="pending",
        )
        subtasks.append(subtask)

    return {"subtasks": subtasks}


# ─── 七部 · 通用执行器 ───

DEPARTMENT_NAMES = {
    "人事科": "人事科·资源调度",
    "数据科": "数据科·账房核算",
    "内容科": "内容科·格式校验",
    "研发科": "研发科·安全守门",
    "审计总": "审计总·质量巡检（含Claude Code深度评估）",
    "工程科": "工程科·生产执行（含猎聘MCP搜岗、Reasonix蒸馏）",
    "情报科": "情报科·三镜融合（命理/思维模型/全库佐证）",
}

TOOL_ROUTES = {
    "审计总": {
        "job_eval": "claude",
        "default": "reasonix",
    },
    "工程科": {
        "search_jobs": "liepin",
        "distill": "reasonix",
        "default": "reasonix",
    },
    "情报科": {
        "qmd_search": "qmd",
        "consilium": "consilium",
        "default": "reasonix",
    },
}


def _execute_情报科(prompt: str, desc: str) -> str:
    """情报科·三镜融合分析执行器"""
    result_parts = []

    try:
        qmd_results = qmd_search(desc, max_results=5)
        if qmd_results:
            result_parts.append("【一镜·格物】QMD搜索命中：")
            for r in qmd_results[:5]:
                result_parts.append(f"  [{r['source']}] {r['text']}")
        else:
            result_parts.append("【一镜·格物】QMD搜索无直接命中。")
    except Exception as e:
        result_parts.append(f"【一镜·格物】搜索异常：{e}")

    try:
        analysis = reasonix_call(prompt, model="flash", timeout=300)
        result_parts.append(f"\n【二镜·析理】Reasonix分析产出：\n{analysis[:2000]}")
    except Exception as e:
        result_parts.append(f"\n【二镜·析理】分析异常：{e}")

    try:
        cv = consilium_cross_validate(analysis[:2000], budget=0.04)
        if cv["passed"]:
            result_parts.append(f"\n【三镜·合验】Consilium验证通过（均分{cv['avg_score']:.1f}/10）")
        else:
            result_parts.append(f"\n【三镜·合验】Consilium发现问题：\n" + "\n".join(cv["issues"][:3]))
    except Exception as e:
        result_parts.append(f"\n【三镜·合验】验证异常：{e}")

    result_parts.append("\n\n[注意] 完整三镜分析需Hermes调用mingyu MCP八字排盘，当前仅完成了思维模型搜索+Consilium验证。")
    return "\n".join(result_parts)


def _exec_sh(command: str, timeout: int = 15) -> str:
    """在subprocess内执行shell命令采集数据"""
    try:
        r = subprocess.run(
            command, shell=True, capture_output=True, text=True, 
            timeout=timeout, env={**os.environ}
        )
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        if not out and err:
            return f"[error] {err[:200]}"
        return out[:2000] or "[empty]"
    except subprocess.TimeoutExpired:
        return "[timeout]"
    except Exception as e:
        return f"[error] {e}"


def _collect_review_data() -> str:
    """三总六科自己采集复盘数据，不需Hermes预处理"""
    cmds = [
        ("=== 工作产出 ===", ""),
        ("【git日志】", 'cd ~/"Nutstore Files" 2>/dev/null && git log --since="7 days ago" --oneline --all 2>/dev/null | head -20 || echo "不是git仓库"'),
        ("【工坊变更】", 'find ~/"Nutstore Files/工坊" -name "*.md" -mtime -7 -type f 2>/dev/null | head -20 || echo "无"'),
        ("【三总六科项目】", 'ls -lt ~/"Nutstore Files/工坊/项目/三总六科/" 2>/dev/null | head -10'),
        ("", ""),
        ("=== 求职进展 ===", ""),
        ("【求职目录】", 'ls -lt ~/"Nutstore Files/工坊/求职/" 2>/dev/null | head -15'),
        ("【投递记录】", 'head -80 ~/"Nutstore Files/工坊/求职/求职跟踪.md" 2>/dev/null || echo "无投递记录"'),
        ("", ""),
        ("=== 系统状态 ===", ""),
        ("【磁盘】", "df -h / 2>/dev/null | tail -1"),
        ("【内存】", "free -h 2>/dev/null | grep Mem"),
        ("【负载】", "uptime 2>/dev/null"),
        ("【cron产出】", 'ls -lt ~/.hermes/cron/output/ 2>/dev/null | head -8'),
    ]
    
    parts = []
    for label, cmd in cmds:
        if not cmd:
            parts.append(label)
        else:
            parts.append(f"{label} {_exec_sh(cmd)}")
    
    return "\n".join(parts)


def node_六部(state: TaskState) -> dict:
    """七部之一执行具体子任务，需要数据的任务自己采集"""
    subtask = state.get("subtask", state)
    dept = subtask.get("dept", "工程科") if isinstance(subtask, dict) else "工程科"
    task_id = subtask.get("id", "unknown") if isinstance(subtask, dict) else "unknown"
    prompt = subtask.get("prompt", "") if isinstance(subtask, dict) else ""
    desc = subtask.get("desc", "") if isinstance(subtask, dict) else ""
    is_review_task = any(w in desc for w in ["复盘", "回顾", "周报", "日报", "汇总"])
    
    # 复盘/分析任务：先自采数据，再喂给reasonix分析
    if is_review_task:
        collected = _collect_review_data()
        prompt = f"{prompt}\n\n=== 自动采集的数据（来自本机shell） ===\n{collected}"

    dept_header = f"你是三总六科AI朝廷的{DEPARTMENT_NAMES.get(dept, dept)}。\n{TRUTHFUL_DIRECTIVE}"
    full_prompt = f"{dept_header}\n\n{prompt}"

    try:
        model = subtask.get("model", "flash") if isinstance(subtask, dict) else "flash"
        is_job_eval = dept == "审计总" and ("JD" in desc or "评估" in desc or "岗位" in desc)
        is_job_search = dept == "工程科" and ("搜" in desc or "岗位" in desc or "猎聘" in desc)
        is_三镜 = dept == "情报科"

        if is_job_eval:
            from lib.state import claude_code_eval
            result = claude_code_eval(full_prompt, timeout=300)
            cost = 0.01
        elif is_job_search:
            result = "[需通过Hermes调用猎聘MCP] 请陛下在QQ上使用三总六科·求职模式搜岗。"
            cost = 0
        elif is_三镜:
            result = _execute_情报科(full_prompt, desc)
            cost = 0.003
        else:
            result = reasonix_call(full_prompt, model=model, timeout=300)
            cost = 0.0006 if model == "pro" else 0.0003

        return {
            "results": {task_id: result},
            "cost_log": [{"task": task_id, "cost": cost}],
        }
    except Exception as e:
        return {
            "results": {task_id: f"[错误] {str(e)}"},
            "errors": [f"{task_id}: {str(e)}"],
        }


# ─── 门下省 · 产出复查 ───

def node_门下省复查(state: TaskState) -> dict:
    """门下省复查七部产出。第2次打回→呈请陛下裁决"""
    current_round = state.get("output_review_round", 0) + 1

    if state.get("needs_imperial_decision", False):
        return {
            "output_review_passed": True,
            "output_review_feedback": "等待陛下裁决",
            "output_review_round": current_round,
        }

    results_str = "\n\n".join(
        f"=== {task_id} ===\n{result[:2000]}"
        for task_id, result in state.get("results", {}).items()
    )

    prompt = f"""{TRUTHFUL_DIRECTIVE}

你是门下省，复查各部产出是否诚实、完整、准确。

用户任务：{state['task']}
复查轮次：{current_round}

各部产出：
{results_str}

复查要点：
1. 各部是否遵守了诚实报告规则？有没有编造不存在的数据？
2. 产出是否回答了用户任务？
3. 不可达/无数据的环节是否如实标注了？
4. 总体质量能否交付？

只输出JSON："""
    try:
        result = json_from_llm(prompt + """
{"passed": true/false, "reason": "通过理由或驳回原因（具体指出哪部分不合格）", "hallucination_found": "如果发现编造的数据，列出具体位置"}""", "pro")
        passed = result.get("passed", True)
        hallucination = result.get("hallucination_found", "")

        if passed:
            return {
                "output_review_passed": True,
                "output_review_feedback": "复查通过",
                "output_review_round": current_round,
            }
        else:
            reason = result.get("reason", "质量不达标")
            if hallucination:
                reason += f"\n\n[幻觉检测] {hallucination}"

            if current_round >= 2:
                decision_request = f"""🔴 **门下省复查第{current_round}次驳回，呈请陛下裁决**

驳回原因：{reason}

当前各部产出摘要："""
                for task_id, res in state.get("results", {}).items():
                    decision_request += f"\n── {task_id} ──\n{res[:300]}"
                decision_request += "\n\n陛下，以上产出经门下省两次审查仍不合格。请裁决：\n① 准予放行\n② 打回重做\n③ 暂停任务"

                return {
                    "output_review_passed": True,
                    "output_review_feedback": reason,
                    "output_review_round": current_round,
                    "needs_imperial_decision": True,
                    "imperial_decision_request": decision_request,
                }
            else:
                return {
                    "output_review_passed": False,
                    "output_review_feedback": reason,
                    "output_review_round": current_round,
                }
    except Exception as e:
        return {
            "output_review_passed": True,
            "output_review_feedback": f"复查异常，跳过：{e}",
            "output_review_round": current_round,
        }


def should_approve_output(state: TaskState) -> str:
    """产出复查路由"""
    if state.get("needs_imperial_decision", False):
        return "approve"
    if not state["output_review_passed"]:
        return "reject"
    return "approve"


# ─── 督办处 · 汇总 ───

def node_督办处(state: TaskState) -> dict:
    """汇总所有产出为最终报告。需裁决时呈报陛下"""
    if state.get("needs_imperial_decision", False):
        decision_req = state.get("imperial_decision_request", "")
        cost_total = sum(c["cost"] for c in state.get("cost_log", []))
        return {
            "summary": f"# ⚠️ 呈请陛下裁决\n\n{decision_req}\n\n---\n💰 本轮已消耗: ${cost_total:.4f}",
            "total_cost": cost_total,
        }

    results_str = "\n\n".join(
        f"=== {task_id} ({next((s['dept'] for s in state.get('subtasks',[]) if s['id']==task_id),'')}) ===\n{result}"
        for task_id, result in state.get("results", {}).items()
    )
    cost_total = sum(c["cost"] for c in state.get("cost_log", []))

    prompt = f"""{TRUTHFUL_DIRECTIVE}

你是三总六科督办处，汇总今日朝政。

任务：{state['task']}
方案思路：{state.get('plan_rationale', '')}

各部奏报：
{results_str}

总成本：${cost_total:.4f}

汇总要求：
1. 标题行写实际日期，不编造
2. 各部分别列出：完成/不可达/错误，不可达的如实写"不可达"
3. 关键产出只引用各部奏报原文中的数据
4. 不得添加各部奏报中未出现的数字或结论
5. 建议以[建议]前缀开头"""

    summary = reasonix_call(prompt, "flash")

    return {
        "summary": summary,
        "total_cost": cost_total,
    }
