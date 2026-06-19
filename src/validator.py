"""三总六科 · 审计总审计 — 通用校验工具

与 dsl.py 审计总节点的 success_criteria JSON 门禁同逻辑。
"""

import json, re
from typing import Any


# ── 核心理念校验 ─────────────────────────────────
def validate_concept(text: str, max_chars: int = 20) -> dict:
    """校验是否 ≤max_chars 且含三总六科关键要素。"""
    n = len(text)
    return {
        "text": text,
        "char_count": n,
        "within_limit": n <= max_chars,
        "has_三省": "三省" in text or "中书" in text,
        "has_六部": "六部" in text or "吏户礼兵刑工" in text,
    }


# ── JSON 门禁格式校验 ────────────────────────────
class AuditError(Exception):
    """审计总审计异常"""


def audit_json_output(text: str) -> dict:
    """解析并校验审计总输出的 JSON 格式。"""
    # 提取 JSON 块
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise AuditError("未找到 JSON 输出")
    try:
        data = json.loads(match.group())
    except json.JSONDecodeError as e:
        raise AuditError(f"JSON 解析失败: {e}")

    required = {"结论", "致命", "明细"}
    missing = required - set(data.keys())
    if missing:
        raise AuditError(f"缺少必填字段: {missing}")

    if data.get("结论") not in ("通过", "驳回", "需修改"):
        raise AuditError(f"无效结论值: {data.get('结论')}")

    return data


# ── 三总六科路由决策校验 ─────────────────────────
VALID_DEPARTMENTS = {"人事科", "数据科", "内容科", "研发科", "审计总", "工程科"}


def validate_routing(route: dict) -> tuple[bool, str]:
    """校验秘书处分拣路由是否合法。"""
    depts = route.get("departments", [])
    if not isinstance(depts, list):
        return False, "departments 必须是列表"
    for d in depts:
        if d not in VALID_DEPARTMENTS:
            return False, f"未知部门: {d}"
    return True, "路由合法"


# ── Graph JSON 结构校验 ──────────────────────────
def validate_graph_json(graph_json: str) -> list[str]:
    """校验 Graph JSON 的基本结构完整性。返回问题列表，空=全部通过。"""
    import json as _json
    issues: list[str] = []
    try:
        g = _json.loads(graph_json) if isinstance(graph_json, str) else graph_json
    except _json.JSONDecodeError as e:
        return [f"JSON 格式错误: {e}"]

    nodes = g.get("nodes", [])
    node_ids = {n["id"] for n in nodes}
    for n in nodes:
        if "agent" not in n:
            issues.append(f"节点 {n.get('id')} 缺少 agent 声明")
        for dep in n.get("depends_on", []):
            if dep not in node_ids:
                issues.append(f"节点 {n['id']} 依赖 {dep} 但不存在")

    return issues
