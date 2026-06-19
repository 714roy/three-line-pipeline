# Configuration

TRSS is configured entirely through environment variables.

## Core Settings

| Variable | Default | Description |
|:---------|:--------|:------------|
| `TRSS_PIPELINE_DIR` | `/tmp/trss` | Directory containing `pipeline.py` and `dsl.py` |
| `TRSS_OUTPUT_DIR` | `$HOME/output/trss` | Base directory for archived outputs |
| `TRSS_NOTIFY_CMD` | (none) | Shell command to run for pipeline notifications |
| `TRSS_LLM_CMD` | `reasonix` | LLM runner executable |
| `TRSS_LLM_MODEL` | `deepseek-v4-flash` | Default model for all LLM calls |

## LLM Runner

The default LLM runner is [reasonix](https://github.com/AnastasiyaW/reasonix), a lightweight CLI for LLM inference. You can override with any CLI tool that accepts:

```bash
$TRSS_LLM_CMD run -m $TRSS_LLM_MODEL --budget <n> --system "<prompt>" "<task>"
```

Compatible alternatives:
- `reasonix` (default) — high-throughput, prefix caching
- `claude` — Anthropic's Claude CLI
- Any custom wrapper script

## Notifications

To receive pipeline notifications (e.g., to Telegram, Discord, or a webhook), set:

```bash
export TRSS_NOTIFY_CMD='curl -s -X POST -d "message=$1" https://your-webhook.example.com/notify'
```

The command receives a single argument: the notification message string.

## Output Directory

By default, pipeline outputs are archived under `$HOME/output/trss/`. This can be any writable directory — Nutstore, Dropbox, or a dedicated workspace:

```bash
export TRSS_OUTPUT_DIR="$HOME/Nutstore Files/工坊/archive"
export TRSS_OUTPUT_DIR="/mnt/shared/trss-outputs"
```

## Example Setup

```bash
# Minimal
export TRSS_PIPELINE_DIR=/mnt/projects/trss/pipeline
alias trss='/mnt/projects/trss/src/entry.sh'
trss "What's new in AI agent frameworks?"

# Full with notifications
export TRSS_OUTPUT_DIR="$HOME/Nutstore Files/知屿/存档库"
export TRSS_NOTIFY_CMD='hermes send -t qqbot "$1" -q'
trss "Write a market analysis report"
```
