---

name: Survey Item Generator
overview: "Phase 1b complete (2026-06-25): Run 4 judge eval — 75.7% concept, 62.6% structure, 4.99/5 question alignment. Next: xFD structure pass, external judge or LoRA."
todos:

- id: github-auth-clone
content: "Set up GitHub SSH key on LRZ, add to GitHub account, clone [git@github.com](mailto:git@github.com):richienod0llar/nlp-css-seminar.git into ~/nlp-css-seminar/, verify remote and branch."
status: completed
- id: lrz-conda-env
content: "Set up LRZ conda env (sig-llm, Python 3.11): install Miniconda if needed, create env, install PyTorch (CUDA 12.6) + vLLM + project deps from requirements.txt / requirements-llm.txt."
status: completed
- id: lrz-gpu-access
content: "Verify GPU access on LRZ: salloc/sbatch on an appropriate partition, srun into compute node, confirm nvidia-smi and conda env activate."
status: completed
- id: vllm-server-setup
content: "Configure and smoke-test vLLM server for Qwen3.5-9B from shared model path (interactive salloc first, then sbatch script)."
status: completed
- id: scaffold
content: "Finish project scaffold: config.yaml, src/sig/ package layout, data/gold_set.xlsx (move from repo-root data.xlsx). Partially done — env files, outputs/.gitignore, scripts/ exist."
status: completed
- id: concepts-ref
content: "Encode the annotation guide into data/concepts.yaml: 22 basic concepts (subjective/objective), the 3 structures, per-concept structure codes, and notation key."
status: completed
- id: gold-loader
content: Implement schema.py + gold-set loader for data.xlsx and a normalize.py for concept-name and structure-code matching (handles spelling/notation differences).
status: completed
- id: llm-client
content: "Implement llm_client.py: OpenAI-compatible client to vLLM with JSON-structured output and retry handling."
status: completed
- id: prompts
content: Write assertion_developer.md and question_developer.md system prompts from the guide rules, including the 3 worked reference rows as few-shot examples.
status: completed
- id: agents-pipeline
content: Implement AssertionDeveloper, QuestionDeveloper agents and pipeline.py (single indicator -> assertion -> question).
status: completed
- id: vllm-script
content: "scripts/start_vllm.sh (interactive) + scripts/run_evaluation.sh sbatch wrapper."
status: completed
- id: metrics
content: "metrics.py: exact-match, per-concept/structure breakdown, confusion matrix export, question-format distribution."
status: completed
- id: judge
content: "judge.py implemented; Run 4 complete (20260625_160020): mean IA 4.51, mean AQ 4.99. Optional: external judge model."
status: completed
- id: eval-runner
content: "run_eval.py: isolated mode over gold set, CSV + JSON to outputs/. Full 115-row baseline run complete (2026-06-20)."
status: completed
- id: smoke-test-transformers
content: "Add scripts/smoke_test_transformers.py: tutorial-style HF load of Qwen3.5-9B from shared path; run on GPU node before vLLM."
status: completed
- id: smoke-test-llm
content: "scripts/smoke_test_llm.py: OpenAI client against local vLLM (/v1/models + /v1/chat/completions)."
status: completed
- id: smoke-test
content: "Run a few gold-set rows end-to-end (agents + parsing + scoring) before the full 115-row eval."
status: completed
- id: baseline-report
content: "Document initial 115-row vLLM baseline in docs/BASELINE_REPORT.md + committed summary JSON."
status: completed
isProject: false

---

---

---

## Progress Update (2026-06-25, Run 4 judge)

**Run 4 complete** (`eval.run_judge: true`, timestamp `20260625_160020`). Same objective metrics as Run 3; adds semantic alignment scores.

| Metric | Result |
|--------|--------|
| Mean indicator→assertion judge | **4.51 / 5** |
| Mean assertion→question judge | **4.99 / 5** |
| Question exact match | 18.3% |
| Non-exact but judge ≥ 4 | 94 / 94 rows |

