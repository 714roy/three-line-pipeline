"""
三总六科 · 多模式通用版

MODE 由方案总根据任务判断，各部门按需参与。
部门不在当前 mode 时自动跳过不影响下游。

MODE 定义：
  research: 内容科+情报科+工程科      → 调研报告
  build:    工程科+数据科              → 方案设计/项目
  debate:   内容科+人事科+情报科       → 争议/决策评估
  full:     内容科+人事科+情报科+工程科+数据科 → 完整流程

用法：改 TASK → agentflow run 三总六科.py
"""
from sansheng import sansheng_graph
from agentflow import shell

import os

# ⚠️ 注意：--no-config 已移除（2026-06-19），所有 reasonix 节点现在能正常访问 MCP 和 skill。
# 如果遇到 MCP 加载冲突或意外行为，请检查 reasonix 的 config.json 中的 MCP 配置。

# ── 常量 ────────────────────────────────────────────────
PROMPT_DIR = "/tmp/三总六科-prompts"
TASK_FILE = "/tmp/三总六科-TASK.txt"

# ════════════════════════════════════════════════
# ① 任务
# ════════════════════════════════════════════════
def resolve_task():
    env_task = os.environ.get("三总六科TASK")
    if env_task and env_task.strip():
        return env_task
    try:
        with open(TASK_FILE) as f:
            return f.read().strip()
    except (FileNotFoundError, IOError):
        pass
    return "分析任意主题，生成结构化报告"

TASK = resolve_task()

# ── 辅助函数 ─────────────────────────────────────────────


def notify_qq(step: str, msg: str = "完成"):
    # Notification via TRSS_NOTIFY_CMD env var (if set)
    return (
        f"echo '[TRSS] {step} {msg}'\\n"
        + 'NOTIFY_CMD="${TRSS_NOTIFY_CMD:-}"\\n'
        + '[ -n "$NOTIFY_CMD" ] && eval "$NOTIFY_CMD" "$step $msg" 2>/dev/null; true\\n'
    )


def heredoc(name: str, body: str) -> str:
    return f"mkdir -p {PROMPT_DIR} && cat > {PROMPT_DIR}/{name}.md << 'PROMPT_EOF'\n{body}\nPROMPT_EOF\n"


def safe_extract(node_name: str, key: str) -> str:
    """生成安全的 shell 代码，从 agentflow node output 中提取 KEY=VALUE。
    用 heredoc 避免输出中的引号/括号破坏 bash 语法。
    sed 前缀剥除 markdown 格式（**KEY=**、| KEY |）防止 P32/P33 污染。"""
    tmp = f"/tmp/_trss_{node_name}_{key}.txt"
    return (
        f"cat > {tmp} << 'EOF_SS'\n"
        f"{{{{ nodes.{node_name}.output }}}}\n"
        f"EOF_SS\n"
        f'{key}=$(sed "s/^[* |]*//" {tmp} | grep "^{key}=" | tail -1 | cut -d= -f2)\n'
    )


def reasonix(name: str, model: str, budget: str, desc: str, body: str, feedback: bool = False, timeout: int = 300) -> str:
    """reasonix 调用 + 工作描述通知。timeout 秒数防止 pipeline 永远挂起（TD6）。"""
    qq = 'TRSS_NOTIFY_CMD="${TRSS_NOTIFY_CMD:-}"; ' + f"[ -n \"$TRSS_NOTIFY_CMD\" ] && eval \"$TRSS_NOTIFY_CMD\" '📌 {name} {desc}' 2>/dev/null; true"
    cmd = heredoc(name, body)
    if feedback:
        cmd += (
            f'REWORK_TYPE=$(cat /tmp/三总六科-REWORK-TYPE.txt 2>/dev/null || echo "")\n'
            f'if [ -n "$FEEDBACK_FILE" ] && [ -f "$FEEDBACK_FILE" ] && [ "$REWORK_TYPE" != "redesign" ]; then\n'
            f'  echo -e "\\n## 【上轮反馈】\\n$(cat "$FEEDBACK_FILE")" >> {PROMPT_DIR}/{name}.md\n'
            f'fi\n'
        )
    cmd += (
        f"reasonix run -m {model} --budget {budget} "
        + f' --system "$(cat {PROMPT_DIR}/{name}.md)" "请执行上述任务，直接输出结果。"\n'
        + qq + "\n"
    )
    return cmd


# ════════════════════════════════════════════════
# ② 图编排
# ════════════════════════════════════════════════

