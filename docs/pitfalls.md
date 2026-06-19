# Pitfalls & Lessons Learned

> A collection of bugs, design flaws, and hard-won lessons from running the TRSS pipeline in production. Updated 2026-06-19.

---

## 🔴 P1: Jinja2 Templates Don't Know Python Variables

**Severity:** Critical — pipeline crash

AgentFlow uses Jinja2 to render shell scripts **before execution**. `{{ variable }}` only works for AgentFlow context variables (e.g., `{{ nodes.NodeName.output }}`), **not** for Python module-level variables.

```python
# ❌ CRASH: Jinja2 doesn't know TASK
"{{ TASK }}"

# ✅ DO: Use Python f-string + file-based injection
f"【任务】{TASK}"
```

**Lesson:** Python variables and Jinja2 template variables are separate worlds. Copy task text into temp files and read from shell, never rely on `{{ }}` for Python variables.

---

## 🔴 P2: Parallel Nodes Crash on `nodes.X.output[:N]` Slicing

**Severity:** Critical — TypeError in Jinja2 rendering

When a shell node references a sibling parallel node's output: `{{ nodes.礼部.output[:3000] }}` — but the sibling hasn't started yet, so `output` is `None`, and `None[:3000]` raises `TypeError`.

```bash
# Fix: remove all output slicing in parallel-scoped nodes
sed -i 's/\.output\[:[0-9]*\]/.output/g' pipeline.py
```

**Lesson:** Never assume a parallel node's output is available. Only slice outputs of nodes that are guaranteed to have run (the preceding serial chain).

---

## 🟡 P3: Markdown Format Pollution on KEY=VALUE Extraction

**Severity:** High — silent archive failure

LLMs in a markdown context naturally wrap output values in `**bold**` or `| table |` formatting. When the pipeline does `grep "^OUTPUT_NAME="`, it finds `**OUTPUT_NAME=xxx**` which doesn't match.

```bash
# ❌ Fails on **OUTPUT_NAME=xxx**
grep "^OUTPUT_NAME=" file.txt

# ✅ Works on all common formats
sed "s/^[* |]*//" file.txt | grep "^OUTPUT_NAME="
```

**Affected extractions:** OUTPUT_NAME, ARCHIVE_PATH, MODE, TYPE, VERDICT, FEEDBACK, REWORK_TYPE — 6+ fields across 3 review nodes.

**Lesson:** Always strip leading markdown before grep for KEY=VALUE extractions. Use `sed "s/^[* |]*//"` as a universal prefix stripper.

---

## 🟡 P4: MCP Tool Output Noise Contaminates Documents

**Severity:** High — 400+ lines of JSON prepended to output

When LLM runners load MCP servers (like agentmemory), startup probes auto-execute and their raw JSON responses get mixed into the generated content.

```bash
# Fix: filter out MCP noise in the Oversight Office
for f in "$DEST/产出/"*.md; do
  head -1 "$f" | grep -q "^\[tool agentmemory_" || continue
  sed -i "0,/^# /{//!d}" "$f"  # delete everything before first heading
done
```

**Lesson:** Any LLM output that passes through MCP-enabled runners is vulnerable to probe-injection. Always filter at the archive step.

---

## 🟡 P5: Entry Script vs Pipeline Directory Drift

**Severity:** High — running old code without knowing

The entry script (`entry.sh`) runs `agentflow run` in `$TRSS_PIPELINE_DIR`. If fixes are applied to the source tree but not re-deployed, the pipeline silently runs stale code.

```bash
# Add a version check at startup
if [ -f "$TRSS_PIPELINE_DIR/pipeline.py" ]; then
  SRC_MD5=$(md5sum "$SOURCE_TREE/pipeline.py" | cut -d' ' -f1)
  DEP_MD5=$(md5sum "$TRSS_PIPELINE_DIR/pipeline.py" | cut -d' ' -f1)
  if [ "$SRC_MD5" != "$DEP_MD5" ]; then
    cp "$SOURCE_TREE/pipeline.py" "$TRSS_PIPELINE_DIR/"
  fi
fi
```

