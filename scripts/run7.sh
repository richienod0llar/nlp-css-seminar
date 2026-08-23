#!/bin/bash
#SBATCH --job-name=sig-run7
#SBATCH --partition=lrz-hgx-h100-94x4
#SBATCH --time=05:00:00
#SBATCH --gres=gpu:2
#SBATCH --cpus-per-task=16
#SBATCH --mem=96G
#SBATCH --output=outputs/logs/run7_%j.log

# Every GPU-dependent fix the paper review asks for, in ONE allocation, because
# requesting a job has more overhead than the compute does.
#
#   Stage 1 (9B, 1 GPU)   three ablation arms, one intervention each -- answers W5
#     v6repro : current prompt, repaired concepts.yaml   (isolates the YAML repair)
#     v7a     : + worked examples de-leaked from the gold set (isolates leakage, W1)
#     v7b     : + notation-derived Norms/Policies/Causal rule (the targeted fix)
#   Stage 2 (72B, 2 GPUs) external judge on Run 6 and on v7b   -- rec #1
#                         72B also GENERATES a full set, then judges itself and the 9B
#   Stage 3 (9B again)    9B judges both generation sets -> completes the 2x2  -- W3
#
# Submit:  sbatch scripts/run7.sh
# Results land in outputs/; commit the ones you keep to docs/baseline/.

set -euo pipefail

PROJECT_ROOT="${HOME}/nlp-css-seminar"
cd "${PROJECT_ROOT}"
mkdir -p outputs/logs

source "${PROJECT_ROOT}/scripts/activate_env.sh"

GEN_MODEL="/dss/dssmcmlfs01/pn25ju/pn25ju-dss-0000/models/Qwen3.5-9B"
JUDGE_MODEL="/dss/dssmcmlfs01/pn25ju/pn25ju-dss-0000/models/Qwen2.5-72B-Instruct"
RUN6_CSV="docs/baseline/eval_report_vllm_20260703_180434.csv"

SERVER_PID=""

stop_server() {
  if [[ -n "${SERVER_PID}" ]] && kill -0 "${SERVER_PID}" 2>/dev/null; then
    echo ">>> stopping server ${SERVER_PID}"
    kill "${SERVER_PID}" 2>/dev/null || true
    wait "${SERVER_PID}" 2>/dev/null || true
    sleep 20  # let the GPUs drain before the next model loads
  fi
  SERVER_PID=""
}
trap stop_server EXIT

wait_for() {  # wait_for <port> <max_tries>
  local port="$1" tries="$2"
  echo ">>> waiting for vLLM on :${port}"
  for _ in $(seq 1 "${tries}"); do
    if curl -sf "http://localhost:${port}/v1/models" >/dev/null 2>&1; then
      echo ">>> ready on :${port}"
      return 0
    fi
    if [[ -n "${SERVER_PID}" ]] && ! kill -0 "${SERVER_PID}" 2>/dev/null; then
      echo "!!! server exited early -- check outputs/logs/vllm_*"
      exit 1
    fi
    sleep 10
  done
  echo "!!! server did not become ready on :${port}"
  exit 1
}

latest() {  # newest outputs/ file matching a glob
  ls -t outputs/$1 2>/dev/null | head -1
}

# --------------------------------------------------------------------------
# Stage 1 -- ablation arms on the 9B generator
# --------------------------------------------------------------------------
echo "=== STAGE 1: 9B generator, three ablation arms ==="
CUDA_VISIBLE_DEVICES=0 bash scripts/start_vllm.sh &
SERVER_PID=$!
wait_for 8000 120

python -m src.sig.evaluation.run_eval --tag v6repro \
  --assertion-prompt src/sig/prompts/assertion_developer.md
python -m src.sig.evaluation.run_eval --tag v7a \
  --assertion-prompt src/sig/prompts/assertion_developer_v7a.md
python -m src.sig.evaluation.run_eval --tag v7b \
  --assertion-prompt src/sig/prompts/assertion_developer_v7b.md

V7B_CSV="$(latest 'eval_report_vllm_v7b_*.csv')"
echo ">>> v7b predictions: ${V7B_CSV}"
stop_server

# --------------------------------------------------------------------------
# Stage 2 -- 72B: judge the 9B runs, then generate and judge itself
# --------------------------------------------------------------------------
echo "=== STAGE 2: 72B judge (TP=2) ==="
bash scripts/start_vllm_judge.sh &
SERVER_PID=$!
wait_for 8001 180

# rec #1: the external judge has never been run on the best configuration
python scripts/run_judge_only.py "${RUN6_CSV}" --tag run6
python scripts/run_judge_only.py "${V7B_CSV}" --tag v7b

# W3: the 72B generates its own items, so "self-preference" can be separated
# from "bigger model is stricter". Same prompt, same protocol, different model.
python -m src.sig.evaluation.run_eval --tag gen72b \
  --model "${JUDGE_MODEL}" --base-url "http://localhost:8001/v1" \
  --assertion-prompt src/sig/prompts/assertion_developer_v7b.md
GEN72B_CSV="$(latest 'eval_report_vllm_gen72b_*.csv')"
echo ">>> 72B generations: ${GEN72B_CSV}"

# 2x2 cell: 72B judging its own output
python scripts/run_judge_only.py "${GEN72B_CSV}" --tag j72b_on_gen72b
stop_server

# --------------------------------------------------------------------------
# Stage 3 -- 9B judges both generation sets (remaining 2x2 cells)
# --------------------------------------------------------------------------
echo "=== STAGE 3: 9B as judge, both generation sets ==="
CUDA_VISIBLE_DEVICES=0 bash scripts/start_vllm.sh &
SERVER_PID=$!
wait_for 8000 120

python scripts/run_judge_only.py "${V7B_CSV}" --tag j9b_on_gen9b \
  --judge-model "${GEN_MODEL}" --judge-base-url "http://localhost:8000/v1"
python scripts/run_judge_only.py "${GEN72B_CSV}" --tag j9b_on_gen72b \
  --judge-model "${GEN_MODEL}" --judge-base-url "http://localhost:8000/v1"
stop_server

echo "=== DONE. Next: python scripts/reanalysis.py ==="
ls -t outputs/eval_summary_* | head -12
