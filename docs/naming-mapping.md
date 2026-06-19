# Naming Mapping — 三省六部 → 三总六科 (TRSS)

This document traces the naming evolution from the original Tang-dynasty concept to the modern corporate restructure.

## Core Project Name

| Phase | Name | Meaning | Period |
|:------|:-----|:--------|:-------|
| 1 | **三省六部** (Sansheng Liubu) | Three Departments, Six Ministries | Tang dynasty (581–907 CE) concept |
| 2 | **TLP** (Three-Line Pipeline) | — | Internal development phase |
| 3 | **TRSS / 三总六科** | Three Reviews, Six Sections | Public release (this repo) |

## Department Mapping

The naming follows a clear modernization pattern:
- **省** (provincial ministry) → **总** (corporate director)
- **部** (ministry) → **科** (business section)
- **司** (imperial bureau) → **秘书处** (corporate secretariat)
- **官** (imperial official) → **处** (office)

| 三省六部 (Original) | 三总六科 (Modern) | English | Role |
|:--------------------|:-----------------|:--------|:------|
| **通政司** | **秘书处** | Secretariat | Task reception, triage, routing |
| **中书省** | **方案总** | Planning Director | Task decomposition, strategy, mode recommendation |
| **门下省一审** | **审核总** | Review Director | Plan review, approval or redesign |
| **尚书省** | **执行总** | Execution Director | Dispatch tasks to sections |
| **门下省二审** | **质控总** | Quality Director | Output review, naming, archive routing |
| **刑部**(终审) | **审计总** | Audit Director | Final security & compliance sign-off |
| **早朝官** | **督办处** | Oversight Office | Collation, archiving, verdict check, notifications |
| — | — | — | — |
| **礼部** | **内容科** | Content Section | Documentation, reports, content generation |
| **兵部** | **研发科** | R&D Section | Code development, technical implementation |
| **工部** | **工程科** | Engineering Section | CI/CD, deployment, toolchain |
| **户部** | **数据科** | Data Section | Data analysis, resource estimation, feasibility |
| **吏部** | **人事科** | HR Section | Agent management, permissions, skill tracking |
| **刑部**(执行) | **审计科** | Audit Section | Security auditing, compliance checking |
| **司天监** | **情报科** | Intelligence Section | External knowledge search, fact verification |

## Why Modernize?

The original 三省六部 naming is historically accurate and conceptually powerful, but for open-source distribution, a modern corporate vocabulary was chosen to:

1. **Lower barrier to entry** — developers unfamiliar with Chinese history can immediately grasp each unit's role
2. **Signal intentionality** — the naming change is deliberate, showing the concept has been adapted, not just copied
3. **Avoid confusion** — "三省六部" already refers to a specific historical institution; this project is a reimagination, not a reenactment

The intellectual debt to the original 三省六部 system is fully acknowledged in [CREDITS.md](../CREDITS.md). The architecture itself — separation of powers, sequential review, parallel execution, independent audit — remains faithful to the original design.
