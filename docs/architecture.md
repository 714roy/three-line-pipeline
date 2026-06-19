# Architecture

## Design Philosophy

TRSS is not a code framework — it is an **organizational institution** for AI agents. The core idea comes from the Tang dynasty's 三省六部 (Three Departments, Six Ministries) governance model, restructured here with modern corporate vocabulary.

### Three Core Principles

**1. Separation of Powers**
Planning (方案总), Review (审核总/质控总), and Audit (审计总) are independent bodies. No single agent both produces and approves work — this prevents self-confirmation bias.

**2. Sequential Review, Parallel Execution**
The review chain is strictly serial (each gate sees the full output of the previous gate), but executing departments run in parallel. This mirrors the original 三省六部 design where 门下省 reviews independently of the producing departments.

**3. Feedback Loops with Escalation**
Rejected work goes back to the originating department with structured feedback. After 2 consecutive rejections, the pipeline signals a full redesign. After 3 rejections on the same issue, it flags a dead end for human intervention.

---

## Node Architecture

### The Pipeline (AgentFlow Version)

TRSS defines 16 nodes in a directed graph:

```text
Secretariat → Secretariat Notification
    → Planning Director → Planning Notification
        → Review Director → Review Notification
            → [Six Sections in parallel: Content, R&D, Intel, Engineering, Data, HR]
                → Quality Director → Quality Check
                    → Audit Director → Audit Notification
                        → Oversight Office
```

### Node Responsibilities

| Node | Type | Input | Output |
|:-----|:-----|:------|:-------|
| **Secretariat** (秘书处) | LLM/reasonix | Raw task | Three-mirror analysis + ROUTE/MODE decision |
| **Planning Director** (方案总) | LLM/reasonix | Task + mirror analysis | Decomposition into 3-5 sub-questions + MODE recommendation |
| **Review Director** (审核总) | LLM/reasonix | Plan | VERDICT (pass/redesign) + improved plan |
| **Content Section** (内容科) | LLM/reasonix | Reviewed plan | Research output, data gathering |
| **R&D Section** (研发科) | Codex/Claude | Reviewed plan | Code implementation |
| **Intelligence Section** (情报科) | LLM/reasonix | Reviewed plan | External knowledge verification |
| **Engineering Section** (工程科) | LLM/reasonix | Reviewed plan | Solution design, framework |
| **Data Section** (数据科) | LLM/reasonix | Reviewed plan | Feasibility assessment |
| **HR Section** (人事科) | LLM/reasonix | Reviewed plan | Key insight extraction |
| **Quality Director** (质控总) | LLM/reasonix | All department outputs | VERDICT + OUTPUT_NAME + ARCHIVE_PATH + route table JSON |
| **Audit Director** (审计总) | LLM/reasonix | All outputs + QC verdict | VERDICT (pass/rework) + improved final output |
| **Oversight Office** (督办处) | shell | All artifacts | Archive files, check verdicts, signal rework |

---

## Routing

### Two-Way Routing

On entry, the Secretariat decides between two paths:

| Route | Condition | Trigger | Cost |
|:------|:----------|:--------|:-----|
| **direct** | Single factual question, brief answer sufficient | `ROUTE=direct` | ~$0.001 |
| **pipeline** | Multi-dimensional, needs formal document | `ROUTE=pipeline` | ~$0.01-0.02 |

### Four Modes (pipeline)

| Mode | Sections | Best For |
|:-----|:---------|:---------|
| `research` | Content + Intel + Engineering | Market research, data gathering |
| `build` | Engineering + Data | Solution design, coding projects |
| `debate` | Content + HR + Intel | Decision evaluation, comparative analysis |
| `full` | All six | Complex multi-faceted tasks |

The mode is recommended by the Planning Director and confirmed by the Review Director. Departments not in the current mode skip automatically.

---

## Rework Loop

```text
                        ┌──────────────┐
                        │  Pipeline     │
                        │  Execution    │
                        └──────┬───────┘
                               │
                    ┌──────────▼──────────┐
                    │   Oversight Office   │
                    │   Check Verdicts     │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Any verdict =       │
                    │  rework/redesign?    │
                    └──────┬──────┬───────┘
                        No │     │ Yes
                           ▼     ▼
                      ┌──────┐ ┌──────────────────────┐
                      │Done │ │ Rework with feedback  │
                      └──────┘ │ Max 2 rounds         │
                               │ 3rd → human intervene│
                               └──────────────────────┘
```

Three verdict points:
1. **Review Director** — plan quality → redesign (back to Planning)
2. **Quality Director** — output quality → rework (back to departments)
3. **Audit Director** — final audit → rework or redesign

---

## Design Evolution

TRSS went through three architectural phases:

| Phase | Framework | Pattern | Status |
|:------|:----------|:--------|:-------|
| v1 | **LangGraph** | State-machine with Send/Command | Legacy (in `langgraph/`) |
| v2 | **AgentFlow** | Directed graph with fan-out/fan-in | Primary (in `src/`) |
| v3 | **Pi fork** (planned) | Extension-based, 4 native loops | Future |

### Key Design Decisions

**Why AgentFlow over LangGraph for production?**
AgentFlow's shell-based nodes are simpler to debug and iterate — each node produces a plain text file. LangGraph's Python state machine is more elegant but harder to modify at runtime.

**Why `ROUTE=direct` exists at all?**
Full pipeline costs ~$0.01-0.02 per run. For simple questions (weather, lookup, quick facts), this is wasteful. The Secretariat triage saves ~90% of tasks from unnecessary overhead.

**Why archive before verdict?**
Originally verdict was checked before archiving — if rework was signaled, output was discarded. The fix (archive-first) ensures no output is ever lost, even if the pipeline needs another round.

---

## Comparison: TRSS vs Modern Alternatives

| Aspect | TRSS | LangGraph Supervisor | CrewAI | AutoGen |
|:-------|:-----|:-------------------|:-------|:--------|
| Review chain | 3-layer (plan/quality/audit) | 1‑layer supervisor | None built-in | Optional critic |
| Parallel execution | 6-section fan-out | Manual | Via agents | Via agents |
| Rework loop | Built-in with feedback | Manual | None | None |
| Direct route | Built-in triage | N/A | N/A | N/A |
| Archive + naming | Integrated | Manual | Manual | Manual |
| MCP noise filter | Built-in | N/A | N/A | N/A |

TRSS is opinionated: it enforces a specific governance model. For teams that want a flexible toolkit, LangGraph or AutoGen are better. For teams that want a battle-tested review pipeline, TRSS provides guardrails out of the box.
