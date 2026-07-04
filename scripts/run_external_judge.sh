#!/bin/bash
#SBATCH --job-name=sig-ext-judge
#SBATCH --partition=lrz-hgx-h100-94x4
#SBATCH --time=02:00:00
#SBATCH --gres=gpu:2
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --output=outputs/logs/ext_judge_%j.log

set -euo pipefail

PROJECT_ROOT="${HOME}/nlp-css-seminar"
cd "${PROJECT_ROOT}"
mkdir -p outputs/logs

source "${PROJECT_ROOT}/scripts/activate_env.sh"

REPORT_CSV="${1:-docs/baseline/eval_report_vllm_20260625_160020.csv}"
MAX_ROWS="${MAX_ROWS:-}"

bash "${PROJECT_ROOT}/scripts/start_vllm_judge.sh" &
VLLM_PID=$!

cleanup() {
  if kill -0 "${VLLM_PID}" 2>/dev/null; then
    kill "${VLLM_PID}" || true
  fi
}
trap cleanup EXIT

JUDGE_URL="http://localhost:${VLLM_JUDGE_PORT:-8001}/v1/models"
echo "Waiting for judge vLLM at ${JUDGE_URL} ..."
for i in $(seq 1 180); do
  if curl -sf "${JUDGE_URL}" >/dev/null 2>&1; then
    echo "Judge vLLM ready."
    break
  fi
  if ! kill -0 "${VLLM_PID}" 2>/dev/null; then
    echo "Judge vLLM exited early. Check outputs/logs/vllm_judge_startup_*.log"
    exit 1
  fi
  sleep 10
done

CMD=(python scripts/run_judge_only.py "${REPORT_CSV}")
if [[ -n "${MAX_ROWS}" ]]; then
  CMD+=(--max-rows "${MAX_ROWS}")
fi
"${CMD[@]}"
echo "External judge scoring complete."
