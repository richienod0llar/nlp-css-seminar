#!/bin/bash
# Start vLLM server for Qwen2.5-72B-Instruct (external judge on port 8001).
# Requires 2 GPUs (tensor parallelism). Run on LRZ H100 compute node.
#
# Usage: bash scripts/start_vllm_judge.sh
#
# Then in another terminal:
#   python scripts/run_judge_only.py docs/baseline/eval_report_vllm_20260625_160020.csv

set -euo pipefail

source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate sig-llm
# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/setup_cuda_libs.sh"

MODEL_PATH="/dss/dssmcmlfs01/pn25ju/pn25ju-dss-0000/models/Qwen2.5-72B-Instruct"
PORT="${VLLM_JUDGE_PORT:-8001}"
TP_SIZE="${VLLM_JUDGE_TP:-2}"

export VLLM_LOGGING_LEVEL="${VLLM_LOGGING_LEVEL:-INFO}"
export VLLM_USE_FLASHINFER_SAMPLER=0

LOG_DIR="$HOME/nlp-css-seminar/outputs/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/vllm_judge_startup_$(date +%Y%m%d_%H%M%S).log"
echo "Starting external judge vLLM on port $PORT (TP=$TP_SIZE)"
echo "Logging to $LOG_FILE"

vllm serve "$MODEL_PATH" \
  --host 0.0.0.0 \
  --port "$PORT" \
  --dtype bfloat16 \
  --tensor-parallel-size "$TP_SIZE" \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.92 \
  --enforce-eager \
  --trust-remote-code \
  2>&1 | tee "$LOG_FILE"
