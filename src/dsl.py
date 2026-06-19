"""
三总六科 DSL — 基于 AgentFlow 的编排构建块

六部 department agents + 门下省 JSON 路由表 + 情报科双线并行。

工具分工：
  方案总（出方案） → shell(reasonix run ...)
  内容科（报告）     → shell(reasonix run ...)
  数据科（数据）     → shell(reasonix run ...)
  研发科（代码）     → claude(read_write) — codex 不可用
  审计科（审计）     → claude(JSON 门禁, read_only)
  工程科（部署）     → reasonix
  人事科（权限）     → reasonix
  情报科（外网）   → reasonix --mcp mingyu（Exa 内置）
  情报科（知识库） → QMD 并行线

调用入口：agentflow run 三总六科.py
"""

from __future__ import annotations

import shlex

from pathlib import Path
from typing import Any

from agentflow import Graph as _AgentFlowGraph
from agentflow import claude, codex, fanout, shell, python_node
from agentflow.specs import ToolAccess

# 再也不需要自定义 adapter 了 —— reasonix/qmd 直接用 shell 原生跑


# ── 工具函数 ─────────────────────────────────────────────
def _reasonix_cmd(prompt: str, *, model: str | None = None, system: str | None = None) -> str:
    """构造 reasonix run 命令, shell-safe 引号处理。"""
    parts = ["reasonix", "run"]
    if model:
        parts.extend(["-m", model])
    else:
        parts.extend(["-m", "deepseek-v4-flash"])
    parts.extend(["--budget", "0.5"])
    if system:
        parts.extend(["-s", system])
    # 安全引用 prompt（防止含引号/换行的内容破坏 shell）
    parts.append(prompt)
    return shlex.join(parts)


def _qmd_cmd(prompt: str) -> str:
    """构造 qmd query 命令。"""
    return shlex.join(["qmd", "query", "--no-gpu", "--limit", "5", prompt[:200]])


# ── 三总六科专用 agent 构建器 ─────────────────────────────
def reasonix(task_id: str, prompt: str, *, model: str | None = None, system: str | None = None, **kwargs):
    """Reasonix 任务节点 — 走 shell() 原生调用，reasonix 自带 MCP/config。"""
    cmd = _reasonix_cmd(prompt, model=model, system=system)
    return shell(task_id=task_id, script=cmd, **kwargs)


def qmd(task_id: str, prompt: str, **kwargs):
    """QMD 知识库搜索节点 — 情报科专用，走 shell() 原生调用。"""
    cmd = _qmd_cmd(prompt)
    return shell(task_id=task_id, script=cmd, **kwargs)


# ── 秘书处：分拣路由 ───────────────────────────────────────
def 秘书处(graph: _AgentFlowGraph, task: str, **kwargs) -> dict:
    """秘书处分拣任务，返回路由决策。实际由调用方（助手）执行，不生成节点。"""
    return {
        "task": task,
        "departments": kwargs.get("departments", ["内容科"]),
        "needs_review": kwargs.get("needs_review", True),
        "needs_audit": kwargs.get("needs_audit", True),
    }


# ── 方案总：出方案 ─────────────────────────────────────────
def 方案总(
    graph: _AgentFlowGraph,
    task_id: str = "方案总",
    prompt: str = "",
    model: str | None = None,
    system: str | None = None,
    **kwargs,
):
    """方案总用 Reasonix 出方案（文档分析/规划）。"""
    return reasonix(
        task_id=task_id,
        prompt=prompt or "请为以下任务制定完整方案：",
        model=model,
        system=system,
        **kwargs,
    )


# ── 执行总：派发 ─────────────────────────────────────────
def 执行总(
    graph: _AgentFlowGraph,
    task_id: str = "执行总",
    departments: list | int | dict = 2,
    prompt: str = "",
    agent_fn=None,
    **kwargs,
):
    """执行总派发任务到六部（基于 fanout）。"""
    fn = agent_fn or (lambda: claude(task_id="六部", prompt=prompt, **kwargs))
    return fanout(fn, departments)


# ── 六部 department agents ──────────────────────────────
def 内容科(
    graph: _AgentFlowGraph,
    task_id: str = "内容科",
    prompt: str = "",
    model: str | None = None,
    system: str | None = None,
    **kwargs,
):
    """内容科 — 文档/报告写作（Reasonix via shell）"""
    return reasonix(
        task_id=task_id,
        prompt=prompt,
        model=model,
        system=system,
        **kwargs,
    )


