# TRSS — 三总六科 / Three-Review Six-Section

> **分权制衡的 Agent 编排管线**：秘书处 → 方案总 → 审核总 → 六科并行 → 质控总 → 审计总 → 督办处
>
> **Agent orchestration with separation of powers**: Secretariat → Planning → Review → Parallel Execution → Quality Check → Audit → Oversight.

TRSS 是对古代**三省六部**治理模型的现代化改造，用企业组织架构的词汇（总、科、秘书处、督办处）重新实现了分权制衡、逐级审核、并行执行、独立审计的核心设计。所有配置通过环境变量完成。

TRSS is an **agent orchestration pipeline** that implements the ancient **三省六部** governance model in modern corporate vocabulary. It routes tasks through a structured review chain with parallel department execution, rework loops, and independent audit.

---

## 架构 / Architecture

```text
                     ┌──────────────────────┐
                     │    秘书处             │  ← 任务分拣：direct / pipeline？
                     │    Secretariat        │
                     └──────────┬───────────┘
                                │ (pipeline 路线)
                     ┌──────────▼───────────┐
                     │    方案总             │  ← 拆解任务，推荐模式
                     │    Planning Director  │
                     └──────────┬───────────┘
                     ┌──────────▼───────────┐
                     │    审核总             │  ← 批准或打回重拆
                     │    Review Director    │
                     └──────────┬───────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                  │
     ┌────────▼───┐   ┌────────▼───┐    ┌────────▼───┐
     │ 内容科     │   │ 研发科     │    │ 情报科     │  ← 六科按模式并行执行
     │ Content    │   │ R&D        │    │ Intelligence│
     ├────────────┤   ├────────────┤    ├────────────┤
     │ 工程科     │   │ 数据科     │    │ 人事科     │
     │ Engineering│   │ Data       │    │ HR         │
     └────────────┘   └────────────┘    └────────────┘
              │                 │                  │
              └─────────────────┼──────────────────┘
                     ┌──────────▼───────────┐
                     │    质控总             │  ← 审核产出、命名归档路径
                     │    Quality Director   │
                     └──────────┬───────────┘
                     ┌──────────▼───────────┐
                     │    审计总             │  ← 最终签批或打回重做
                     │    Audit Director     │
                     └──────────┬───────────┘
                     ┌──────────▼───────────┐
                     │    督办处             │  ← 归档、通知、判 verdict
                     │    Oversight Office   │
                     └──────────────────────┘
```

### 四种模式 / Four Modes

| 模式 | 参与部门 | 适用场景 |
|:-----|:---------|:---------|
| `research` | 内容科 + 情报科 + 工程科 | 市场调研、资料搜集 |
| `build` | 工程科 + 数据科 | 方案设计、代码项目 |
| `debate` | 内容科 + 人事科 + 情报科 | 决策评估、争议分析 |
| `full` | 全部六科 | 复杂综合任务 |

### 两条路线 / Two Routes

| 路线 | 含义 | 成本 | 耗时 |
|:-----|:------|:-----|:-----|
| `direct` | 秘书处直接回答 | ~$0.001 | ~10s |
| `pipeline` | 完整审核链 | ~$0.01-0.02 | ~3-10min |

### 重做循环 / Rework Loop

任一审核节点（审核总/质控总/审计总）驳回产出 → 进入重做循环（带反馈注入）。连续 2 轮驳回 → 降级为推翻重做。同一问题驳回 3 次 → 标记死胡同，建议人工介入。

---

## 快速开始 / Quick Start

### 安装 / Install

```bash
git clone https://github.com/reoroy/three-line-pipeline.git
cd three-line-pipeline

cp src/entry.sh /usr/local/bin/trss
chmod +x /usr/local/bin/trss
pip install -e .

mkdir -p /tmp/trss
cp src/pipeline.py /tmp/trss/
cp src/dsl.py /tmp/trss/
```

### 运行 / Run

```bash
# 快速回答
trss "上海今天天气怎么样？"

# 完整流水线
trss "调研 AI Agent 编排框架市场，写一份竞争分析报告"
```

### 前置依赖 / Prerequisites

- Python 3.10+
- [AgentFlow](https://github.com/noahyamamoto/AgentFlow) — 管线引擎
- [reasonix](https://github.com/AnastasiyaW/reasonix) — LLM 运行器（可配置为其他 CLI）
- Claude Code（可选）— 代码开发与审计任务

### 配置 / Configuration

| 环境变量 | 默认值 | 说明 |
|:---------|:-------|:------|
| `TRSS_PIPELINE_DIR` | `/tmp/trss` | pipeline 定义目录 |
| `TRSS_OUTPUT_DIR` | `/tmp/trss/output` | 产出归档目录 |
| `TRSS_NOTIFY_CMD` | (无) | 通知命令（如 `hermes send`） |
| `TRSS_LLM_CMD` | `reasonix` | LLM 运行器命令 |
| `TRSS_LLM_MODEL` | `deepseek-v4-flash` | 默认模型 |

---

## 项目结构 / Project Structure

```text
three-line-pipeline/
├── src/
│   ├── entry.sh         # 入口脚本（bash，含 rework 循环）
│   ├── pipeline.py      # AgentFlow 主图（623 行，16 节点）
│   ├── dsl.py           # DSL 代理构建器
│   ├── core.py          # 核心理念定义
│   ├── validator.py     # 输出校验器
│   └── prompts/         # 提示词模板
├── langgraph/           # LangGraph 替代实现
├── docs/
│   ├── architecture.md  # 架构设计 [中文]
│   ├── naming-mapping.md # 三省六部→三总六科映射
│   └── pitfalls.md      # 实战陷阱 [中文]
├── CREDITS.md           # 思想来源与开源依赖
└── LICENSE              # MIT
```

---

## 命名演化 / Evolution

1. **三省六部** — 唐代治理模型原始概念
2. **TLP** (Three-Line Pipeline) — 内部开发阶段
3. **TRSS / 三总六科** — 公开版现代化改造

详见 `docs/naming-mapping.md`。

---

## 许可 / License

MIT — see [LICENSE](LICENSE).

## 致谢 / Credits

See [CREDITS.md](CREDITS.md) for intellectual origins and open-source dependencies.
