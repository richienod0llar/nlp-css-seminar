#!/bin/bash
# Start vLLM server for Qwen3.5-9B (run on GPU compute node).
# Usage: bash scripts/start_vllm.sh

set -euo pipefail

source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate sig-llm

MODEL_PATH="/dss/dssmcmlfs01/pn25ju/pn25ju-dss-0000/models/Qwen3.5-9B"

vllm serve "$MODEL_PATH" \
  --host 0.0.0.0 \
  --port 8000 \
  --dtype auto \
  --max-model-len 8192
