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
#   Stage 2 (32B, 2 GPUs) external judge on Run 4, Run 6 and v7b   -- rec #1
#                         32B also GENERATES a full set, then judges itself and the 9B
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
JUDGE_MODEL="/dss/dssmcmlfs01/pn25ju/pn25ju-dss-0000/models/Qwen3-32B"
RUN6_CSV="docs/baseline/eval_report_vllm_20260703_180434.csv"
# The predictions Run 5 judged with the now-deleted 72B. Re-judging them with the
# 32B is the only like-for-like old-judge/new-judge comparison, and it keeps
# fig12/fig13 reproducible under the replacement instrument.
RUN4_CSV="docs/baseline/eval_report_vllm_20260625_160020.csv"

SERVER_PID=""

# The server scripts run `vllm serve ... | tee`, so SERVER_PID is the wrapper
# bash, not vLLM. Killing the wrapper orphans vLLM, which keeps holding ~90 GB
# and makes the NEXT stage die with "Free memory on device cuda:0 ... is less
# than desired GPU memory utilization". So: start each server with setsid, in
# its own process group, and signal the whole group. Then wait for the memory
# to actually come back instead of guessing with sleep 20.
start_server() {  # start_server <script> [env assignments...]
  setsid "$@" &
  SERVER_PID=$!
}

wait_gpu_free() {
  echo ">>> waiting for GPU memory to drain"
  for _ in $(seq 1 60); do
    local max
    max="$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits \
           | sort -rn | head -1)"
    if [[ -n "${max}" && "${max}" -lt 5000 ]]; then
      echo ">>> GPUs free (max ${max} MiB in use)"
      return 0
    fi
    sleep 5
  done
  echo "!!! GPU memory did not drain -- stray process still holding it:"
  nvidia-smi
  exit 1
}

stop_server() {
  if [[ -n "${SERVER_PID}" ]]; then
    echo ">>> stopping server group ${SERVER_PID}"
    kill -TERM -- -"${SERVER_PID}" 2>/dev/null || true
    for _ in $(seq 1 30); do
      kill -0 -- -"${SERVER_PID}" 2>/dev/null || break
      sleep 2
    done
    kill -KILL -- -"${SERVER_PID}" 2>/dev/null || true
    wait "${SERVER_PID}" 2>/dev/null || true
    SERVER_PID=""
    wait_gpu_free
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
# Resume support: RUN7_SKIP_STAGE1=1 reuses the newest v7b CSV already on disk
# (override with V7B_CSV=...). Stage 1 costs ~25 min, so don't repeat it just
# because a later stage died.
if [[ "${RUN7_SKIP_STAGE1:-0}" == "1" ]]; then
  V7B_CSV="${V7B_CSV:-$(latest 'eval_report_vllm_v7b_*.csv')}"
  if [[ -z "${V7B_CSV}" || ! -f "${V7B_CSV}" ]]; then
    echo "!!! RUN7_SKIP_STAGE1=1 but no v7b CSV found in outputs/"
    exit 1
  fi
  echo "=== STAGE 1 skipped -- reusing ${V7B_CSV} ==="
  wait_gpu_free
else
  echo "=== STAGE 1: 9B generator, three ablation arms ==="
  start_server env CUDA_VISIBLE_DEVICES=0 bash scripts/start_vllm.sh
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
fi

# --------------------------------------------------------------------------
# Stage 2 -- 32B: judge the 9B runs, then generate and judge itself
# --------------------------------------------------------------------------
echo "=== STAGE 2: 32B judge (TP=2) ==="
start_server bash scripts/start_vllm_judge.sh
wait_for 8001 180

# rec #1: the external judge has never been run on the best configuration
python scripts/run_judge_only.py "${RUN4_CSV}" --tag run4_32b
python scripts/run_judge_only.py "${RUN6_CSV}" --tag run6
python scripts/run_judge_only.py "${V7B_CSV}" --tag v7b

# W3: the 32B generates its own items, so "self-preference" can be separated
# from "bigger model is stricter". Same prompt, same protocol, different model.
python -m src.sig.evaluation.run_eval --tag gen32b \
  --model "${JUDGE_MODEL}" --base-url "http://localhost:8001/v1" \
  --assertion-prompt src/sig/prompts/assertion_developer_v7b.md
GEN32B_CSV="$(latest 'eval_report_vllm_gen32b_*.csv')"
echo ">>> 32B generations: ${GEN32B_CSV}"

# 2x2 cell: 32B judging its own output
python scripts/run_judge_only.py "${GEN32B_CSV}" --tag j32b_on_gen32b
stop_server

# --------------------------------------------------------------------------
# Stage 3 -- 9B judges both generation sets (remaining 2x2 cells)
# --------------------------------------------------------------------------
echo "=== STAGE 3: 9B as judge, both generation sets ==="
start_server env CUDA_VISIBLE_DEVICES=0 bash scripts/start_vllm.sh
wait_for 8000 120

python scripts/run_judge_only.py "${V7B_CSV}" --tag j9b_on_gen9b \
  --judge-model "${GEN_MODEL}" --judge-base-url "http://localhost:8000/v1"
python scripts/run_judge_only.py "${GEN32B_CSV}" --tag j9b_on_gen32b \
  --judge-model "${GEN_MODEL}" --judge-base-url "http://localhost:8000/v1"
stop_server

echo "=== DONE. Next: python scripts/reanalysis.py ==="
ls -t outputs/eval_summary_* | head -12
