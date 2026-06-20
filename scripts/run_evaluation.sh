#!/bin/bash
#SBATCH --job-name=sig-eval
#SBATCH --partition=lrz-hgx-h100-94x4
#SBATCH --time=04:00:00
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --output=outputs/logs/eval_%j.log

set -euo pipefail

PROJECT_ROOT="${HOME}/nlp-css-seminar"
cd "${PROJECT_ROOT}"
mkdir -p outputs/logs

source "${PROJECT_ROOT}/scripts/activate_env.sh"

# Start vLLM in background (same flags as start_vllm.sh)
bash "${PROJECT_ROOT}/scripts/start_vllm.sh" &
VLLM_PID=$!

cleanup() {
  if kill -0 "${VLLM_PID}" 2>/dev/null; then
    kill "${VLLM_PID}" || true
  fi
}
trap cleanup EXIT

echo "Waiting for vLLM at http://localhost:8000/v1/models ..."
for i in $(seq 1 120); do
  if curl -sf http://localhost:8000/v1/models >/dev/null 2>&1; then
    echo "vLLM ready."
    break
  fi
  if ! kill -0 "${VLLM_PID}" 2>/dev/null; then
    echo "vLLM process exited early. Check outputs/logs/vllm_startup_*.log"
    exit 1
  fi
  sleep 5
done

python -m src.sig.evaluation.run_eval
echo "Evaluation complete."
