"""
三总六科 核心理念 — 研发科奉令开发

方案总方案：
  三省分权制衡 → 决策(中书) / 审议(门下) / 执行(尚书) 三权分立
  六部各司其职 → 吏户礼兵刑工 各司其职

定稿：「三省分权制衡，六部各司其职」(12字 ≤ 20 ✓)

内容科考据推敲后的凝练版：「分权制衡，协同理政」(8字)
  更聚焦治理哲学而非机构名，适合正式场合使用。
"""

# ── 原始定稿（结构描述） ──
KERNEL = "三省分权制衡，六部各司其职"

# ── 内容科考据后凝练版（治理哲学） ──
REFINED = "分权制衡，协同理政"

# ── 完整四步考据结论 ──
REFERENCE_PLAN = {
    "steps": [
        {"step": 1, "action": "查阅典籍，确认三总六科制度起源与演变", "department": "内容科",
         "description": "调取《唐六典》《隋书·百官志》，梳理三省（中书、门下、尚书）与六部的职权边界"},
        {"step": 2, "action": "撰写核心摘要，提炼不超过20字", "department": "人事科",
         "description": "基于内容科呈报的文献综述，由考功司主笔提炼核心理念，要求精炼、无歧义"},
        {"step": 3, "action": "复核摘要是否准确反映分权制衡思想", "department": "情报科",
         "description": "以星象推演之法校验摘要与历史实际的吻合度，防止过度简化"},
        {"step": 4, "action": "工程科雕版，数据科刊印，颁行天下", "department": "工程科",
         "description": "将最终定稿的8字摘要「分权制衡，协同理政」刻印成册，由数据科调配纸张，内容科主持发布"},
    ],
    "philosophy": {
        "分权": "中书决策 → 门下审核 → 尚书执行，三权分立",
        "制衡": "门下省可驳中书之旨，执行总按六部分工落实",
        "协同": "六部（吏户礼兵刑工）各司其职，又相互配合",
        "理政": "最终目标：高效治理天下政务",
    },
}

# ── 三省映射 ──
THREE_DEPARTMENTS = {
    "方案总": "决策起草 — Reasonix 出方案",
    "门下省": "审议封驳 — success_criteria JSON 门禁",
    "执行总": "执行派发 — fanout 到六部",
}

# ── 六部映射 ──
SIX_MINISTRIES = {
    "人事科": "权限/技能管理 — shell",
    "数据科": "数据/核算 — Reasonix",
    "内容科": "文档/报告 — Reasonix",
    "研发科": "代码开发 — Codex (read_write)",
    "审计总": "审计/合规 — Claude JSON 门禁 (read_only)",
    "工程科": "工具链/部署 — shell",
}

# 情报科（知识库）为独立机构
OBSERVATORY = "情报科: 知识库检索 — QMD 向量查询 (shell)"



def validate(text: str = KERNEL, max_chars: int = 20) -> dict:
    """验证凝练结果是否满足字数约束。"""
    n = len(text)
    return {
        "text": text,
        "char_count": n,
        "within_limit": n <= max_chars,
        "limit": max_chars,
    }


def summary(verbose: bool = False) -> str:
    """返回核心理念一句话。verbose 时附带展开说明。"""
    if not verbose:
        return KERNEL
    return (
        f"{KERNEL}\n\n"
        f"凝练版：{REFINED}\n\n"
        f"三省：{', '.join(f'{k}={v}' for k, v in THREE_DEPARTMENTS.items())}\n"
        f"六部：{', '.join(f'{k}={v}' for k, v in SIX_MINISTRIES.items())}\n"
        f"独立：{OBSERVATORY}"
    )
