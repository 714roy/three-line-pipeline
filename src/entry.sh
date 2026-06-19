#!/bin/bash
# TRSS · AgentFlow pipeline entry (with rework loop + secretariat pre-check)
# THREE-REVIEW SIX-SECTION (三总六科) — modern corporate restructure of 三省六部
# Usage: trss <task description>
#
# Configuration via environment variables:
#   TRSS_PIPELINE_DIR   — pipeline definition location (default: /tmp/trss)
#   TRSS_OUTPUT_DIR     — output archive base (default: /tmp/trss/output)
#   TRSS_NOTIFY_CMD     — notification command (default: none)
#   TRSS_LLM_CMD        — LLM runner command (default: reasonix)
#   TRSS_LLM_MODEL      — default model (default: deepseek-v4-flash)

set -e

: "${TRSS_PIPELINE_DIR:=/tmp/trss}"
: "${TRSS_OUTPUT_DIR:=/tmp/trss/output}"
: "${TRSS_NOTIFY_CMD:=}"
: "${TRSS_LLM_CMD:=reasonix}"
: "${TRSS_LLM_MODEL:=deepseek-v4-flash}"

TASK="${1:-$(cat /dev/stdin)}"
if [ -z "$TASK" ]; then
    echo "Usage: trss <task>"
    echo "   or: echo '<task>' | trss"
    exit 1
fi

echo "$TASK" > /tmp/trss-TASK.txt
rm -f /tmp/trss-FEEDBACK.txt /tmp/trss-REWORK.txt

notify() {
    [ -n "$TRSS_NOTIFY_CMD" ] && eval "$TRSS_NOTIFY_CMD '$1'" 2>/dev/null || true
}

# ── Secretariat pre-check ──────────────────
echo "🔎 Secretariat pre-check..."
mkdir -p /tmp/trss-prompts

cat > /tmp/trss-prompts/secretariat-precheck.md << 'PROMPT_EOF'
You are the Secretariat of TRSS. Determine if the task below should get a quick answer (ROUTE=direct) or requires the full pipeline (ROUTE=pipeline).

ROUTE=direct (any one applies):
- Single factual question
- Brief answer sufficient, no deep analysis needed
- No cross-source verification required

ROUTE=pipeline (any applies):
- Deep analysis/research/comparison needed
- Formal document/solution required
- Multi-dimensional judgment involved

Output format (plain text, no markdown):
ROUTE=direct|pipeline
REASON=short reason
PROMPT_EOF

echo "---" >> /tmp/trss-prompts/secretariat-precheck.md
echo "Task: $(cat /tmp/trss-TASK.txt)" >> /tmp/trss-prompts/secretariat-precheck.md

$TRSS_LLM_CMD run -m $TRSS_LLM_MODEL --budget 0.05 \
  --system "$(cat /tmp/trss-prompts/secretariat-precheck.md)" \
  "Analyze task routing." > /tmp/trss-precheck-result.txt 2>/dev/null || true

ROUTE=$(sed 's/^[* |]*//' /tmp/trss-precheck-result.txt | grep "^ROUTE=" | tail -1 | cut -d= -f2 | tr -d '[:space:]')
echo "📋 Secretariat: ROUTE=${ROUTE:-pipeline}"

if [ "$ROUTE" = "direct" ]; then
  mkdir -p /tmp/trss-prompts
  cat > /tmp/trss-prompts/secretariat-direct.md << 'PROMPT_EOF'
You are the TRSS fast-track. The user asked a simple question — give a concise, accurate answer.
PROMPT_EOF

  echo "Task: $(cat /tmp/trss-TASK.txt)" >> /tmp/trss-prompts/secretariat-direct.md
  echo "" >> /tmp/trss-prompts/secretariat-direct.md
  echo "Answer directly." >> /tmp/trss-prompts/secretariat-direct.md

  $TRSS_LLM_CMD run -m $TRSS_LLM_MODEL --budget 0.1 \
    --system "$(cat /tmp/trss-prompts/secretariat-direct.md)" \
    "Execute the above task." > /tmp/trss-direct-answer.txt 2>/dev/null || {
    echo "❌ Secretariat direct-answer failed"
    exit 1
  }

  echo ""
  echo "━━━ TRSS Fast Track ━━━"
  cat /tmp/trss-direct-answer.txt
  echo "━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "✅ TRSS pipeline complete (direct route)"
  exit 0
fi

# ── Pipeline + rework loop ──────────────────
ROUND=1
MAX_ROUND=2

while [ $ROUND -le $MAX_ROUND ]; do
    export ROUND

    if [ $ROUND -ge 2 ] && [ -f /tmp/trss-FEEDBACK.txt ]; then
        export FEEDBACK_FILE=/tmp/trss-FEEDBACK.txt
        echo "🔄 Round $ROUND (injecting feedback)"
    else
        unset FEEDBACK_FILE
    fi

    # Restore MODE/TYPE for round 2+
    if [ $ROUND -eq 2 ]; then
      if [ ! -s /tmp/trss-CUR-MODE.txt ]; then
        grep -E '^MODE=' /tmp/_trss_ROUTE.txt 2>/dev/null | tail -1 > /tmp/trss-CUR-MODE.txt
      fi
      if [ ! -s /tmp/trss-MODE.txt ]; then
        cp /tmp/trss-CUR-MODE.txt /tmp/trss-MODE.txt 2>/dev/null || true
      fi
      if [ ! -s /tmp/trss-TYPE.txt ]; then
        grep -E '^TYPE=' /tmp/_trss_review.txt 2>/dev/null | tail -1 > /tmp/trss-TYPE.txt || true
      fi
    fi

    cd "$TRSS_PIPELINE_DIR"
    source /tmp/agentflow/.venv/bin/activate
    agentflow run pipeline.py || true

    # Check rework signal
    if [ ! -f /tmp/trss-REWORK.txt ]; then
        echo ""
        echo "✅ TRSS pipeline complete (round $ROUND passed)"
        exit 0
    fi

    ROUND=$((ROUND + 1))
    rm -f /tmp/trss-REWORK.txt

    if [ $ROUND -gt $MAX_ROUND ]; then
        echo ""
        echo "❌ TRSS failed after $MAX_ROUND rounds"
        echo "See $TRSS_OUTPUT_DIR for the latest audit report."
        notify "❌ TRSS failed after $MAX_ROUND rounds"
        exit 1
    fi

    echo "🔄 Entering round $ROUND..."
done
