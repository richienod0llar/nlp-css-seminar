# nlp-css-seminar

Prompt-driven pipeline to generate survey items from health indicators (Assertion Developer + Question Developer), evaluated against a gold set. Runs on LRZ with **Qwen3.5-9B** served via vLLM.

**Status:** Phase 0 complete (env, GPU, vLLM). Phase 1 in progress: agents + mock eval work locally; real vLLM eval not run yet. See [docs/PLAN.md](docs/PLAN.md).

## Repo layout

```
nlp-css-seminar/
├── README.md
├── config.yaml                 # LLM endpoint, mock flag, data paths
├── docs/PLAN.md
├── data/
│   ├── gold_set.xlsx           # 115-row gold set
│   └── concepts.yaml           # 22 concepts, structures, notation
├── src/sig/
│   ├── agents.py               # Assertion + Question developers
│   ├── pipeline.py             # indicator → assertion → question
│   ├── llm_client.py           # vLLM client + MockLLMClient
│   ├── loader.py               # gold set + concepts loader
│   ├── schema.py, normalize.py
│   ├── prompts/                # agent prompts + prompt_loader.py
│   └── evaluation/             # metrics.py, run_eval.py, judge.py (stub)
├── run_test_pipeline.py        # quick pipeline demo
├── test_load.py                # loader + prompt injection test
├── scripts/
│   ├── activate_env.sh
│   ├── setup_cuda_libs.sh
│   ├── request_gpu.sh          # interactive GPU (salloc)
│   ├── start_vllm.sh           # vLLM server (use this, not bare vllm serve)
│   ├── smoke_test_llm.py
│   └── smoke_test_transformers.py
├── outputs/                    # eval reports + logs/ (gitignored)
├── environment.yml
├── requirements.txt
└── requirements-llm.txt
```

## Quick start (LRZ)

### 1. Request a GPU (login node)

```bash
cd ~/nlp-css-seminar
bash scripts/request_gpu.sh
```

When `salloc` succeeds, note the **job ID** from `squeue -u $USER`, then enter the node:

```bash
srun --jobid=<JOBID> --overlap --pty bash
nvidia-smi
source ~/nlp-css-seminar/scripts/activate_env.sh
```

### 2. Start vLLM (terminal 1, on compute node)

```bash
cd ~/nlp-css-seminar
bash scripts/start_vllm.sh
```

Wait for `Application startup complete`.

### 3. Smoke test (terminal 2, same job)

```bash
srun --jobid=<JOBID> --overlap --pty bash
source ~/nlp-css-seminar/scripts/activate_env.sh
cd ~/nlp-css-seminar
python scripts/smoke_test_llm.py
```

### 4. Pipeline (mock vs real)

`config.yaml` has `mock: true` by default (no vLLM needed):

```bash
python run_test_pipeline.py
python -m src.sig.evaluation.run_eval
```

For real vLLM: set `mock: false` in `config.yaml`, start vLLM, then rerun.

## Scripts reference

| Script | Purpose |
|--------|---------|
| `request_gpu.sh` | Interactive 1× H100 via `salloc` |
| `activate_env.sh` | Activate `sig-llm` + CUDA lib paths |
| `start_vllm.sh` | Serve Qwen3.5-9B on port 8000 |
| `smoke_test_llm.py` | Test vLLM OpenAI API |
| `run_test_pipeline.py` | One-indicator pipeline demo |
| `src/sig/evaluation/run_eval.py` | Eval on first 10 gold rows (mock by default) |

## Model

- **Path:** `/dss/dssmcmlfs01/pn25ju/pn25ju-dss-0000/models/Qwen3.5-9B`
- **API:** `http://localhost:8000/v1` (key: `EMPTY`)

## Notes

- vLLM and Python clients must run on the **same compute node**.
- Use `scripts/start_vllm.sh`; bare `vllm serve` crashes on LRZ without the CUDA workarounds.
- Git push: `ssh-add ~/.ssh/id_ed25519_github` if your key has a passphrase.