with sansheng_graph("三总六科", concurrency=3, max_iterations=3) as g:

    # ── 秘书处 · 三镜分析任务本质 ─────────────────
    秘书处 = shell(task_id="秘书处", script=reasonix("秘书处", "deepseek-v4-flash", "0.2",
        "📜 三镜分析任务本质",
        "【角色】你是秘书处左通政——接收奏章（任务），用三镜分析其本质，为方案总决策提供依据。\n"
        "【任务】" + TASK + "\n\n"
        "**请用三镜分析这个任务：**\n\n"
        "**🪞 一镜·格物镜：产出形态分析**\n"
        "问：这个任务最终要产出什么形态的东西？\n"
        "  - 具体内容（如清单/计划/文章/报告/答案/日历）\n"
        "  - 框架方法论（如设计模式/架构/指南/模板/方案书）\n"
        "  - 研究分析（如调研报告/行业分析/对比评估）\n"
        "给出判断和理由。\n\n"
        "**🪞 二镜·析理镜：受众分析**\n"
        "问：谁会直接使用这个产出？\n"
        "  - 终端用户直接执行/阅读（需要具体可操作的内容）\n"
        "  - AI/开发者再加工（需要结构化框架）\n"
        "  - 多人协作参考（需要通用模板）\n"
        "给出判断和理由。\n\n"
        "**🪞 三镜·合验镜：定制化分析**\n"
        "问：这个产出需要多深入的定制？\n"
        "  - 高度个性化（基于特定数据/条件/约束）\n"
        "  - 通用方案（可套用到同类场景）\n"
        "  - 学术深度（需要完整的研究方法）\n"
        "给出判断和理由。\n\n"
        "**综合判断：**\n"
        "基于以上三镜分析，推荐产出类型和模式。请严格区分：\n"
        "  - TYPE=project → 需要设计方案/架构/框架，工程科产出方案。如：APP设计、系统架构、产品规划\n"
        "  - TYPE=document → 需要具体内容/答案/推荐，内容科直接出。如：学习计划、购物清单、文章、报告\n"
        "  - **关键区分**：用户要的是「我的专属xx」还是「通用的xx方法论」？前者是 document，后者是 project\n\n"
        "**路由决策：**\n"
        "判断这个任务是否需要走完整三总六科流程。规则：\n"
        "  - ROUTE=direct → 简单任务：单一事实性问题/快速调研/已有明确答案的咨询，直接一个 reasonix 调用即可回答\n"
        "  - ROUTE=pipeline → 复杂任务：多维度调研/方案设计/报告生成/个性化计划，需要多个部门协作输出\n"
        "判断依据：任务是否涉及多个独立的子问题、是否需要跨源验证、是否最终产出是一份正式文档\n\n"
        "输出格式：\n"
        "先输出一段三镜分析正文（你的分析过程和结论）\n"
        "***最后单独一行*** 输出：MODE=<推荐的模式>\n"
        "***倒数第二行*** 输出：TYPE=<project|document>\n"
        "***倒数第三行*** 输出：ROUTE=direct 或 ROUTE=pipeline\n"
        "***倒数第四行*** 输出：OUTPUT_NATURE=<具体内容|框架方法论|研究分析>\n"
        "***倒数第五行*** 输出：AUDIENCE=<终端用户|开发者/AI|多人协作>\n"
        "***倒数第六行*** 输出：CUSTOMIZATION=<高度个性化|通用方案|学术深度>"
    ))

    # ── 秘书处通知 ─────────────────────────
    秘书处通知 = shell(task_id="秘书处通知", script=(
'test -f /tmp/三总六科-STOP.txt && exit 0\n' +         # 提取秘书处 ROUTE 判断
        "cat > /tmp/_trss_ROUTE.txt << 'EOF_SS'\n"
        + "{{ nodes.秘书处.output }}\n"
        + "EOF_SS\n"
        + 'ROUTE=$(sed "s/^[* |]*//" /tmp/_trss_ROUTE.txt | grep "^ROUTE=" | tail -1 | cut -d= -f2)\n'
        + 'echo "$ROUTE" > /tmp/三总六科-ROUTE.txt\n'
        + 'MODE=$(sed "s/^[* |]*//" /tmp/_trss_ROUTE.txt | grep "^MODE=" | tail -1 | cut -d= -f2)\n'
        + 'echo "$MODE" > /tmp/三总六科-CUR-MODE.txt\n'
        + 'if echo "$ROUTE" | grep -Eqi "direct"; then\n'
        # direct 模式：直接 reasonix 回答+归档，后续部门跳过
        + notify_qq("📜", "秘书处 判定简单任务，直达回答")
        + "  mkdir -p /tmp/三总六科-prompts\n"
        + "  cat > /tmp/三总六科-prompts/秘书处直答.md << 'PROMPT_EOF'\n"
        + "【角色】你是秘书处——快速回答用户的问题。基于你的知识，给出简洁准确的答案。\n"
        + f"【任务】{TASK}\n"
        + "直接输出答案，不需要分析过程。格式不限，准确第一。\n"
        + "PROMPT_EOF\n"
        + "  reasonix run -m deepseek-v4-flash --budget 0.2 --system \"$(cat /tmp/三总六科-prompts/秘书处直答.md)\" \"请执行上述任务。\" > /tmp/三总六科-direct-answer.txt 2>/dev/null\n"
        # 归档
        + '  OUTPUT_NAME=$(sed "s/^[* |]*//" /tmp/_trss_ROUTE.txt | grep "^TYPE=" | tail -1 | cut -d= -f2)\n'
        + '  DEST="${TRSS_OUTPUT_DIR:-$HOME/output/trss/direct}"\n'
        + '  mkdir -p "$DEST/产出"\n'
        + '  cp /tmp/三总六科-direct-answer.txt "$DEST/产出/${OUTPUT_NAME:-answer}.md"\n'
        + '  cp /tmp/三总六科-TASK.txt "$DEST/TASK.txt" 2>/dev/null; true\n'
        + notify_qq("📦", "归档: 秘书处直答")
        + notify_qq("🏁", "三总六科快速通道完成")
        + '  touch /tmp/三总六科-STOP.txt\n'
        + '  exit 0\n'
        + 'fi\n'
        + notify_qq("📜", "秘书处 三镜分析完毕")))

    # ── 方案总 · 任务拆解 + 推荐 MODE ─────────────────
    方案总 = shell(task_id="方案总", script=(
'test -f /tmp/三总六科-STOP.txt && exit 0\n' +         # ROUTE=direct 快速跳过
        'test -f /tmp/三总六科-ROUTE.txt && grep -qi "direct" /tmp/三总六科-ROUTE.txt && echo "【SKIP】快速通道跳过方案总" && exit 0\n'
        # 第二轮跳过方案总——除非是 redesign 重拆
        'REWORK_TYPE=$(cat /tmp/三总六科-REWORK-TYPE.txt 2>/dev/null || echo "")\n'
        'if [ "$ROUND" -gt 1 ] && [ "$REWORK_TYPE" != "redesign" ]; then\n'
        '  echo "【SKIP】第二轮跳过方案总重拆"\n'
        '  exit 0\n'
        'fi\n'
        # redesign 时注入上轮反馈
        + 'if [ "$REWORK_TYPE" = "redesign" ] && [ -n "$FEEDBACK_FILE" ] && [ -f "$FEEDBACK_FILE" ]; then\n'
        + '  echo -e "\n【上轮反馈】\n$(cat "$FEEDBACK_FILE")" >> /tmp/三总六科-prompts/方案总.md\n'
        + 'fi\n'
        + reasonix("方案总", "deepseek-v4-flash", "0.3",
            "🏛️ 拆解任务并推荐模式",
            "【角色】你是方案总丞相——宏观视角，为【任务】制定执行框架并推荐运行模式。\n"
            "【任务】" + TASK + "\n\n"
            "【秘书处三镜分析】\n{{ nodes.秘书处.output }}\n\n"
            "请完成：\n"
            "1. 拆解任务为3-5个子问题，明确调研方向\n"
            "2. 判断任务产出类型：\n"
            "   - project（项目类）：需要设计方案、架构、框架 → 工程科产出方案\n"
            "   - document（文档类）：需要具体内容、推荐、答案 → 内容科直接出内容，跳过工程科\n"
            "3. 根据任务类型选择最合适的运行模式：\n"
            "   - research：市场调研、行业分析、资料搜集（内容科调研→情报科核验→工程科方案）\n"
            "   - build：方案设计、代码项目、产品规划（工程科方案→数据科评估）\n"
            "   - debate：决策评估、争议分析、方案对比（内容科调研→人事科提炼→情报科核验）\n"
            "   - full：需要全流程的复杂任务（所有部门参与）\n"
            "3. 给出整体策略建议\n\n"
            "输出格式：JSON，包含 sub_questions（数组）、recommended_mode（字符串）、type（project或document）、rationale（理由）。\n"
            "***最后单独一行*** 输出：MODE=<推荐的模式>\n"
            "***倒数第二行*** 输出：TYPE=<project|document>"
        )
    ))

    # ── 方案总通知 ──────────────────────────────
    方案总通知 = shell(task_id="方案总通知", script=(
'test -f /tmp/三总六科-STOP.txt && exit 0\n' +         'REWORK_TYPE=$(cat /tmp/三总六科-REWORK-TYPE.txt 2>/dev/null || echo "")\n'
        'if [ "$ROUND" -gt 1 ] && [ "$REWORK_TYPE" != "redesign" ]; then\n'
        '  echo "【SKIP】第二轮跳过"\n'
        '  exit 0\n'
        'fi\n'
        # 提取方案总推荐模式并保存
        + "cat > /tmp/_trss_中书_MODE.txt << 'EOF_SS'\n"
        + "{{ nodes.方案总.output }}\n"
        + "EOF_SS\n"
        + 'MODE=$(sed "s/^[* |]*//" /tmp/_trss_中书_MODE.txt | grep "^MODE=" | tail -1 | cut -d= -f2)\n'
        + 'echo "$MODE" > /tmp/三总六科-CUR-MODE.txt\n'
        + notify_qq("🏛️", "方案总 方案已出")))

    # ── 审核总 · 审核方案 + 确认 MODE ─────────
    审核总 = shell(task_id="审核总", script=(
        'test -f /tmp/三总六科-STOP.txt && exit 0\n'
'test -f /tmp/三总六科-ROUTE.txt && grep -qi "direct" /tmp/三总六科-ROUTE.txt && echo "【SKIP】快速通道跳过一审" && exit 0\n'
        'REWORK_TYPE=$(cat /tmp/三总六科-REWORK-TYPE.txt 2>/dev/null || echo "")\n'
        'if [ "$ROUND" -gt 1 ] && [ "$REWORK_TYPE" != "redesign" ]; then\n'
        '  cat /tmp/三总六科-MODE.txt 2>/dev/null; cat /tmp/三总六科-TYPE.txt 2>/dev/null\n'
        '  echo "【SKIP】第二轮跳过一审审核"\n'
        '  exit 0\n'
        'fi\n'
        + reasonix("审核总", "deepseek-v4-flash", "0.3",
            "🔍 审核方案 + 改进方案",
            "【角色】你是审核总官——审核方案总的方案，**大问题打回，小问题直接修好**。你的输出就是后续部门的执行依据。\n"
            "【任务】" + TASK + "\n\n"
            "方案总原方案如下：\n{{ nodes.方案总.output }}\n\n"
            "请完成：\n"
            "1. **评估是否存在大问题**：方向错误、模式完全不匹配、遗漏关键子问题、任务理解偏差\n"
            "2. **有大问题（VERDICT=重拆）**：详细说明问题所在 + 给出具体修改建议，供方案总重做\n"
            "3. **没大问题（VERDICT=pass）**：**直接优化完善方案总方案**——修正小问题（补充遗漏、优化结构、精炼描述、纠正偏差），输出你修改后的完善方案\n\n"
            "核心原则：如果你的 VERDICT=pass，你的输出正文就是后续部门将参考的完善方案。不要只写审核意见，要写你修改后的好东西。\n\n"
            "***最后单独一行*** 输出：MODE=<最终确定的模式>\n"
            "***倒数第二行*** 输出：TYPE=<project|document>\n"
            "***倒数第三行*** 输出：VERDICT=pass 或 VERDICT=重拆\n"
            "***倒数第四行*** 输出：FEEDBACK=<如果重拆，给出具体要修改的内容>"
        )
    ))

    # ── 一审通知 ──────────────────────────────
    审核总通知 = shell(task_id="审核总通知", script=(
'test -f /tmp/三总六科-STOP.txt && exit 0\n' +         'REWORK_TYPE=$(cat /tmp/三总六科-REWORK-TYPE.txt 2>/dev/null || echo "")\n'
        'if [ "$ROUND" -gt 1 ] && [ "$REWORK_TYPE" != "redesign" ]; then\n'
        '  echo "【SKIP】第二轮跳过"\n'
        '  exit 0\n'
        'fi\n'
        # 提取一审确认模式并覆盖保存
        + "cat > /tmp/_trss_一审_MODE.txt << 'EOF_SS'\n"
        + "{{ nodes.审核总.output }}\n"
        + "EOF_SS\n"
        + 'MODE=$(sed "s/^[* |]*//" /tmp/_trss_一审_MODE.txt | grep "^MODE=" | tail -1 | cut -d= -f2)\n'
        + '[ -n "$MODE" ] && echo "$MODE" > /tmp/三总六科-CUR-MODE.txt\n'
        + notify_qq("🔍", "审核总 审核完毕")))

    # ── 内容科 · 调研（所有 mode 通用）─────────────
    内容科 = shell(task_id="内容科", script=(
        'test -f /tmp/三总六科-STOP.txt && exit 0\n'
'test -f /tmp/三总六科-ROUTE.txt && grep -qi "direct" /tmp/三总六科-ROUTE.txt && echo "【SKIP】快速通道跳过内容科" && exit 0\n'
        + safe_extract("审核总", "MODE")
        + safe_extract("审核总", "TYPE")
        + 'if ! echo "$MODE" | grep -Eqi "research|debate|full"; then\n'
        + '  echo "【SKIP】当前模式($MODE)无需内容科"\n'
        + '  echo "[TRSS] 📌 内容科 跳过" && [ -n "${TRSS_NOTIFY_CMD:-}" ] && eval "${TRSS_NOTIFY_CMD}" "📌 内容科 跳过" 2>/dev/null; true\n'
        + '  exit 0\n'
        + 'fi\n'
        + reasonix("内容科", "deepseek-v4-flash", "0.5",
            "📚 调研关键事实与维度",
            "【角色】你是内容科调研官——信息广、角度多、善于发现关键线索。\n"
            "【任务】" + TASK + "\n"
            "【产出类型】TYPE={{ nodes.审核总.output }}\n\n"
            "请根据产出类型调整输出：\n"
            "  如果 TYPE=document（文档类）：直接输出具体内容/推荐/答案，不要方法论，直接给出干货。\n"
            "    ⚠️ 个性化方案铁律（P29）：如果是用户的个人计划/方案/日程，先思考用户可能已有哪些资源（课程/工具/历史方案等），\n"
            "    基于已有资源做延伸，切勿只给泛泛的通用推荐。\n"
            "  如果 TYPE=project（项目类）：按常规调研，输出关键事实、数据、维度分析。\n\n"
            "输出格式：Markdown。文档类直接给答案，项目类200字以内分维度。",
            feedback=True
        )
    ))

    # ── 人事科 · 提炼（debate, full 模式）────────────
    人事科 = shell(task_id="人事科", script=(
        'test -f /tmp/三总六科-STOP.txt && exit 0\n'
'test -f /tmp/三总六科-ROUTE.txt && grep -qi "direct" /tmp/三总六科-ROUTE.txt && echo "【SKIP】快速通道跳过人事科" && exit 0\n'
        + safe_extract("审核总", "MODE")
        + 'if ! echo "$MODE" | grep -Eqi "debate|full"; then\n'
        + '  echo "【SKIP】当前模式($MODE)无需人事科"\n'
        + '  echo "[TRSS] 📌 人事科 跳过" && [ -n "${TRSS_NOTIFY_CMD:-}" ] && eval "${TRSS_NOTIFY_CMD}" "📌 人事科 跳过" 2>/dev/null; true\n'
        + '  exit 0\n'
        + 'fi\n'
        + reasonix("人事科", "deepseek-v4-flash", "0.3",
            "✂️ 提炼核心要点",
            "【角色】你是人事科主笔——擅提炼、抓重点。\n"
            "基于内容科调研（{{ nodes.内容科.output }}）提炼核心要点：\n"
            "1. 最重要的3-5个关键发现\n"
            "2. 各发现之间的逻辑关系或矛盾点\n"
            "3. 初步结论性判断\n\n"
            "输出格式：3-5条精炼要点，每条不超过80字。"
        )
    ))

    # ── 情报科 · 核验（research, debate, full 模式）─
    情报科 = shell(task_id="情报科", script=(
        'test -f /tmp/三总六科-ROUTE.txt && grep -qi "direct" /tmp/三总六科-ROUTE.txt && echo "【SKIP】快速通道跳过情报科" && exit 0\n'
        + safe_extract("审核总", "MODE")
        + 'if ! echo "$MODE" | grep -Eqi "research|debate|full"; then\n'
        + '  echo "【SKIP】当前模式($MODE)无需情报科"\n'
        + '  echo "[TRSS] 📌 情报科 跳过" && [ -n "${TRSS_NOTIFY_CMD:-}" ] && eval "${TRSS_NOTIFY_CMD}" "📌 情报科 跳过" 2>/dev/null; true\n'
        + '  exit 0\n'
        + 'fi\n'
        + reasonix("情报科", "deepseek-v4-flash", "0.3",
            "🔎 核验事实盲点",
            "【角色】你是情报科复核官——敏锐、较真。\n"
            "对人事科/内容科要点进行核验：\n"
            "  内容科调研：{{ nodes.内容科.output }}\n"
            "  人事科提炼：{{ nodes.人事科.output }}\n\n"
            "请完成：\n"
            "1. 是否存在事实盲点、过度简化或遗漏\n"
            "2. 哪些方面值得质疑，常见信息偏差是什么\n"
            "3. 复核结论（通过/需修正/驳回）\n\n"
            "输出格式：核验结论 + 修正建议，150字以内。"
        )
    ))

    # ── 工程科 · 方案设计（research, build, full 模式）─
    工程科 = shell(task_id="工程科", script=(
        'test -f /tmp/三总六科-STOP.txt && exit 0\n'
'test -f /tmp/三总六科-ROUTE.txt && grep -qi "direct" /tmp/三总六科-ROUTE.txt && echo "【SKIP】快速通道跳过工程科" && exit 0\n'
        + safe_extract("审核总", "MODE")
        + safe_extract("审核总", "TYPE")
        + 'if ! echo "$MODE" | grep -Eqi "research|build|full"; then\n'
        + '  echo "【SKIP】当前模式($MODE)无需工程科"\n'
        + '  echo "[TRSS] 📌 工程科 跳过" && [ -n "${TRSS_NOTIFY_CMD:-}" ] && eval "${TRSS_NOTIFY_CMD}" "📌 工程科 跳过" 2>/dev/null; true\n'
        + '  exit 0\n'
        + 'fi\n'
        + 'if echo "$TYPE" | grep -Eqi "document"; then\n'
        + '  echo "【SKIP】文档类任务无需工程科出方案"\n'
        + '  echo "[TRSS] 📌 工程科 跳过" && [ -n "${TRSS_NOTIFY_CMD:-}" ] && eval "${TRSS_NOTIFY_CMD}" "📌 工程科 跳过" 2>/dev/null; true\n'
        + '  exit 0\n'
        + 'fi\n'
        + reasonix("工程科", "deepseek-v4-flash", "0.3",
            "🔧 设计方案/指南",
            "【角色】你是工程科匠作官——善于把信息转化为可执行的方案。\n"
            "依赖上下文（根据 MODE 使用可用的）：\n"
            "  内容科调研：{{ nodes.内容科.output }}\n"
            "  情报科核验：{{ nodes.情报科.output }}\n\n"
            "为【任务】产出可落地的方案/指南/框架：\n"
            "1. 核心方案设计（结构清晰，可操作）\n"
            "2. 实施路径或执行建议\n"
            "3. 注意事项和风险提示\n\n"
            "输出格式：Markdown结构化文档。标题用# 一级标题写明方案全称。",
            feedback=True
        )
    ))

    # ── 数据科 · 评估（build, full 模式）─────────────
    数据科 = shell(task_id="数据科", script=(
        'test -f /tmp/三总六科-STOP.txt && exit 0\n'
'test -f /tmp/三总六科-ROUTE.txt && grep -qi "direct" /tmp/三总六科-ROUTE.txt && echo "【SKIP】快速通道跳过数据科" && exit 0\n'
        + safe_extract("审核总", "MODE")
        + 'if ! echo "$MODE" | grep -Eqi "build|full"; then\n'
        + '  echo "【SKIP】当前模式($MODE)无需数据科"\n'
        + '  echo "[TRSS] 📌 数据科 跳过" && [ -n "${TRSS_NOTIFY_CMD:-}" ] && eval "${TRSS_NOTIFY_CMD}" "📌 数据科 跳过" 2>/dev/null; true\n'
        + '  exit 0\n'
        + 'fi\n'
        + reasonix("数据科", "deepseek-v4-flash", "0.3",
            "💰 评估可行性",
            "【角色】你是数据科度支官——务实，算成本、估难度。\n"
            "对工程科方案（{{ nodes.工程科.output }}）进行评估：\n"
            "1. 可行性（成本/复杂度/前置条件）\n"
            "2. 可能被低估的难点\n"
            "3. 精简/优化建议\n\n"
            "输出格式：评估 + 建议，200字以内。"
        )
    ))

    # ── 门下省二审 · 审核 + 路由 + 命名 ────────────
    质控总 = shell(task_id="质控总", script=(
        'test -f /tmp/三总六科-STOP.txt && exit 0\n'
'test -f /tmp/三总六科-ROUTE.txt && grep -qi "direct" /tmp/三总六科-ROUTE.txt && echo "【SKIP】快速通道跳过二审" && exit 0\n'
        + reasonix("质控总", "deepseek-v4-flash", "0.3",
        "✅ 审核质量并指定归档",
        "【角色】你是门下省审核官——**评估问题严重性，区分致命与改进建议**。\n"
        "【任务】" + TASK + "\n"
        "【MODE】{{ nodes.审核总.output }}\n\n"
        "审核以下各部门产出，按以下标准严格检查：\n"
        "1. 内容是否完整（有无明显遗漏）\n"
        "2. 数据/事实是否准确（有无明显错误）\n"
        "3. 结构是否清晰合理\n"
        "4. 是否适合直接交付给用户\n\n"
        "**你的职责是判断问题严重性：致命问题（事实错误/遗漏严重/无法交付）→ VERDICT=需重做；小问题（格式/数据源/可优化项）→ VERDICT=pass，在 JSON 中记录到 NOTES 字段供归档参考。**\n\n"
        "然后：\n"
        "1. 输出完整 JSON 审核结论和路由表（含对每个部门的评价和路由决定）\n"
        "2. **输出**：VERDICT=pass 或 VERDICT=需重做\n"
        "3. **输出**：FEEDBACK=<如果需重做，给出具体要修改的内容>\n"
        "4. **最后单独一行**输出：OUTPUT_NAME=<方案文件名（不含后缀）>（纯文本，不加 markdown 格式）\n"
        "   例如：OUTPUT_NAME=上海缅因猫市场调研与选购指南\n"
        "   规则：工程科方案的标题经过精炼，作为产出文件名。\n"
        "5. **最后一行**输出：ARCHIVE_PATH=<你判断的归档根路径>（纯文本，不加 markdown 格式）\n"
        "   例如：ARCHIVE_PATH=知屿/存档库/上海缅因猫市场\n"
        "         或 ARCHIVE_PATH=工坊/项目/上海缅因猫市场调查\n"
        "   规则：工程科（主方案）若适合当项目放工坊/项目/xxx，否则放知屿/存档库/xxx\n\n"
        "产出预览：\n"
        "  内容科：{{ nodes.内容科.output }}\n"
        "  人事科：{{ nodes.人事科.output }}\n"
        "  情报科：{{ nodes.情报科.output }}\n"
        "  工程科：{{ nodes.工程科.output }}\n"
        "  数据科：{{ nodes.数据科.output }}\n"
        "  方案总：{{ nodes.方案总.output }}"
    )))
    # 注意：以上三个括号依次为：reasonix() 结束、script=(...) 结束、shell(...) 结束

    # ── 质控检查：如果二审判重做，写信号文件 ──
    质控检查 = shell(task_id="质控检查", script=(
'test -f /tmp/三总六科-STOP.txt && exit 0\n' +         'MODE=$(cat /tmp/三总六科-CUR-MODE.txt 2>/dev/null || echo "?")\n'
        # 读二审 output 文件
        + 'RUN_DIR=$(ls -dt .agentflow/runs/*/ 2>/dev/null | head -1)\n'
        + 'infile="$RUN_DIR/artifacts/质控总/output.txt"\n'
        + 'if [ -f "$infile" ] && grep -qi "需重做" "$infile" 2>/dev/null; then\n'
        + '  touch /tmp/三总六科-SKIP审计总.txt\n'
        + '  echo "二审判定需重做，已标记跳过审计总"\n'
        + '  echo "[TRSS] ⏭️ 二审 需重做，跳过审计总" && [ -n "${TRSS_NOTIFY_CMD:-}" ] && eval "${TRSS_NOTIFY_CMD}" "⏭️ 二审 需重做，跳过审计总" 2>/dev/null; true\n'
        + 'else\n'
        + '  rm -f /tmp/三总六科-SKIP审计总.txt\n'
        + '  echo "二审通过，审计总正常审计"\n'
        + '  echo "[TRSS] ✅ 二审 通过，审计总审计" && [ -n "${TRSS_NOTIFY_CMD:-}" ] && eval "${TRSS_NOTIFY_CMD}" "✅ 二审 通过，审计总审计" 2>/dev/null; true\n'
        + 'fi\n'
    ))

    # ── 审计总审计 ──────────────────────────────
    审计总 = shell(task_id="审计总", script=(
        'test -f /tmp/三总六科-STOP.txt && exit 0\n'
'test -f /tmp/三总六科-ROUTE.txt && grep -qi "direct" /tmp/三总六科-ROUTE.txt && echo "【SKIP】快速通道跳过审计总" && exit 0; '
        + "echo '===== 审计总审计 ====='\\\n"
        # 检查是否要跳过——全在一行，不用换行
        + '; '  # 分隔前一个echo
        + 'if test -f /tmp/三总六科-SKIP审计总.txt; then '
        + '  echo "【SKIP】二审已判重做,跳过审计总审计"; '
        + '  echo "VERDICT=rework"; '
        + '  echo "[TRSS] ⚖️ 审计总 二审已判重做,跳过审计" && [ -n "${TRSS_NOTIFY_CMD:-}" ] && eval "${TRSS_NOTIFY_CMD}" "⚖️ 审计总 二审已判重做,跳过审计" 2>/dev/null; true'
        + '  exit 0; '
        + 'fi; '
        + notify_qq("⚖️", "审计总 审计中")
        + reasonix("审计总", "deepseek-v4-flash", "0.3",
            "⚖️ 审计 + 改进",
            "【角色】你是审计总御史——**大问题打回方案总重做，小问题直接修好交给督办处归档**。\n"
            "【任务】" + TASK + "\n\n"
            "审计以下各部门产出质量（注意：跳过的部门输出【SKIP】，应评价为\"跳过\"而不扣分）：\n"
            "  方案总: {{ nodes.方案总.output }}\n"
            "  审核总: {{ nodes.审核总.output }}\n"
            "  内容科: {{ nodes.内容科.output }}\n"
            "  人事科: {{ nodes.人事科.output }}\n"
            "  情报科: {{ nodes.情报科.output }}\n"
            "  工程科: {{ nodes.工程科.output }}\n"
            "  数据科: {{ nodes.数据科.output }}\n"
            "  门下省二审（含NOTES）：{{ nodes.质控总.output }}\n\n"
            "请完成：\n"
            "1. **评估是否存在大问题**：事实性错误、致命逻辑漏洞、关键遗漏导致产出不可用\n"
            "2. **有大问题（VERDICT=rework）**：详细说明问题所在 + 给方案总的修改建议，要求重做\n"
            "3. **没大问题（VERDICT=pass）**：根据二审的 NOTES 和你的审计发现，修正各部门产出中的小问题，输出你修改后的完善版本。这个版本就是最终归档的内容。\n\n"
            "核心原则：\n"
            "- VERDICT=pass 时，你的输出正文就是**最终完善后的产出**，不要只写审计意见要写改好的东西\n"
            "- 如果二审 NOTES 中有可优化项，你应该在完善版本中一并处理\n"
            "- 被跳过的部门（标有【SKIP】）不需要评价\n\n"
            "***最后单独一行***  输出：VERDICT=pass 或 VERDICT=rework\n"
            "***倒数第二行***    输出：REWORK_TYPE=redesign （只有需打回方案总重做的才标 redesign，一般重做留空）\n"
            "***倒数第三行***    输出：FEEDBACK=<要修改的内容，给方案总>"
            # AUDIT_ISSUE 不再需要——审计总现在同时审计和改进
        )
    ))

    # ── 审计总通知 ────────────────────────────
    审计总通知 = shell(task_id="审计总通知", script=(
'test -f /tmp/三总六科-STOP.txt && exit 0\n' +         'MODE=$(cat /tmp/三总六科-CUR-MODE.txt 2>/dev/null || echo "?")\n'
        + notify_qq("⚖️", "审计总 审计完毕")))

    # ── 督办处（先归档再判 verdict） ─────
    督办处 = shell(task_id="督办处", script=(
'if test -f /tmp/三总六科-STOP.txt; then exit 0; fi\n'
        + "RUN_DIR=$(ls -dt /tmp/sansheng/.agentflow/runs/*/ 2>/dev/null | head -1)\n"
        + "echo '===== 三总六科呈报 ====='\n"
        "echo '任务: " + TASK + "'\n"
        "echo ''\n"
        # ── ① 先归档（无论 verdict，确保产出不丢）──
        # 提取 OUTPUT_NAME / ARCHIVE_PATH 从二审
        + "cat > /tmp/_trss_二审.txt << 'EOF_SS'\n"
        + "{{ nodes.质控总.output }}\n"
        + "EOF_SS\n"
        + "cat > /tmp/三总六科-提取归档.py << 'PYEOF'\n"
        + "import re\n"
        + 'txt = open("/tmp/_trss_二审.txt").read()\n'
        + "def extract(key):\n"
        + '    pat = re.compile(r"\\\\*{0,2}" + key + r"\\\\*{0,2}[=:]\\\\*{0,2}\\\\s*(.+?)\\\\s*(?:\\\\*|$|\\\\||)", re.MULTILINE)\n'
        + "    m = pat.search(txt)\n"
        + '    return m.group(1).strip() if m else ""\n'
        + 'name = extract("OUTPUT_NAME")\n'
        + 'path = extract("ARCHIVE_PATH")\n'
        + 'print(f"OUTPUT_NAME={name}")\n'
        + 'print(f"ARCHIVE_PATH={path}" if path else "ARCHIVE_PATH=知屿/存档库/三总六科")\n'
        + "PYEOF\n"
        + "python3 /tmp/三总六科-提取归档.py > /tmp/三总六科-归档提取.txt 2>/dev/null\n"
        + 'OUTPUT_NAME=$(grep "^OUTPUT_NAME=" /tmp/三总六科-归档提取.txt | cut -d= -f2-)\n'
        + 'ARCHIVE_BASE=$(grep "^ARCHIVE_PATH=" /tmp/三总六科-归档提取.txt | cut -d= -f2-)\n'
        + 'DEST="${TRSS_OUTPUT_DIR:-$HOME/output/trss}/$ARCHIVE_BASE"\n'
        + 'mkdir -p "$DEST/产出"\n'
        # 从内容科/工程科取主产出
        + "cat > /tmp/_trss_一审.txt << 'EOF_SS'\n"
        + "{{ nodes.审核总.output }}\n"
        + "EOF_SS\n"
        + 'TYPE=$(sed "s/^[* |]*//" /tmp/_trss_一审.txt | grep "^TYPE=" | tail -1 | cut -d= -f2)\n'
        + 'if echo "$TYPE" | grep -Eqi "document"; then SRC_NODE="内容科"; else SRC_NODE="工程科"; fi\n'
        + 'NAME="${OUTPUT_NAME:-方案}"\n'
        + 'if [ -n "$RUN_DIR" ]; then\n'
        + '  infile="$RUN_DIR/artifacts/$SRC_NODE/output.txt"\n'
        + '  if [ -f "$infile" ] && ! grep -q "^【SKIP】" "$infile" 2>/dev/null; then\n'
        + '    cp "$infile" "$DEST/产出/${NAME}.md" 2>/dev/null; fi\n'
        + '  infile="$RUN_DIR/artifacts/审计总/output.txt"\n'
        + '  if [ -f "$infile" ]; then\n'
        + '    cp "$infile" "$DEST/产出/审计报告.md" 2>/dev/null; fi\n'
        + '  infile="$RUN_DIR/artifacts/质控总/output.txt"\n'
        + '  if [ -f "$infile" ]; then\n'
        + '    cp "$infile" "$DEST/产出/路由表.json" 2>/dev/null; fi\n'
        + 'fi\n'
        + 'cp /tmp/三总六科-TASK.txt "$DEST/TASK.txt" 2>/dev/null; true\n'
        # 清除 MCP 噪音
        + 'for f in "$DEST/产出/"*.md; do\n'
        + '  [ -f "$f" ] || continue\n'
        + '  head -1 "$f" | grep -q "^\\[tool agentmemory_" || continue\n'
        + '  sed -i "0,/^# /{//!d}" "$f" 2>/dev/null; done\n'
        + 'echo "✅ 产出已整理: $DEST/产出/" >> "$DEST/产出/README.md" 2>/dev/null\n'
        + 'echo "[TRSS] 📦 归档: 秘书处直答" && [ -n "${TRSS_NOTIFY_CMD:-}" ] && eval "${TRSS_NOTIFY_CMD}" "📦 归档: 秘书处直答" 2>/dev/null; true\n'
        + 'echo "[TRSS] 📄 产出: $ARCHIVE_BASE/产出/" && [ -n "${TRSS_NOTIFY_CMD:-}" ] && eval "${TRSS_NOTIFY_CMD}" "📄 产出: $ARCHIVE_BASE/产出/" 2>/dev/null; true\n'
        # ── ② 判 verdict ──
        + 'VERDICT_RESULT=pass\n'
        + "cat > /tmp/_trss_v1.txt << 'EOF_SS'\n"
        + "{{ nodes.审核总.output }}\n"
        + "EOF_SS\n"
        + 'V1=$(sed "s/^[* |]*//" /tmp/_trss_v1.txt | grep "^VERDICT=" | tail -1 | cut -d= -f2)\n'
        + 'if echo "$V1" | grep -Eqi "重拆"; then\n'
        + '  FEEDBACK=$(sed "s/^[* |]*//" /tmp/_trss_v1.txt | grep "^FEEDBACK=" | tail -1 | cut -d= -f2-)\n'
        + '  echo "$FEEDBACK" > /tmp/三总六科-FEEDBACK.txt\n'
        + '  echo redesign > /tmp/三总六科-REWORK-TYPE.txt\n'
        + '  echo rework > /tmp/三总六科-REWORK.txt\n'
        + '  VERDICT_RESULT=rework\n'
        + '  echo "[TRSS] 🔄 一审判定需重拆方案" && [ -n "${TRSS_NOTIFY_CMD:-}" ] && eval "${TRSS_NOTIFY_CMD}" "🔄 一审判定需重拆方案" 2>/dev/null; true\n'
        + 'fi\n'
        + 'if [ "$VERDICT_RESULT" = "pass" ]; then\n'
        + "  cat > /tmp/_trss_v2.txt << 'EOF_SS'\n"
        + "{{ nodes.质控总.output }}\n"
        + "EOF_SS\n"
        + '  V2=$(sed "s/^[* |]*//" /tmp/_trss_v2.txt | grep "^VERDICT=" | tail -1 | cut -d= -f2)\n'
        + '  if echo "$V2" | grep -Eqi "重做"; then\n'
        + '    FEEDBACK=$(sed "s/^[* |]*//" /tmp/_trss_v2.txt | grep "^FEEDBACK=" | tail -1 | cut -d= -f2-)\n'
        + '    echo "$FEEDBACK" > /tmp/三总六科-FEEDBACK.txt\n'
        + "    sed 's/^[* |]*//' /tmp/_trss_v1.txt | grep '^MODE=' | tail -1 > /tmp/三总六科-MODE.txt\n"
        + "    sed 's/^[* |]*//' /tmp/_trss_v1.txt | grep '^TYPE=' | tail -1 > /tmp/三总六科-TYPE.txt\n"
        + '    echo rework > /tmp/三总六科-REWORK-TYPE.txt\n'
        + '    echo rework > /tmp/三总六科-REWORK.txt\n'
        + '    VERDICT_RESULT=rework\n'
        + '    echo "[TRSS] 🔄 二审判定需重做" && [ -n "${TRSS_NOTIFY_CMD:-}" ] && eval "${TRSS_NOTIFY_CMD}" "🔄 二审判定需重做" 2>/dev/null; true\n'
        + '  fi\n'
        + 'fi\n'
        + 'if [ "$VERDICT_RESULT" = "pass" ] && [ -n "$RUN_DIR" ]; then\n'
        + '  infile="$RUN_DIR/artifacts/审计总/output.txt"\n'
        + '  if [ -f "$infile" ]; then\n'
        + '    V3=$(sed "s/^[* |]*//" "$infile" | grep "^VERDICT=" | tail -1 | cut -d= -f2)\n'
        + '    if echo "$V3" | grep -Eqi "rework"; then\n'
        + '      FEEDBACK=$(sed "s/^[* |]*//" "$infile" | grep "^FEEDBACK=" | tail -1 | cut -d= -f2-)\n'
        + '      REWORK_TYPE=$(sed "s/^[* |]*//" "$infile" | grep "^REWORK_TYPE=" | tail -1 | cut -d= -f2 | tr -d " ")\n'
        + '      echo "$FEEDBACK" > /tmp/三总六科-FEEDBACK.txt\n'
        + '      if echo "$REWORK_TYPE" | grep -Eqi "^redesign"; then\n'
        + '        echo redesign > /tmp/三总六科-REWORK-TYPE.txt\n'
        + '        echo "[TRSS] 🔄 审计总判定需打回方案总重做" && [ -n "${TRSS_NOTIFY_CMD:-}" ] && eval "${TRSS_NOTIFY_CMD}" "🔄 审计总判定需打回方案总重做" 2>/dev/null; true\n'
        + '      else\n'
        + '        echo rework > /tmp/三总六科-REWORK-TYPE.txt\n'
        + "        sed 's/^[* |]*//' /tmp/_trss_v1.txt | grep '^MODE=' | tail -1 > /tmp/三总六科-MODE.txt 2>/dev/null; true\n"
        + "        sed 's/^[* |]*//' /tmp/_trss_v1.txt | grep '^TYPE=' | tail -1 > /tmp/三总六科-TYPE.txt 2>/dev/null; true\n"
        + '        echo "[TRSS] 🔄 审计总判定需修改" && [ -n "${TRSS_NOTIFY_CMD:-}" ] && eval "${TRSS_NOTIFY_CMD}" "🔄 审计总判定需修改" 2>/dev/null; true\n'
        + '      fi\n'
        + '      echo rework > /tmp/三总六科-REWORK.txt\n'
        + '      VERDICT_RESULT=rework\n'
        + '    fi\n'
        + '  fi\n'
        + 'fi\n'
        + 'if [ "$VERDICT_RESULT" = "rework" ]; then exit 0; fi\n'
        + notify_qq("🏁", "三总六科全流程完成")
    ))

# ════════════════════════════════════════════════
# ③ 图边 — 串行化执行顺序
# ════════════════════════════════════════════════
秘书处 >> 秘书处通知 >> 方案总 >> 方案总通知 >> 审核总 >> 审核总通知

# 六科并行派发（fan-out）
审核总通知 >> 内容科
审核总通知 >> 人事科
审核总通知 >> 情报科
审核总通知 >> 工程科
审核总通知 >> 数据科

# 六科汇聚到质控（fan-in）
内容科 >> 质控总
人事科 >> 质控总
情报科 >> 质控总
工程科 >> 质控总
数据科 >> 质控总

# 审核链
质控总 >> 质控检查 >> 审计总 >> 审计总通知 >> 督办处

print(g.to_json())