Report: [docs/BASELINE_REPORT.md](BASELINE_REPORT.md). Figures: `docs/figures/fig08`–`fig11`.

**Next:** structure pass for `xFD`/`xFy`; external judge (Qwen2.5-72B) or LoRA on assertion stage.

---

## Progress Update (2026-06-25, Run 3)

**Run 3 complete** (structure prompt pass + JSON repair + richer metrics). `eval.run_judge: false`.

| Metric | Run 2 | Run 3 | Δ |
|--------|-------|-------|---|
| Concept accuracy | 69.6% | **75.7%** | +6.1 pp |
| Structure accuracy | 55.7% | **62.6%** | +6.9 pp |
| Both correct | 53.0% | **60.9%** | +7.8 pp |
| Question non-empty | 99.1% | **100%** | +0.9 pp |

Report: [docs/BASELINE_REPORT.md](BASELINE_REPORT.md). Artifacts: `docs/baseline/eval_*_20260625_134833.*`

**Highlights:** Preference structure 40%→90%; row 114 JSON fixed; cumulative Run 1→Run 3: +18.3 pp concept.

**Next:** LLM-as-judge run (`eval.run_judge: true`); structure pass for `xFD`/`xFy`/`vIi`; optional LoRA if structure plateaus.

---

## Progress Update (2026-06-20)

**Baseline complete.** Full 115-row eval on LRZ H100 with Qwen3.5-9B + vLLM 0.23.


| Metric                           | Result |
| -------------------------------- | ------ |
| Concept accuracy                 | 57.4%  |
| Structure accuracy               | 51.3%  |
| Concept + structure both correct | 42.6%  |
| Question non-empty               | 99.1%  |
| Question exact match             | 20.0%  |


Report: [docs/BASELINE_REPORT.md](BASELINE_REPORT.md). Artifacts: `outputs/eval_report_vllm_20260620_185119.csv`, `outputs/eval_summary_vllm_20260620_185119.json`.

**Fixes applied for stable vLLM eval:**

- `enable_thinking: false` + `/no_think` for Qwen3.5 JSON output
- Separate JSON schemas for assertion vs question stages in `llm_client.py`
- `evaluate_row()` isolated eval (question dev on gold assertions)
- `normalize.py` wired into metrics

**Next steps (Phase 1b):**

1. Spelling normalization (`Behavior`/`Behaviour`, `judgment`/`judgement`)
2. Few-shot prompt improvements + concept output constraints
3. Implement `judge.py` (LLM-as-judge alignment scores)
4. Confusion matrix + per-concept breakdown in metrics
5. Optional LoRA SFT on assertion developer (train/val split)
6. `scripts/run_evaluation.sh` sbatch wrapper

---

## Progress Update (2026-06-19)

Completed locally:

- Created Phase 1 project scaffold
- Added concept.yaml reference file from protocol framework
- Implemented normalize.py utilities
- Implemented data loader
- Implemented LLM client
- Implemented MockLLMClient for local development
- Dynamically incorporated concept.yaml file into the prompts, ensuring LLM always has the latest rules without manual prompt editing. 
- Implemented AssertionDeveloper agent
- Implemented QuestionDeveloper agent
- Implemented SurveyPipeline
- Implemented initial eveluation metrics
- Implemented local evaluation runner
- Successfully executed end-to-end pipeline using mock responses.

---

# Survey Item Generator: Prompting Baseline + Evaluation

## Goal

Implement Caro's two ideas as a prompt-driven pipeline and evaluate it against the gold set, before any fine-tuning.

- Step 2 Assertion Developer: `input_indicator` -> `basic_concept` + `semantic_structure` + `assertion`
- Step 3 Question Developer: `assertion` -> `question` + `answer_options`
- Evaluation harness scoring both agents against `data.xlsx`

## Architecture

