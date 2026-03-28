#!/usr/bin/env bash
# Run the Mac CUA workflow.
# Usage:  ./run.sh [options]
#
# Options (all optional — defaults shown):
#   --model                qwen-3-vl
#   --model_url            http://172.22.225.5:8006/v1
#   --api_key              EMPTY
#   --temperature          1.0
#   --top_p                0.9
#   --max_tokens           32768
#   --history_n            4
#   --coordinate_type      relative
#   --sleep_after_execution 1.5

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Resolve conda env Python ─────────────────────────────────────────────────
CONDA_ENV="osworld"
PYTHON="$(conda info --base)/envs/${CONDA_ENV}/bin/python"
if [[ ! -x "$PYTHON" ]]; then
    echo "ERROR: could not find Python for conda env '$CONDA_ENV' at $PYTHON" >&2
    exit 1
fi
echo "Python: $PYTHON  (env: $CONDA_ENV)"

# ── Defaults ──────────────────────────────────────────────────────────────────
MODEL="qwen-3-vl"
MODEL_URL="http://172.22.225.5:8031/v1"
API_KEY="EMPTY"
TEMPERATURE="1.0"
TOP_P="0.9"
MAX_TOKENS="32768"
HISTORY_N="4"
COORDINATE_TYPE="relative"
SLEEP="1.5"
RECORD_DIR="/Users/jiateng5/research/Mac_Cua_Framework/interactive_position_workflow"
RECORD_FPS="5"

# ── Parse overrides ───────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --model)                 MODEL="$2";          shift 2 ;;
        --model_url)             MODEL_URL="$2";      shift 2 ;;
        --api_key)               API_KEY="$2";        shift 2 ;;
        --temperature)           TEMPERATURE="$2";    shift 2 ;;
        --top_p)                 TOP_P="$2";          shift 2 ;;
        --max_tokens)            MAX_TOKENS="$2";     shift 2 ;;
        --history_n)             HISTORY_N="$2";      shift 2 ;;
        --coordinate_type)       COORDINATE_TYPE="$2"; shift 2 ;;
        --sleep_after_execution) SLEEP="$2";          shift 2 ;;
        --record_dir)            RECORD_DIR="$2";    shift 2 ;;
        --record_fps)            RECORD_FPS="$2";    shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

# ── Run ───────────────────────────────────────────────────────────────────────
echo "Starting workflow: $(date '+%Y-%m-%d %H:%M:%S')"
echo "  model              : $MODEL"
echo "  model_url          : $MODEL_URL"
echo "  coordinate_type    : $COORDINATE_TYPE"
echo "  sleep_after_exec   : $SLEEP"
echo ""

cd "$DIR"
"$PYTHON" run.py \
    --model                 "$MODEL" \
    --model_url             "$MODEL_URL" \
    --api_key               "$API_KEY" \
    --temperature           "$TEMPERATURE" \
    --top_p                 "$TOP_P" \
    --max_tokens            "$MAX_TOKENS" \
    --history_n             "$HISTORY_N" \
    --coordinate_type       "$COORDINATE_TYPE" \
    --sleep_after_execution "$SLEEP" \
    --record_dir            "$RECORD_DIR" \
    --record_fps            "$RECORD_FPS"
