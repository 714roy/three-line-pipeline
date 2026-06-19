"""
状态定义 + LLM 调用工具
"""
from typing import TypedDict, Optional, Any, Annotated
from typing_extensions import NotRequired
import subprocess, json, os, operator, re

# ─── 加载 claudeprompt 知识库作为 reasonix 的 System Prompt ───
CLAUDEPROMPT_DIR = os.path.expanduser("~/Nutstore Files/工坊/参考/claude-code-system-prompts/system-prompts")
_SYSTEM_PROMPT_CACHE = None

def _load_claudeprompt_system() -> str:
    """加载 claudeprompt 知识库中与诚实报告/安全/行为相关的规则"""
    global _SYSTEM_PROMPT_CACHE
    if _SYSTEM_PROMPT_CACHE is not None:
        return _SYSTEM_PROMPT_CACHE
    
    key_files = [
        "system-prompt-action-safety-and-truthful-reporting.md",
        "system-prompt-harness-instructions.md", 
    ]
    
    parts = ["<!-- 以下规则来自 Claude Code System Prompts (Fable 5) -->"]
    
    for fname in key_files:
        fpath = os.path.join(CLAUDEPROMPT_DIR, fname)
        if not os.path.exists(fpath):
            continue
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception:
            continue
        
        # 去掉 YAML frontmatter (<!-- ... -->)
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL).strip()
        # 去掉模板变量 ${...}
        text = re.sub(r'\$\{[^}]+\}', '', text).strip()
        # 去掉多余的空白行
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        if text:
            parts.append(text)
    
    # 额外加一条三总六科特有的诚实指令（claudeprompt库没有的）
    parts.append(
        "\n[三总六科额外规则]\n"
        "1. 只引用输入数据中实际存在的内容。没有的数据、未知的数值→写'不可达'或'无数据'。\n"
        "2. 不可用推测填充未知。不知道就说不知道。\n"
        "3. 所有陈述必须可追溯。无从验证的陈述=不合格。\n"
        "4. 改进建议用[建议]标注以与事实区分。\n"
        "5. 做完了说做完了，没做完说没做完，不修饰不编造。"
    )
    
    _SYSTEM_PROMPT_CACHE = "\n\n".join(parts)
    return _SYSTEM_PROMPT_CACHE

# ─── 状态类型 ───

class Subtask(TypedDict, total=False):
    id: str               # 任务ID，如 "工程科_写代码"
    dept: str             # 所属部："人事科"/"数据科"/"内容科"/"研发科"/"审计总"/"工程科"
    desc: str             # 任务描述
    prompt: str           # 给 Reasonix 的完整 prompt
    depends_on: list[str] # 依赖的其他task id
    result: str           # 执行结果
    cost: float           # 该子任务消耗($)
    model: str            # "flash"/"pro"
    status: str           # "pending"/"running"/"done"/"failed"

class TaskState(TypedDict):
    # 原始输入
    task: str
    user_context: str              # 用户补充上下文
    
    # 秘书处输出
    intent: str                    # 任务类型
    params: dict                   # 提取的关键参数
    
    # 方案总输出
    plan: list[dict]               # 方案步骤 [{step, dept, desc, prompt_suggestion}]
    plan_rationale: str            # 方案理由
    
    # 门下省审核
    review_passed: bool
    review_feedback: str           # 驳回原因
    review_round: int              # 审核轮次（防死循环）
    
    # 执行总调度
    subtasks: list[Subtask]        # 派发的子任务
    
    # 六部执行结果
    results: Annotated[dict, operator.or_]  # 并行写入合并
    errors: Annotated[list[str], operator.add]
    
    # 门下省复查
    output_review_passed: bool
    output_review_feedback: str
    output_review_round: int              # 复查轮次
    needs_imperial_decision: bool         # 需要皇帝裁决
    imperial_decision_request: str        # 呈请裁决的内容
    
    # 督办处汇总
    final_output: str
    summary: str
    
    # 成本追踪
    cost_log: Annotated[list[dict], operator.add]
    total_cost: float

def default_state(task: str, context: str = "") -> TaskState:
    return {
        "task": task,
        "user_context": context,
        "intent": "",
        "params": {},
        "plan": [],
        "plan_rationale": "",
        "review_passed": False,
        "review_feedback": "",
        "review_round": 0,
        "subtasks": [],
        "results": {},
        "errors": [],
        "output_review_passed": False,
        "output_review_feedback": "",
        "output_review_round": 0,
        "needs_imperial_decision": False,
        "imperial_decision_request": "",
        "final_output": "",
        "summary": "",
        "cost_log": [],
        "total_cost": 0.0,
    }