```mermaid
flowchart LR
  indicator["input_indicator"] --> AD["Assertion Developer (Qwen3.5-9B)"]
  AD --> concept["basic_concept"]
  AD --> struct["semantic_structure"]
  AD --> assertion["assertion"]
  assertion --> QD["Question Developer (Qwen3.5-9B)"]
  QD --> question["question"]
  QD --> options["answer_options"]
  gold["data.xlsx gold set"] --> evalH["Evaluation harness"]
  concept --> evalH
  struct --> evalH
  assertion --> evalH
  question --> evalH
  options --> evalH
```



vLLM runs as an OpenAI-compatible server on an LRZ GPU compute node (not the login node) loading the local model at `/dss/dssmcmlfs01/pn25ju/pn25ju-dss-0000/models/Qwen3.5-9B`. The pipeline and harness are plain Python clients hitting that endpoint. All Python work runs inside a dedicated conda env `**sig-llm**` on LRZ, following the [Week 3 lrz-tutorial.pdf](../Week%203%20lrz-tutorial.pdf) workflow.

```mermaid
flowchart TB
  vpn["EduVPN if off-campus"] --> ssh["SSH login.ai.lrz.de"]
  ssh --> login["Login node + tmux"]
  login --> conda["conda activate sig-llm"]
  conda --> salloc["salloc GPU job"]
  salloc --> compute["Compute node"]
  compute --> smokeHF["smoke_test_transformers.py optional"]
  compute --> vllm["bash scripts/start_vllm.sh :8000"]
  vllm --> api["OpenAI API localhost:8000/v1"]
  login --> client["run_evaluation.py on same compute node"]
  client --> api
```



## GitHub repo connection (Phase 0 — first step)

