# nlp-css-seminar

Prompt-driven pipeline to generate survey items from health indicators (Assertion Developer + Question Developer), evaluated against a gold set. Runs on LRZ with **Qwen3.5-9B** served via vLLM.

**Status:** Phase 0 done (env, GPU, vLLM). Phase 1 (agents + eval) in progress. See [docs/PLAN.md](docs/PLAN.md) for the full roadmap.

## Repo layout

```
nlp-css-seminar/
├── README.md                 # this file
├── docs/
│   └── PLAN.md               # implementation plan and LRZ setup notes
├── data.xlsx                 # gold set (115 rows); will move to data/ in Phase 1
├── environment.yml           # conda env spec (sig-llm, Python 3.11)
├── requirements.txt          # pipeline / eval Python deps
├── requirements-llm.txt      # HuggingFace + ML stack deps
├── outputs/
│   └── .gitignore            # ignores logs/ (vLLM startup logs, etc.)
├── scripts/
│   ├── activate_env.sh       # conda activate sig-llm + CUDA lib paths
│   ├── setup_cuda_libs.sh    # LRZ CUDA 12.2 workaround for vLLM 0.23
│   ├── install_pytorch.sh    # pinned PyTorch cu126 install
│   ├── request_gpu.sh        # example salloc for 1x H100
│   ├── start_vllm.sh         # start vLLM server (main entry point)
│   ├── start_vllm_debug.sh   # same with DEBUG logging
│   ├── smoke_test_transformers.py   # HF load test on GPU
│   └── smoke_test_llm.py            # OpenAI API test against vLLM
├── Protocol Meeting Lanre & Rudraksha.docx   # annotation guide / protocol
└── Week 3 lrz-tutorial.pdf                   # LRZ GPU tutorial
```

**Phase 1 (not in repo yet):** `config.yaml`, `src/sig/` (agents, prompts, evaluation), `data/concepts.yaml`, `scripts/run_evaluation.py`.

## Quick start (LRZ)

### 1. Environment

```bash
cd ~/nlp-css-seminar
# one-time: create env per docs/PLAN.md, or:
conda env create -f environment.yml
source scripts/activate_env.sh
```

### 2. GPU session

```bash
bash scripts/request_gpu.sh          # or your own salloc
srun --jobid=<JOBID> --overlap --pty bash
```

### 3. Start vLLM (terminal 1)

```bash
cd ~/nlp-css-seminar
bash scripts/start_vllm.sh
```

Wait for `Application startup complete`. Logs go to `outputs/logs/vllm_startup_*.log`.

### 4. Smoke test (terminal 2, same SLURM job)

```bash
srun --jobid=<JOBID> --overlap --pty bash
source ~/nlp-css-seminar/scripts/activate_env.sh
cd ~/nlp-css-seminar
python scripts/smoke_test_llm.py
```

## Scripts reference

| Script | Purpose |
|--------|---------|
| `activate_env.sh` | Activate `sig-llm` and set `LD_LIBRARY_PATH` for vLLM |
| `setup_cuda_libs.sh` | Sourced by `activate_env.sh` / `start_vllm.sh` |
| `install_pytorch.sh` | Install pinned PyTorch (CUDA 12.6) |
| `request_gpu.sh` | Request interactive H100 via SLURM |
| `start_vllm.sh` | Serve Qwen3.5-9B on port 8000 |
| `start_vllm_debug.sh` | Verbose vLLM logs |
| `smoke_test_transformers.py` | Test HF model load on GPU |
| `smoke_test_llm.py` | Test `/v1/models` and `/v1/chat/completions` |

## Model

- **Path:** `/dss/dssmcmlfs01/pn25ju/pn25ju-dss-0000/models/Qwen3.5-9B` (shared LRZ storage, read-only)
- **API:** `http://localhost:8000/v1` (OpenAI-compatible, key can be `EMPTY`)

## Notes

- Run vLLM and Python clients on the **same compute node**, not the login node.
- LRZ H100 nodes need the vLLM flags in `start_vllm.sh` (Triton attention, etc.). Do not use a bare `vllm serve` command.
- Git push needs `ssh-add ~/.ssh/id_ed25519_github` if your key has a passphrase.
