# CREDITS

## Intellectual Origin

### 三省六部 (Three Departments and Six Ministries)

The **TRSS (Three-Review Six-Section)** architecture is a **modern corporate restructuring** of the ancient Chinese **三省六部** governance system. The original concept — separation of powers, sequential review, parallel execution, and independent audit — dates back to the Sui-Tang dynasty (581–907 CE) and has been adapted here for AI agent orchestration.

Key inspirations from the original:
- **三权分立** (Separation of three powers): Planning → Review → Execution
- **封驳权** (Veto power): Review bodies can reject decisions from planning bodies
- **六部分权** (Six-ministerial division of labor): Specialized departments with clear boundaries
- **台谏制度** (Censorate system): Independent audit as a separate branch

The naming evolution from 三省六部 to 三总六科 reflects a deliberate modernization: **省 (provincial ministry) → 总 (corporate director)**, **部 (ministry) → 科 (business section)**, and **司 (bureau) → 秘书处 (corporate secretariat)**.

### ETO (Evolutionary-Teal Organization)

TRSS is the implementation layer of the **ETO** design philosophy — an AI agent orchestration framework inspired by Frédéric Laloux's *Reinventing Organizations* (2014). Laloux's teal-organization model (self-management, wholeness, evolutionary purpose) provides the long-term vision; TRSS provides the amber-to-orange evolutionary path.

## Open-Source Dependencies

| Project | License | Usage |
|:--------|:--------|:------|
| [AgentFlow](https://github.com/noahyamamoto/AgentFlow) | MIT | Pipeline graph definition and execution engine |
| [LangGraph](https://github.com/langchain-ai/langgraph) | MIT | Alternative implementation (in `langgraph/`) |
| [reasonix](https://github.com/AnastasiyaW/reasonix) | MIT | LLM runner for document/report tasks |
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) | Proprietary | Agent for code development and audit tasks |

## Design References

- Laloux, F. (2014). *Reinventing Organizations: A Guide to Creating Organizations Inspired by the Next Stage of Human Consciousness*
- Anthropic (2025). *Building effective agents* — Practical patterns for agent orchestration
- Microsoft (2024). *AutoGen* — Multi-agent conversation framework
- Google (2025). *A2A (Agent-to-Agent) Protocol* — Inter-agent communication standard

## Repository Structure

This project was originally developed under the name **三省六部 (Three Departments Six Ministries)**, migrated to **TLP (Three-Line Pipeline)**, and finally restructured as **TRSS (Three-Review Six-Section)** for public release. The evolution is documented in `docs/naming-mapping.md`.

---

*If your work is referenced here and you'd like an update, please open an issue.*