Remote: **[https://github.com/richienod0llar/nlp-css-seminar](https://github.com/richienod0llar/nlp-css-seminar)** (private). All project code lives in `**~/nlp-css-seminar/`** after clone. Your home directory keeps seminar docs separately unless you choose to move them into the repo later.

**Status: done (2026-06-16).** Repo at `~/nlp-css-seminar/`. Remote: `git@github.com:richienod0llar/nlp-css-seminar.git`. Branch: `main`, pushed to GitHub (Phase 0 infra commits). SSH auth works (key has a passphrase; run `ssh-add ~/.ssh/id_ed25519_github` once per session before non-interactive git push).

**Workflow going forward:** all project work happens inside `~/nlp-css-seminar/` and gets pushed to this repo. Commits only when explicitly requested; after each meaningful milestone, push to `origin main` (or a feature branch if we split work).

### 1. Generate an SSH key on LRZ (if you do not already have one for GitHub)

On the login node:

```bash
ssh-keygen -t ed25519 -C "your_email@example.com" -f ~/.ssh/id_ed25519_github
# press Enter for no passphrase, or set one if you prefer
cat ~/.ssh/id_ed25519_github.pub
```

Copy the **public** key output.

### 2. Add the key to GitHub

1. GitHub → **Settings** → **SSH and GPG keys** → **New SSH key**
2. Paste the public key, save

Alternatively use a **Personal Access Token (PAT)** for HTTPS clone, but SSH is simpler for ongoing push/pull on LRZ.

### 3. Configure SSH to use this key for GitHub

Add to `~/.ssh/config`:

```
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_github
  IdentitiesOnly yes
```

Test:

```bash
ssh -T git@github.com
# expect: "Hi richienod0llar! You've successfully authenticated..."
```

### 4. Clone the private repo

```bash
cd ~
git clone git@github.com:richienod0llar/nlp-css-seminar.git
cd nlp-css-seminar
git remote -v
git branch -a
git status
```

If the repo is empty, you will see an empty directory or only a README; that is fine — we scaffold the project inside it.

If clone fails with "repository not found", confirm: (a) Bolei/Lanre added your GitHub user as collaborator, (b) repo name is exact.

### 5. Wire in existing local files

Keep protocol docs in home or add to repo as needed:


| File                | Location in repo (current) |
| ------------------- | -------------------------- |
| Gold set            | `data/gold_set.xlsx`       |
| Protocol / LRZ docs | Repo root + `docs/PLAN.md` |
| Implementation plan | `docs/PLAN.md`             |


Add to `.gitignore` (root): `outputs/logs/`, `*.log`, `.env`, `__pycache__/`. Eval CSV/JSON in `outputs/` are local runtime artifacts; committed summaries live in `docs/baseline/`.

### 6. Git workflow during development

```bash
cd ~/nlp-css-seminar
git checkout -b feature/assertion-question-agents   # or main if solo
# ... work ...
git add -A && git status
git commit -m "Add assertion developer scaffold"
git push -u origin feature/assertion-question-agents
```

We only commit when you explicitly ask (per your rules). Default: work on a feature branch, push when ready.

### GitHub setup checklist

- [x] SSH key generated on LRZ
- [x] Public key added to GitHub account
- [x] `ssh -T git@github.com` succeeds
- [x] `~/nlp-css-seminar/` cloned, `origin` points to correct URL
- [x] First commit pushed (Phase 0 infra on `main`)

**Note:** SSH key has a passphrase. Before git push from a non-interactive session, run in your terminal:

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519_github
```

## LRZ environment setup (Phase 0 — after GitHub clone)

Based on [Week 3 lrz-tutorial.pdf](../Week%203%20lrz-tutorial.pdf). **Login nodes cannot run GPU jobs**; you must request a GPU via SLURM (`salloc` or `sbatch`), then activate your conda env on the compute node.

### 0. Connect to LRZ

1. On-campus: MWN or eduroam. Off-campus: install [EduVPN](https://www.eduvpn.org/client-apps/).
2. SSH: `ssh <username>@login.ai.lrz.de` (optional `Host lrz` in `~/.ssh/config`).
3. Web portal (files, jobs): [https://login.ai.lrz.de/](https://login.ai.lrz.de/)
4. Start **tmux** so work survives disconnects: `tmux`

Paths:

- Personal storage (100 GB): `/dss/dsshome1/02/<username>/` (yours: `/dss/dsshome1/02/ra35tif2/`)
- Shared models (read-only): `/dss/dssmcmlfs01/pn25ju/pn25ju-dss-0000/models/Qwen3.5-9B`
- Do not modify or delete shared storage (see usage guidelines in tutorial)

**Optional — VS Code Remote-SSH (tutorial pp. 20–26):** generate `ssh-keygen -t ed25519`, upload public key to `~/.ssh/authorized_keys` via LRZ web file manager, then connect VS Code to `login.ai.lrz.de` and edit `~/nlp-css-seminar/` while SLURM jobs run on compute nodes.

### 1. Install Miniconda (once, if not already present)

```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
source ~/miniconda3/etc/profile.d/conda.sh   # add to ~/.bashrc for persistence
```

Useful commands: `conda env list`, `conda activate sig-llm`, `conda list`, `conda remove -n sig-llm --all`.

### 2. Create the project conda env `sig-llm`

**Status: done.** Miniconda at `~/miniconda3/`. Env `sig-llm` (Python 3.11). PyTorch pinned to cu126 (`torch==2.11.0+cu126`). vLLM `0.23.0`. Use `source ~/nlp-css-seminar/scripts/activate_env.sh` (activates conda + CUDA lib paths).

Name: `**sig-llm`** (Python 3.11; tutorial uses `llm` — we use a project-specific name).

```bash
conda create -n sig-llm python=3.11 -y
conda activate sig-llm

# GPU PyTorch (CUDA 12.6) — see scripts/install_pytorch.sh for pinned versions
bash scripts/install_pytorch.sh

pip install vllm==0.23.0
pip install -r requirements-llm.txt
pip install -r requirements.txt
```

Tutorial `requirements-llm.txt` baseline (we extend with `vllm`):

```
transformers>=4.41.0
datasets>=2.20.0
accelerate>=0.30.0
huggingface_hub>=0.23.0
tokenizers>=0.19.0
scipy numpy pandas tqdm tensorboard python-dotenv
vllm   # added for OpenAI-compatible serving
```

We will split dependencies into two files in the repo:

- `requirements-llm.txt`: torch-adjacent + vLLM + HuggingFace stack (install on GPU node)
- `requirements.txt`: lightweight pipeline/eval client deps (can also run on login node for data prep, but inference must be on GPU node)

Also add `environment.yml` in the repo for reproducibility (`name: sig-llm`, `python=3.11`).

### 3. Request a GPU (interactive development)

Check partitions: `sinfo`

General LRZ (example from tutorial):

```bash
salloc -p lrz-hgx-h100-94x4 --time=0-2:00:00 --gres=gpu:1
# once allocated:
srun --pty bash
conda activate sig-llm
nvidia-smi   # verify GPU visible
```

MCML partition (requires `-q mcml`):

```bash
salloc -p mcml-dgx-a100-40x8 -q mcml --time=0-2:00:00 --gres=gpu:1
srun --pty bash
conda activate sig-llm
```

For Qwen3.5-9B + vLLM, **1 GPU** is enough (A100 40GB/80GB or H100 both fine). Enter the node with `srun --pty bash` or `srun --jobid=<JOBID> --overlap --pty bash` (job ID from [https://login.ai.lrz.de/](https://login.ai.lrz.de/) dashboard).

### 4. Sanity check: transformers load

**Status: done.** On the compute node:

```bash
source ~/nlp-css-seminar/scripts/activate_env.sh
cd ~/nlp-css-seminar
python scripts/smoke_test_transformers.py
```

The script sets `TORCH_CUDNN_SDPA_ENABLED=0` and `attn_implementation="eager"` to avoid cuDNN SDPA issues on LRZ H100 stacks.

### 5. Start the vLLM model server

**Status: done (interactive).** Do not run the bare `vllm serve ... --dtype auto` command on LRZ; it crashes on inference (CUDA 13 runtime vs driver 12.2, FlashAttention 3).

#### LRZ + vLLM 0.23 workarounds (required)

LRZ H100 nodes ship **driver CUDA 12.2**. vLLM 0.23 wheels link `**libcudart.so.13`**. Without fixes you get:

- `CUDA driver version is insufficient for CUDA runtime version` (FlashAttention / custom ops)
- FlashInfer JIT failures (`nvcc` / header mismatch)

**Fixes in repo:**


| File                          | Purpose                                                                 |
| ----------------------------- | ----------------------------------------------------------------------- |
| `scripts/setup_cuda_libs.sh`  | cu12 libs first, cu13 appended for extension load; `CUDA_HOME` for nvcc |
| `scripts/activate_env.sh`     | conda activate + sources setup_cuda_libs                                |
| `scripts/start_vllm.sh`       | Correct vLLM flags + logs to `outputs/logs/vllm_startup_*.log`          |
| `scripts/start_vllm_debug.sh` | Same with `VLLM_LOGGING_LEVEL=DEBUG`                                    |


**Required vLLM flags** (already in `start_vllm.sh`):

- `--attention-backend TRITON_ATTN` (not `FLASH_ATTN`; FA3 crashes on LRZ)
- `--gdn-prefill-backend triton`
- `--compilation-config '{"custom_ops":["none"]}'`
- `--enforce-eager`
- `export VLLM_USE_FLASHINFER_SAMPLER=0`

#### Interactive startup (terminal 1)

```bash
srun --jobid=<JOBID> --overlap --pty bash   # or srun --pty bash inside salloc
cd ~/nlp-css-seminar
bash scripts/start_vllm.sh
```

Wait for `Application startup complete`. Logs: `outputs/logs/vllm_startup_<timestamp>.log`.

#### Test (terminal 2 — new Cursor tab or second `srun` into same job)

```bash
srun --jobid=<JOBID> --overlap --pty bash
source ~/nlp-css-seminar/scripts/activate_env.sh
cd ~/nlp-css-seminar
curl http://localhost:8000/v1/models
python scripts/smoke_test_llm.py
```

First chat request may take 30–60s (Triton JIT). Set `enable_thinking: false` in `config.yaml` for eval; Qwen3.5 otherwise emits "Thinking Process" prose instead of JSON.

`**config.yaml` (Phase 1 — current):**

```yaml
llm:
  base_url: "http://localhost:8000/v1"
  model: "/dss/dssmcmlfs01/pn25ju/pn25ju-dss-0000/models/Qwen3.5-9B"
  api_key: "EMPTY"
  max_tokens: 1024
  temperature: 0.0
  enable_thinking: false
  mock: false
eval:
  max_rows: null   # null = all 115 rows
  output_dir: "outputs/"
```

**Important:** vLLM and the Python client must run on the **same compute node**. Use a second terminal tab with `srun --jobid=<ID> --overlap --pty bash`, not the login node.

### 6. Batch jobs via sbatch (Phase 1 — not yet implemented)

`scripts/start_vllm.sh` today is **interactive only** (no `#SBATCH` headers). For full 115-row eval, add sbatch wrappers that:

1. `source scripts/activate_env.sh` (not bare `conda activate`)
2. Call the same vLLM flags as `start_vllm.sh` (or `exec scripts/start_vllm.sh` after adding SBATCH headers to a separate `scripts/sbatch_vllm.sh`)

**Planned `scripts/run_evaluation.sh`:**

```bash
#!/bin/bash
#SBATCH --job-name=sig-eval
#SBATCH --partition=lrz-hgx-h100-94x4
#SBATCH --time=02:00:00
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --output=outputs/logs/eval_%j.log

source ~/nlp-css-seminar/scripts/activate_env.sh
cd ~/nlp-css-seminar
python scripts/run_evaluation.py --config config.yaml
```

Pattern for eval: single sbatch script starts vLLM in background, waits for `/health`, runs eval, stops server.

- `scancel <job-id>` — cancel job

### 7. Fallback: direct transformers

vLLM works on LRZ with the workarounds above. Keep `smoke_test_transformers.py` as a diagnostic if vLLM breaks after upgrades. Agents could temporarily use in-process HuggingFace inference only as a last resort.

### Setup checklist (Phase 0 gate)

- [x] GitHub SSH key on LRZ + added to GitHub account
- [x] `ssh -T git@github.com` succeeds
- [x] `~/nlp-css-seminar/` cloned; commits pushed to `origin/main`
- [x] SSH + tmux to LRZ working
- [x] Miniconda installed (`~/miniconda3/`)
- [x] Env `sig-llm` created
- [x] PyTorch sees GPU on compute node
- [x] Shared model path readable
- [x] `smoke_test_transformers.py` passes
- [x] vLLM installed (`vllm==0.23.0`)
- [x] `bash scripts/start_vllm.sh` → `Application startup complete`
- [x] `smoke_test_llm.py` returns a chat completion (`POST /v1/chat/completions` 200)

## Key resources to leverage

- Gold set: `data/gold_set.xlsx` (115 rows, all 22 basic concepts). Columns: `example_id, input_indicator, basic_concept, semantic_structure, assertion, question, answer_options, domain, source_type, confusable_with`.
- Annotation Guide in the protocol doc is the first draft of the Assertion Developer prompt: the 22 basic concepts (14 subjective + 8 objective), the 3 semantic structures, the per-concept structure-code table, the notation key, the 4 question formats, the 3 worked reference rows, and the confusable-concept heuristics. These get encoded directly into prompts and a `concepts` reference module.

## Project layout (`~/nlp-css-seminar/`)

### Exists today


| Path                                                   | Status                                                       |
| ------------------------------------------------------ | ------------------------------------------------------------ |
| `config.yaml`                                          | LLM + eval settings; `mock: false`, `enable_thinking: false` |
| `data/gold_set.xlsx`                                   | Gold set (115 rows)                                          |
| `data/concepts.yaml`                                   | 22 concepts, structures, notation                            |
| `src/sig/`                                             | Agents, pipeline, LLM client, loader, prompts, eval          |
| `run_test_pipeline.py`, `test_load.py`                 | Local test scripts                                           |
| `docs/PLAN.md`, `docs/BASELINE_REPORT.md`, `README.md` | Documentation                                                |
| `docs/baseline/`                                       | Committed eval summary JSON snapshots                        |
| `environment.yml`, `requirements*.txt`                 | Dependencies                                                 |
| `outputs/`                                             | Runtime eval CSV/JSON + `logs/` (logs gitignored)            |
| `scripts/activate_env.sh`, `setup_cuda_libs.sh`        | Conda + LRZ CUDA workaround                                  |
| `scripts/start_vllm.sh`                                | Interactive vLLM (working on H100)                           |
| `scripts/smoke_test_*.py`                              | Phase 0 smoke tests                                          |
| Protocol doc, LRZ tutorial PDF                         | Repo root                                                    |


### Still to build

- `src/sig/evaluation/judge.py` — LLM-as-judge (empty stub)
- Confusion matrix export, question-format metric, per-concept breakdown
- Spelling aliases in `normalize.py` (Behavior/Behaviour, judgment/judgement)
- Few-shot prompt tuning + concept output constraints
- Optional LoRA SFT on assertion developer
- `scripts/run_evaluation.sh` — sbatch wrapper for batch eval

## Evaluation design (from the protocol's criteria tables)

Primary mode is per-agent isolated evaluation (matches the doc: Question Developer is evaluated on gold assertions, not chained output).

Assertion Developer (input = gold `input_indicator`):

- Identification of basic concept (objective): accuracy of predicted vs gold `basic_concept` (normalized) + per-concept confusion matrix; `confusable_with` used for error analysis.
- Correct semantic structure (objective): predicted structure number + code matches gold (normalized via the per-concept code table).
- Concept-assertion alignment (rated 4/5 objective): LLM-as-judge 1-5 that the assertion faithfully represents the indicator.

Question Developer (input = gold `assertion`):

- Question format (objective): classify the generated question into one of the 4 formats (direct/indirect x interrogative/imperative) and record it.
- Assertion-question alignment (rated 4/5 objective): LLM-as-judge 1-5 that the question represents the assertion.

Report: overall accuracy, per-concept and per-structure breakdowns, mean judge scores, plus a per-row predictions-vs-gold table for manual spot-check.

## Decisions made:

- LLM-as-judge for the two alignment metrics, model configurable; default to a stronger local model (`Qwen2.5-72B-Instruct` is available on LRZ) to avoid self-grading bias. The 3 objective metrics need no judge.
- Agents return strict JSON (vLLM guided/JSON decoding) for robust parsing.
- Gold-set normalization layer rather than editing `data.xlsx`, so the source file is untouched.

## Implementation order

**Phase 0 — Infra: complete (2026-06-16)**

1. GitHub SSH auth + clone + push
2. Conda env `sig-llm` + PyTorch cu126 + vLLM 0.23
3. GPU access via `salloc` / `srun`
4. Transformers smoke test
5. vLLM server + API smoke test (LRZ CUDA workarounds)

**Phase 1 — Pipeline + baseline: complete (2026-06-20)**

1. ~~Scaffold, concepts, gold loader~~ done
2. ~~Agents + prompts + mock pipeline~~ done
3. ~~Connect to real vLLM + Qwen3.5 thinking fix~~ done
4. ~~Isolated eval + 115-row run + reports~~ done
5. Finish eval harness (judge, confusion matrix, question-format metric) — **in progress**
6. Prompt tuning + optional LoRA SFT — **next**
7. Full eval via sbatch — pending

## Open items to confirm with the team (not blockers)

- Which SLURM partition to use by default: general LRZ (`lrz-dgx-a100-94x4` / `lrz-hgx-h100-94x4`) vs MCML (`mcml-dgx-a100-40x8 -q mcml`). Tutorial shows both; we template general LRZ and note MCML flag.
- Whether Miniconda is already installed on your account — **yes**, at `~/miniconda3/`.
- Judge model: if running Qwen2.5-72B for LLM-as-judge, may need a second GPU job or a separate allocation.
- Indicator granularity question already flagged for Caro in the guide (single facet vs broad topic) only affects future test-data expansion, not this baseline.

