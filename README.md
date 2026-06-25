# nlp-css-seminar

Prompt-driven pipeline to generate survey items from health indicators (Assertion Developer + Question Developer), evaluated against a gold set. Runs on LRZ with **Qwen3.5-9B** served via vLLM.

**Status:** Phase 1b complete (2026-06-25): Run 4 with judge — **75.7%** concept / **62.6%** structure / **4.99/5** question alignment. See [docs/BASELINE_REPORT.md](docs/BASELINE_REPORT.md). Next: structure pass for `xFD`/`xFy`, optional external judge or LoRA. Full plan: [docs/PLAN.md](docs/PLAN.md).

## Baseline results (Qwen3.5-9B, zero-shot + judge)

| Metric | Run 3 | Run 4 (+ judge) |
|--------|-------|-----------------|
| Concept accuracy | **75.7%** | 75.7% |
| Structure accuracy | **62.6%** | 62.6% |
| Question non-empty | **100%** | 100% |
| Question exact match | 18.3% | 18.3% |
| Mean IA judge (1–5) | — | **4.51** |
| Mean AQ judge (1–5) | — | **4.99** |

Prompt-engineering progression (Runs 1→3): concept 57% → 70% → **76%**; structure 51% → 56% → **63%**.

## Repo layout

```
nlp-css-seminar/
├── README.md
├── config.yaml                 # LLM endpoint, mock flag, eval settings
├── docs/
│   ├── PLAN.md
│   ├── BASELINE_REPORT.md      # Initial 115-row baseline write-up
│   └── baseline/               # Committed summary JSON snapshots
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
├── run_test_pipeline.py        # quick single-indicator demo (stdout only)
├── test_load.py                # loader + prompt injection test
├── scripts/
│   ├── activate_env.sh
│   ├── setup_cuda_libs.sh
│   ├── request_gpu.sh          # interactive GPU (salloc)
│   ├── start_vllm.sh           # vLLM server (use this, not bare vllm serve)
│   ├── smoke_test_llm.py
│   └── smoke_test_transformers.py
├── outputs/                    # eval reports + logs/ (logs gitignored)
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

### 4. Pipeline and evaluation

`config.yaml` settings:

```yaml
llm:
  mock: false              # true = MockLLMClient (no vLLM)
  enable_thinking: false   # required for reliable JSON from Qwen3.5
eval:
  max_rows: null           # null = all 115 rows; 5 for quick test
  output_dir: "outputs/"
```

**Single indicator (stdout only):**

```bash
python run_test_pipeline.py
```

**Full baseline eval** (writes CSV + JSON to `outputs/`):

```bash
python -m src.sig.evaluation.run_eval
```

For mock mode (no GPU): set `mock: true` and run the same commands.

## Scripts reference

| Script | Purpose |
|--------|---------|
| `request_gpu.sh` | Interactive 1× H100 via `salloc` |
| `activate_env.sh` | Activate `sig-llm` + CUDA lib paths |
| `start_vllm.sh` | Serve Qwen3.5-9B on port 8000 |
| `smoke_test_llm.py` | Test vLLM OpenAI API |
| `run_test_pipeline.py` | One-indicator pipeline demo |
| `src/sig/evaluation/run_eval.py` | Full gold-set eval (isolated mode) |

## Model

- **Path:** `/dss/dssmcmlfs01/pn25ju/pn25ju-dss-0000/models/Qwen3.5-9B`
- **API:** `http://localhost:8000/v1` (key: `EMPTY`)

## Notes

- vLLM and Python clients must run on the **same compute node**.
- Use `scripts/start_vllm.sh`; bare `vllm serve` crashes on LRZ without the CUDA workarounds.
- Eval uses **isolated mode**: question developer is scored on gold assertions, not chained predictions.
- Git push: `ssh-add ~/.ssh/id_ed25519_github` if your key has a passphrase.