def 数据科(
    graph: _AgentFlowGraph,
    task_id: str = "数据科",
    prompt: str = "",
    model: str | None = None,
    system: str | None = None,
    **kwargs,
):
    """数据科 — 数据/核算（Reasonix via shell）"""
    return reasonix(
        task_id=task_id,
        prompt=prompt,
        model=model,
        system=system,
        **kwargs,
    )


def 研发科(
    graph: _AgentFlowGraph,
    task_id: str = "研发科",
    prompt: str = "",
    model: str | None = None,
    **kwargs,
):
    """研发科 — 代码开发（Codex, read_write）"""
    return codex(
        task_id=task_id,
        prompt=prompt,
        model=model,
        tools=ToolAccess.READ_WRITE,
        **kwargs,
    )


def 审计科(
    graph: _AgentFlowGraph,
    task_id: str = "审计科",
    prompt: str = "",
    model: str | None = None,
    **kwargs,
):
    """审计科 — 安全/合规/审计，输出 JSON 供 success_criteria 解析"""
    return claude(
        task_id=task_id,
        prompt=
        "审计以下内容。必须以 JSON 格式输出结论：\n"
        '{"结论": "通过"|"驳回"|"需修改", "强制修正": N, "致命": true|false, "明细": [...]}\n\n'
        + prompt,
        model=model,
        tools=ToolAccess.READ_ONLY,
        success_criteria=[
            {
                "kind": "output_contains",
                "value": '"结论": "通过"',
            },
        ],
        **kwargs,
    )


def 工程科(
    graph: _AgentFlowGraph,
    task_id: str = "工程科",
    prompt: str = "",
    model: str | None = None,
    **kwargs,
):
    """工程科 — 工具链/部署（Reasonix，非 shell，需要理解自然语言）"""
    return reasonix(
        task_id=task_id,
        prompt=prompt,
        model=model,
        **kwargs,
    )


def 人事科(
    graph: _AgentFlowGraph,
    task_id: str = "人事科",
    prompt: str = "",
    model: str | None = None,
    **kwargs,
):
    """人事科 — 权限/技能管理（Reasonix，需要理解自然语言）"""
    return reasonix(
        task_id=task_id,
        prompt=prompt,
        model=model,
        **kwargs,
    )


def 情报科(
    graph: _AgentFlowGraph,
    task_id: str = "情报科",
    prompt: str = "",
    **kwargs,
):
    """情报科 — 知识库查询（QMD 向量搜索 via shell）"""
    return qmd(
        task_id=task_id,
        prompt=prompt,
        **kwargs,
    )


# ── 门下省：审核（success_criteria 自动门禁） ─────────────
def 门下省_通过(conclusion: str = '"结论": "通过"'):
    """门下省自动门禁 — success_criteria 模板"""
    return [{"kind": "output_contains", "value": conclusion}]


# ── 驳回循环构建器 ──────────────────────────────────────
def 驳回循环(write_node, review_node, max_iter: int = 3):
    """构建 内容科写 → 审计科审 → 驳回→重写 循环。
    
    用法:
        report = 内容科(...)
        audit = 审计科(...)
        report >> audit
        驳回循环(report, audit)
    """
    review_node.on_failure >> write_node


# ── 六部并行构建器 ──────────────────────────────────────
def 六部并行(graph, departments: list, prompt_fn=None):
    """并行派发到多个部门。
    
    用法:
        六部 = 六部并行(g, ["内容科", "数据科", "审计科"])
    """
    tasks = []
    for dept in departments:
        task_id = dept
        prompt = prompt_fn(dept) if prompt_fn else f"{dept} 执行"
        tasks.append({"department": dept, "task_id": task_id, "prompt": prompt})
    return tasks


# ── 三总六科完整 Graph 构建器 ─────────────────────────────
class sansheng_graph:
    """三总六科 Graph 上下文管理器。
    
    用法:
        with sansheng_graph("周复盘") as g:
            方案 = 方案总(g, prompt="出方案")
            报告 = 内容科(g, prompt="写报告")
            审计 = 审计科(g, prompt="审计")
            方案 >> 报告 >> 审计
            驳回循环(报告, 审计)
    """

    def __init__(
        self,
        name: str,
        *,
        description: str | None = None,
        concurrency: int = 4,
        max_iterations: int = 5,
        **kwargs,
    ):
        self._graph = _AgentFlowGraph(
            name=name,
            description=description,
            concurrency=concurrency,
            max_iterations=max_iterations,
            **kwargs,
        )

    def __enter__(self):
        return self._graph.__enter__()

    def __exit__(self, *args):
        return self._graph.__exit__(*args)

    @property
    def graph(self):
        return self._graph
