# TRSS — Three-Review Six-Section / 三总六科

> **Agent orchestration with separation of powers**: Secretariat → Planning → Review → Parallel Execution → Quality Check → Audit → Oversight.

TRSS is an **agent orchestration pipeline** that implements the ancient **三省六部** governance model in modern corporate vocabulary. It routes tasks through a structured review chain with parallel department execution, rework loops, and independent audit — all configurable via environment variables.

---

## Architecture

```text
                     ┌──────────────────────┐
                     │    Secretariat        │  ← Task triage: direct or pipeline?
                     │    (秘书处)            │
                     └──────────┬───────────┘
                                │ (pipeline route)
                     ┌──────────▼───────────┐
                     │    Planning Director  │  ← Break down task, recommend mode
                     │    (方案总)            │
                     └──────────┬───────────┘
                     ┌──────────▼───────────┐
                     │    Review Director    │  ← Approve or redesign the plan
                     │    (审核总)            │
                     └──────────┬───────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                  │
     ┌────────▼───┐   ┌────────▼───┐    ┌────────▼───┐
     │ Content    │   │  R&D       │    │ Intelligence│  ← Six sections execute in
     │ (内容科)    │   │  (研发科)   │    │ (情报科)    │     parallel based on mode
     ├────────────┤   ├────────────┤    ├────────────┤
     │ Engineering│   │  Data      │    │  HR        │
     │ (工程科)    │   │  (数据科)   │    │ (人事科)    │
     └────────────┘   └────────────┘    └────────────┘
              │                 │                  │
              └─────────────────┼──────────────────┘
                     ┌──────────▼───────────┐
                     │   Quality Director   │  ← Review output, name & route artifacts
                     │   (质控总)            │
                     └──────────┬───────────┘
                     ┌──────────▼───────────┐
                     │   Audit Director     │  ← Final sign-off or rework
                     │   (审计总)            │
                     └──────────┬───────────┘
                     ┌──────────▼───────────┐
                     │   Oversight Office    │  ← Archive, notify, check verdicts
                     │   (督办处)            │
                     └──────────────────────┘
```

### Four Modes

| Mode | Participating Sections | Best For |
|:-----|:-----------------------|:---------|
| `research` | Content + Intelligence + Engineering | Market research, data gathering |
| `build` | Engineering + Data | Solution design, coding projects |
| `debate` | Content + HR + Intelligence | Decision evaluation, comparative analysis |
| `full` | All six sections | Complex multi-faceted tasks |

### Two Routes

| Route | Meaning | Cost | Latency |
|:------|:--------|:-----|:--------|
| `direct` | Secretariat answers directly | ~$0.001 | ~10s |
| `pipeline` | Full review chain | ~$0.01-0.02 | ~3-10min |

### Rework Loop

If any review body (Review Director / Quality Director / Audit Director) rejects the output, the pipeline enters a rework loop with feedback injection. After 2 consecutive rejections, it downgrades to a full redesign.

---

## Quick Start

### Prerequisites

- Python 3.10+
- [AgentFlow](https://github.com/noahyamamoto/AgentFlow) — pipeline engine
- [reasonix](https://github.com/AnastasiyaW/reasonix) — LLM runner (or configure your own)
- Claude Code (optional) — for code development and audit tasks

### Install

```bash
# Clone
git clone https://github.com/714roy/three-line-pipeline.git
cd three-line-pipeline

# Set up
cp src/entry.sh /usr/local/bin/trss
chmod +x /usr/local/bin/trss
pip install -e .

# Deploy pipeline
mkdir -p /tmp/trss
cp src/pipeline.py /tmp/trss/
cp src/dsl.py /tmp/trss/
```

### Run

```bash
# Direct answer
trss "What's the weather in Shanghai?"

# Full pipeline
trss "Research the AI agent market and write a competitive analysis report"
```

### Configuration

| Env Var | Default | Description |
|:--------|:--------|:------------|
| `TRSS_PIPELINE_DIR` | `/tmp/trss` | Pipeline definition location |
| `TRSS_OUTPUT_DIR` | `/tmp/trss/output` | Output archive base |
| `TRSS_NOTIFY_CMD` | (none) | Command to run for notifications |
| `TRSS_LLM_CMD` | `reasonix` | LLM runner command |
| `TRSS_LLM_MODEL` | `deepseek-v4-flash` | Default LLM model |

---

## Project Structure

```text
three-line-pipeline/
├── src/
│   ├── entry.sh         # Entry script (bash, with rework loop)
│   ├── pipeline.py      # AgentFlow pipeline (624 lines, 16 nodes)
│   ├── dsl.py           # DSL library with agent builders
│   ├── core.py          # Core concepts and philosophy
│   ├── validator.py     # Output validators
│   └── prompts/         # Prompt templates
├── langgraph/           # Alternative LangGraph implementation
├── docs/
│   ├── architecture.md
│   ├── naming-mapping.md   # 三省六部 → 三总六科 evolution
│   └── pitfalls.md
├── CREDITS.md           # Intellectual origins & open-source deps
└── LICENSE              # MIT
```

---

## Evolution

This project has gone through three naming phases:

1. **三省六部** (Three Departments Six Ministries) — original concept based on Tang dynasty governance
2. **TLP** (Three-Line Pipeline) — renamed from a risk-management framework
3. **TRSS / 三总六科** — modern corporate restructure for public release

See `docs/naming-mapping.md` for the full mapping.

---

## License

MIT — see [LICENSE](LICENSE).

## Credits

See [CREDITS.md](CREDITS.md) for intellectual origins and open-source dependencies.