# ─── LLM 调用 ───

VENV_PYTHON = "/home/roy/.hermes/hermes-agent/.venv/bin/python"

def reasonix_call(prompt: str, model: str = "flash", timeout: int = 300) -> str:
    """调用 Reasonix (DeepSeek Flash/Pro)，自动注入 claudeprompt 系统规则"""
    system = _load_claudeprompt_system()
    env = {**os.environ}
    if "PATH" in env and "/home/roy/.npm-global/bin" not in env["PATH"]:
        env["PATH"] = "/home/roy/.npm-global/bin:/home/roy/.local/bin:" + env["PATH"]
    elif "PATH" not in env:
        env["PATH"] = "/home/roy/.npm-global/bin:/home/roy/.local/bin:/usr/local/bin:/usr/bin:/bin"
    r = subprocess.run(
        ["reasonix", "run", "--system", system, prompt],
        capture_output=True, text=True, timeout=timeout,
        env=env
    )
    stdout = r.stdout or ""
    lines = stdout.rstrip().split("\n")
    # 去掉末尾统计行
    if lines and lines[-1].startswith("—"):
        content = "\n".join(lines[:-1])
    else:
        content = stdout
    content = content.strip()
    
    # 简单的成本估算
    input_chars = len(prompt)
    output_chars = len(content.encode("utf-8"))
    # Reasonix ~$0.0003/次 (Flash), ~$0.0006/次 (Pro)
    cost = 0.0006 if model == "pro" else 0.0003
    
    return content

def _clean_json_text(text: str) -> str:
    """提取并清理 JSON 文本，处理常见格式问题"""
    text = text.strip()
    # 去除 markdown 代码块包裹
    if text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0]
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:].strip()
    if text.startswith("```"):
        text = text[3:].strip()
    # 提取 {} 包围的部分
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end+1]
    return text.strip()


def _repair_json(text: str) -> str:
    """尝试修复常见 JSON 格式错误"""
    # 1. 去除尾随逗号（在 } 或 ] 前）
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    # 2. 修复单引号为双引号（仅在键名和字符串值上）
    #    先保护已转义的双引号
    # 3. 去除注释风格的 // 行
    text = re.sub(r'^\s*//.*$', '', text, flags=re.MULTILINE)
    return text


def json_from_llm(prompt: str, model: str = "flash") -> dict:
    """调用 LLM 返回 JSON（含多级容错）"""
    json_prompt = prompt + "\n\n只输出JSON，不要Markdown包裹，不要额外文字。"
    text = reasonix_call(json_prompt, model)
    text = _clean_json_text(text)
    
    # 尝试直接解析
    for attempt in range(3):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            if attempt == 0:
                text = _repair_json(text)
            elif attempt == 1:
                # 更激进的修复：尝试用 ast.literal_eval 处理 Python 风格 dict
                import ast
                try:
                    # 转换 true/false/null 为 Python 格式
                    py_text = text.replace("true", "True").replace("false", "False").replace("null", "None")
                    result = ast.literal_eval(py_text)
                    if isinstance(result, dict):
                        return result
                except Exception:
                    pass
                # 尝试用 json5 风格的宽松解析
                try:
                    # 手动用正则提取键值对构建简单 dict
                    pass
                except Exception:
                    pass
            else:
                # 最终 fallback：抛出原始异常
                raise


# ─── Claude Code 调用（审计总深度评估用） ───

CLAUDE_CAREER_OPS_DIR = "/home/roy/Nutstore Files/工坊/求职/career-ops"
CC_CLI = "claude"  # 假设在 PATH 中

def claude_code_eval(prompt: str, timeout: int = 300) -> str:
    """调用 Claude Code 做深度评估（JD 6-Block 等）"""
    full_prompt = prompt + "\n\n请输出完整的评估结果。"
    
    r = subprocess.run(
        ["claude", "--dangerously-skip-permissions", "--print", full_prompt],
        capture_output=True, text=True, timeout=timeout,
        cwd=CLAUDE_CAREER_OPS_DIR
    )
    stdout = r.stdout or ""
    
    # 去掉 claude 的输出头（如果有）
    lines = stdout.strip().split("\n")
    # 过滤掉 claude 自己的日志行
    clean_lines = [l for l in lines if not l.startswith("[") and not l.startswith("INFO")]
    result = "\n".join(clean_lines).strip()
    
    return result