**Lesson:** Fix the source tree, then re-deploy to the pipeline directory. Add a startup hash check.

---

## 🟡 P6: Python `-c` Inline with `$` Characters in Bash Context

**Severity:** High — shell syntax error

Embedding Python code in `bash -c` (via AgentFlow's shell executor) with `$` characters (e.g., regex anchors) causes bash to interpret them as variable references.

```python
# ❌ BROKEN: $ inside python3 -c "..."
python3 -c "re.compile(r'^(?:foo|bar$)', re.M)"

# ✅ SAFE: Write temp file, then execute
cat > /tmp/script.py << 'PYEOF'
import re
re.compile(r'^(?:foo|bar$)', re.M)
PYEOF
python3 /tmp/script.py
```

**Lesson:** Never embed Python code with `$` characters in `python3 -c "..."`. Always write a temp file.

---

## 🟡 P7: AgentFlow Parallel Dispatch Breaks STOP Signals

**Severity:** High — duplicate execution

AgentFlow schedules **all nodes without explicit dependencies in parallel**. A Secretariat-written STOP file (`/tmp/trss-STOP.txt`) for the `direct` route isn't seen by other nodes — they've already started.

```bash
# Fix: pre-check at the entry script level, don't rely on AgentFlow file signals
ROUTE=$(reasonix precheck "$TASK")
if [ "$ROUTE" = "direct" ]; then
  reasonix answer "$TASK"
  exit 0  # never call agentflow at all
fi
agentflow run pipeline.py
```

**Lesson:** File signals are unreliable in a parallel execution model. Pre-route at the script level.

---

## 🟢 P8: Unquoted Heredoc in Bash Expands Variables

**Severity:** Medium — incorrect prompts

```bash
cat > prompt.md << PROMPT_EOF   # UNQUOTED — shell expands $VARS
cat > prompt.md << 'PROMPT_EOF' # QUOTED — literal text
```

When writing LLM prompts from shell scripts, use **quoted heredoc** (`<< 'EOF'`) to prevent shell expansion of `$` in the prompt text.

---

## 🟢 P9: Rework Loop Loses MODE/TYPE on Round 2

**Severity:** Medium — all nodes skip on second round

During rework round 2, nodes that skip (中书省 after round 1, etc.) don't output MODE/TYPE. If the temp files are consumed or overwritten, downstream nodes get empty MODE → all exit as `[SKIP]`.

```bash
# Fix: Persist MODE/TYPE from round 1 before starting round 2
if [ $ROUND -eq 2 ]; then
  grep -E '^MODE=' /tmp/_trss_ROUTE.txt > /tmp/trss-CUR-MODE.txt
  grep -E '^TYPE=' /tmp/_trss_REVIEW.txt > /tmp/trss-TYPE.txt
fi
```

**Lesson:** Rework loops must restore state from round 1 outputs, not from skipped round 2 outputs.

---

## 🟢 P10: Verdict Check Before Archive Loses Output

**Severity:** Medium — output discarded on rework

The original pipeline checked verdict before archiving. When rework was signaled, `exit 0` happened before `cp`, so the output was lost — rework had nothing to improve upon.

**Fix:** Archive first, then check verdict.

---

## Summary

| # | Pattern | Category | Fixed |
|:--|:--------|:---------|:------|
| P1 | Jinja2 doesn't know Python variables | AgentFlow | ✅ |
| P2 | Parallel node output slicing | AgentFlow | ✅ |
| P3 | Markdown format pollution | LLM output | ✅ (sed prefix) |
| P4 | MCP noise injection | LLM runner | ✅ (oversight filter) |
| P5 | Source/directory drift | Deployment | ⚠️ (add check) |
| P6 | Python `-c` with `$` | Shell scripting | ✅ (temp files) |
| P7 | File signal in parallel graph | AgentFlow | ✅ (pre-route) |
| P8 | Unquoted heredoc | Shell scripting | ✅ (quoted) |
| P9 | MODE/TYPE loss in rework | Pipeline logic | ✅ |
| P10 | Archive after verdict | Pipeline logic | ✅ (archive-first) |
