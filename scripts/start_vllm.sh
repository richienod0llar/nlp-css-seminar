#!/bin/bash
# Start vLLM server for Qwen3.5-9B (run on GPU compute node).
# Usage: bash scripts/start_vllm.sh
#
# Logs are written to outputs/logs/vllm_startup_<timestamp>.log (no need to
# scroll the terminal to copy errors).
#
# LRZ driver CUDA 12.2 + vLLM 0.23 (libcudart.so.13) needs the workarounds below.
# See scripts/setup_cuda_libs.sh for the CUDA library path setup.

set -euo pipefail

source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate sig-llm
# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/setup_cuda_libs.sh"

MODEL_PATH="/dss/dssmcmlfs01/pn25ju/pn25ju-dss-0000/models/Qwen3.5-9B"

export VLLM_LOGGING_LEVEL="${VLLM_LOGGING_LEVEL:-INFO}"
# Avoid FlashInfer sampler JIT (nvcc/header mismatch on LRZ).
export VLLM_USE_FLASHINFER_SAMPLER=0

LOG_DIR="$HOME/nlp-css-seminar/outputs/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/vllm_startup_$(date +%Y%m%d_%H%M%S).log"
echo "Logging to $LOG_FILE"

vllm serve "$MODEL_PATH" \
  --host 0.0.0.0 \
  --port 8000 \
  --dtype bfloat16 \
  --max-model-len 8192 \
  --enforce-eager \
  --gdn-prefill-backend triton \
  --attention-backend TRITON_ATTN \
  --compilation-config '{"custom_ops":["none"]}' \
  --trust-remote-code \
  --limit-mm-per-prompt '{"image":0,"video":0}' \
  2>&1 | tee "$LOG_FILE"