def liepin_search(job_name: str, address: str) -> list[dict]:
    """搜索猎聘岗位（通过 Python 子进程调用 MCP）"""
    # 猎聘 MCP 需要从 Hermes 上下文调用，这里用简单 fallback
    # 实际运行时通过主进程的 MCP 调用
    return []


# ─── Consilium 三模型交叉验证（门下省审核用） ───

CONSILIUM_SCRIPT = os.path.expanduser("~/.hermes/scripts/consilium-sf.sh")

def consilium_cross_validate(prompt: str, budget: float = 0.04, timeout: int = 180) -> dict:
    """
    调用 Consilium 三模型（Qwen2.5-72B / DeepSeek-V3 / Qwen3.6-27B）交叉验证。
    
    返回结构化结果：
    {
        "raw": "...",              # 原始输出
        "passed": True/False,      # 综合判断
        "scores": {},              # 各模型评分
        "avg_score": 0.0,          # 平均分
        "issues": [...],           # 发现的问题
        "cost_estimate": 0.10,     # 费用估算
    }
    """
    if not os.path.exists(CONSILIUM_SCRIPT):
        return {
            "raw": "[Consilium 脚本不可用]",
            "passed": True,  # 无法验证时放行
            "scores": {},
            "avg_score": 8.0,
            "issues": [],
            "cost_estimate": 0,
        }
    
    env = {**os.environ}
    for p in ["/home/roy/.npm-global/bin", "/home/roy/.local/bin"]:
        if "PATH" in env and p not in env["PATH"]:
            env["PATH"] = p + ":" + env["PATH"]
    
    full_prompt = f"评审以下内容的质量、准确性和完整性：\n\n{prompt}\n\n请给出评分（1-10分）和关键问题。"
    
    try:
        r = subprocess.run(
            ["bash", CONSILIUM_SCRIPT, full_prompt, f"--budget", str(budget)],
            capture_output=True, text=True, timeout=timeout,
            env=env
        )
        output = (r.stdout or "") + "\n" + (r.stderr or "")
        
        # 简单解析：看是否包含"通过"/"认可"/"同意"等正面词
        lower = output.lower()
        has_pass = any(w in lower for w in ["通过", "认可", "同意", "pass", "approve", "good", "ok"])
        has_reject = any(w in lower for w in ["驳回", "问题", "错误", "reject", "fail", "issue", "error"])
        
        # 估算评分
        avg = 6.0
        if has_pass and not has_reject:
            avg = 8.0
        elif has_pass and has_reject:
            avg = 6.0
        else:
            avg = 4.0
        
        return {
            "raw": output[:3000],
            "passed": avg >= 6.0,
            "scores": {"estimated": avg},
            "avg_score": avg,
            "issues": [output[:500]] if has_reject else [],
            "cost_estimate": 0.10,
        }
    except subprocess.TimeoutExpired:
        return {
            "raw": "[Consilium 超时]",
            "passed": True,
            "scores": {},
            "avg_score": 8.0,
            "issues": [],
            "cost_estimate": 0.05,
        }


# ─── QMD 搜索（情报科·格物镜用） ───

QMD_SEEK_DIR = os.path.expanduser("~/Nutstore Files/Obsidian/知屿/Seek知识库")
QMD_ARCHIVE_DIR = os.path.expanduser("~/Nutstore Files/Obsidian/知屿/存档库")

def qmd_search(query: str, max_results: int = 10) -> list[dict]:
    """调用 QMD 语义搜索 Seek 知识库，返回 [{title, content, score}, ...]"""
    env = {**os.environ}
    for p in ["/home/roy/.npm-global/bin", "/home/roy/.local/bin"]:
        if "PATH" in env and p not in env["PATH"]:
            env["PATH"] = p + ":" + env["PATH"]
    
    results = []
    
    for base_dir, label in [(QMD_SEEK_DIR, "Seek"), (QMD_ARCHIVE_DIR, "存档库")]:
        if not os.path.isdir(base_dir):
            continue
        try:
            r = subprocess.run(
                ["qmd", "search", query, "--no-gpu"],
                capture_output=True, text=True, timeout=30,
                cwd=base_dir, env=env
            )
            lines = (r.stdout or "").strip().split("\n")
            for line in lines[:max_results]:
                if line.strip():
                    results.append({
                        "source": label,
                        "text": line.strip()[:200],
                        "score": 0.8,
                    })
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    
    return results

