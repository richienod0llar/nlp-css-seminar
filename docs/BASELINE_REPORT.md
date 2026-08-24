# Prompting Baseline Report — Qwen3.5-9B (vLLM)

**Model:** Qwen3.5-9B (`/dss/dssmcmlfs01/pn25ju/pn25ju-dss-0000/models/Qwen3.5-9B`)  
**Server:** vLLM 0.23 on LRZ H100 (`scripts/start_vllm.sh`)  
**Gold set:** **113 rows** (`data/gold_set.xlsx`) — corrected 2026-08-24, see below  
**External judge:** **Qwen3-32B** (`scripts/start_vllm_judge.sh`) — replaces Qwen2.5-72B-Instruct  
**Config:** `mock: false`, `enable_thinking: false`, `temperature: 0.0`, `max_tokens: 1024`

Three full eval runs document **prompt engineering** (Runs 1–3). **Run 4** adds self-judge semantic scores. **Run 5** re-scores Run 4 with an external judge. **Run 6** applies structure prompt pass 2. **Run 7** is the review-response run: a three-arm prompt ablation, a replacement external judge, and a 2×2 generator×judge design, reaching **85.0% concept / 79.6% structure**.

> ### ⚠️ Gold-set correction (2026-08-24) — read before quoting any number
>
> The gold set was corrected from 115 to **113 items**, and one label was changed:
>
> 1. **Exact duplicates removed.** Ids 71 and 67 duplicate ids 5 and 29 — identical
>    indicator, concept *and* structure in both pairs. Id 71 is additionally one of the
>    16 items quoted verbatim in the v6 prompt, so keeping it double-counted a memorised
>    item in the headline accuracy.
> 2. **Evaluative-belief notation standardised.** Gold labelled three items of one concept
>    three different ways (`xPyc`, `xP(e)`, `xP(e)y`) while `concepts.yaml` licensed a
>    fourth pair. Standardised on the notation-derived `(e)` form, so id 3 became `xP(e)y`.
>    The model predicts `xPyc` for all three, so it is now scored **wrong on all three**.
>    Standardising the other way would have *raised* structure accuracy by ~1.7 pp by
>    moving gold toward what the prompt already teaches — which is why it was not done.
>
> **Every per-run section below reports the numbers as they were published at n=115.**
> They are kept as a changelog of what was reported at the time. The corrected n=113
> numbers — which are what the paper should cite — are in
> [Corrected results (n=113)](#corrected-results-n113) and in `docs/reanalysis.json`,
> which is the single source of truth. The `eval_summary_*.json` files in
> `docs/baseline/` are **stale at n=115**; do not quote them.
>
> Re-scoring is replayed offline by `src/sig/gold_fixes.py` — no run was repeated on a GPU.

## Run changelog — what changed between runs

All runs share unless noted:

- **Model:** Qwen3.5-9B via vLLM 0.23 on LRZ H100
- **Gold set:** 113 rows after the 2026-08-24 correction (115 in Runs 1–6 as published), **isolated eval** (assertion from indicator; question from gold assertion)
- **Config:** `mock: false`, `enable_thinking: false`, `temperature: 0.0`, `max_tokens: 1024`
- **Scoring:** exact match on concept/structure/question after `normalize.py`
- **Judge:** off in Runs 1–3; **self-judge (9B) in Run 4**; **external judge (Qwen2.5-72B) in Run 5**; **external judge (Qwen3-32B) + 2×2 generator×judge in Run 7** (the 72B was deleted from the shared store after Run 5)

Git commits: `1fdd4bf` → Run 1; `7fd51fa` → Run 2; `3485c2d` → Run 3/4 code.

---

### Run 1 — Initial baseline (`20260620_185119`)

**Purpose:** First full 115-row vLLM eval after infrastructure was working.

**Code state (commit `1fdd4bf` — “bug fixes before vLLM run”):**

| Area | What was in place |
|------|-------------------|
| **vLLM / JSON** | `enable_thinking: false`, `/no_think` suffix, `chat_template_kwargs`, separate `guided_json` schemas for assertion vs question |
| **Parsing** | `parse_json_response()` strips thinking text and extracts JSON substring |
| **Eval** | `run_eval.py` over all 115 rows; `evaluate_row()` isolated protocol |
| **Metrics** | Concept + structure exact match; `normalize.py` wired (lowercase, structure code regex) |
| **Prompts** | `assertion_developer.md` — 3 worked examples, 6 strict rules, dynamic `concepts.yaml` injection |
| **Agents** | Basic `Assertion_Developer` / `Question_Developer`; no concept enum constraint |

**Not yet present (added in Run 2+):**

- US/UK spelling unification in scoring (`Behavior` vs `Behaviour`)
- `guided_json` enum restricting `concept` to the 22 YAML names
- Disambiguation tables or extra few-shot examples in assertion prompt
- JSON repair for broken question responses
- Confusion matrices, per-concept breakdown, LLM-as-judge

**Observed issues driving later runs:**

- 9 rows failed concept match due to spelling only (`Behavior`/`Behaviour`, `judgment`/`judgement`)
- Frequent Preference ↔ Expectations of future events confusions
- Row 114 question JSON parse failure
- Structure accuracy lagged concept accuracy

---

### Run 2 — Prompt tuning (`20260620_194152`)

**Purpose:** Fix scoring aliases, constrain model concept output, and teach common concept confusions via prompt.

**Code changes (commit `7fd51fa` — “spelling normalization + concept constraint + one targeted prompt pass”):**

#### 1. Scoring — `src/sig/normalize.py`

- Added `_concept_key()` to unify **US/UK spelling** before comparison:
  - `Behavior` ↔ `Behaviour`
  - `Cognitive judgment` ↔ `Cognitive judgement`
- `match_concept()` and `concepts_match()` use this key

*Effect:* Re-scoring Run 1 CSV with Run 2 normalize would raise concept accuracy from **57.4% → ~65%** without re-running the model. Run 2’s reported **69.6%** is model improvement **plus** fairer scoring.

#### 2. Model constraint — `llm_client.py`, `agents.py`, `loader.py`

- `build_assertion_schema(valid_concepts)` adds **`enum`** on `concept` field in `guided_json` (22 names from `concepts.yaml`)
- `Assertion_Developer` loads concept names via `load_concept_names()` and passes them to vLLM
- Post-processing: `match_concept()` maps model output to canonical YAML name before storing prediction

*Effect:* Stops invented concept labels; forces pick from Caro’s taxonomy.

#### 3. Assertion prompt — `assertion_developer.md`

- Rule 1: use **exact** concept name as in YAML (e.g. `Behaviour`, `Cognitive judgement`)
- New section: **COMMONLY CONFUSED CONCEPTS** table (Evaluation vs Evaluative belief vs Expectation vs Preference vs Action tendencies vs Behaviour)
- Short structure hints (`xPRy` vs `xFD`, `vIi` vs `xIi`)
- **3 new worked examples:**
  - Example 4: *Expectations met* → Evaluative belief / `xPyc`
  - Example 5: *Desired improvement* → Preference / `xPRy`
  - Example 6: *Frequency of physical exercise* → Behaviour / `rDy`

**Unchanged from Run 1:** question prompt, JSON repair, structure-focused examples, judge, confusion export.

**Measured impact vs Run 1:** +12.2 pp concept, +4.3 pp structure. Largest gains: Behavior 0%→86%, Preference concept 40%→80%. Preference **structure** still weak at 40% (`xPRy` vs `xIpr`).

---

### Run 3 — Structure prompt (`20260625_134833`)

**Purpose:** Target structure-code errors (especially Preference `xPRy`), fix row 114 JSON, add richer eval exports.

**Code changes (commit `3485c2d` — judge/metrics/tooling + structure prompt):**

#### 1. Assertion prompt — `assertion_developer.md`

- Expanded **structure disambiguation** from bullet list to full table (`xPRy`, `xIpr`, `xFDy`, `xFD`, `rFDy`, `xPyc`, `rDy`, `xDy`, `xDpI`, `xFy`, etc.)
- Explicit rules:
  - **Preference → default `xPRy`** (not `xIpr`)
  - Action tendencies vs Expectations vs Behaviour vs Demographics
  - Events vs Behaviour (“experienced/witnessed” → Events)
- Concept table rows added for **Events** and **Place**
- **3 new worked examples:**
  - Example 7: *Preferred contact method* → Preference / `xPRy`
  - Example 8: *Expectation that economy will improve* → Expectations / `xFDy`
  - Example 9: *Experience or witnessing bullying* → Events / `xDy`

#### 2. Question JSON repair — `llm_client.py`

- `_repair_broken_question_json()` recovers `question`, `answer_options`, `question_format` when the model emits **invalid JSON** (options as separate quoted strings)
- Fixes **row 114** class of failures

#### 3. Question prompt — `question_developer.md`

- Rule 7: `answer_options` must be a **single JSON string** (comma-separated options inside one value)

#### 4. Eval harness (does not change model predictions except via JSON repair)

- `metrics.py`: `both_correct_pct`, per-concept/structure breakdown, confusion matrices, question-format distribution
- `run_eval.py`: exports `concept_confusion_*.csv`, `structure_confusion_*.csv`
- `judge.py`: LLM-as-judge implemented but **`run_judge: false`** for this run
- `scripts/analyze_eval.py`, `scripts/run_evaluation.sh` added

**Unchanged from Run 2:** spelling normalize, concept enum, core config, isolated eval protocol.

**Measured impact vs Run 2:** +6.1 pp concept, +6.9 pp structure, +7.8 pp both correct, question non-empty **100%**. Key win: Preference structure **40% → 90%**. Remaining gap: `xFD`/`xFy` structure codes often wrong even when concept is right.

---

### Run 4 — LLM-as-judge (`20260625_160020`)

**Purpose:** Add semantic alignment scores (1–5) without changing prompts or generations.

**Config change only:** `eval.run_judge: true`. Re-runs assertion + question agents, then calls `judge.py` twice per row (230 extra LLM calls).

**No changes to:** prompts, `normalize.py`, schemas, or temperature.

**Measured impact vs Run 3:** objective metrics **identical**; adds mean IA **4.51** and mean AQ **4.99** (self-judge, same model as generator).

---

### Run 5 — External judge (`20260703_171851`)

**Purpose:** Re-score Run 4 predictions with a **separate, stronger judge** to quantify self-grade bias. No pipeline rerun; no prompt changes.

**Setup:**

| Component | Value |
|-----------|--------|
| Judge model | Qwen2.5-72B-Instruct |
| Server | vLLM on port 8001, `tensor-parallel-size=2` (2× H100) |
| Input | Run 4 CSV (`eval_report_vllm_20260625_160020.csv`) |
| Script | `scripts/run_judge_only.py` (230 judge calls: IA + AQ per row) |

**Measured impact vs Run 4 self-judge:**

| Metric | Self (9B) | External (72B) | Δ |
|--------|-----------|----------------|---|
| Mean indicator→assertion | **4.51** | **4.09** | −0.42 |
| Mean assertion→question | **4.99** | **4.56** | −0.43 |
| IA score = 5 | 97 / 115 (84%) | 43 / 115 (37%) | — |
| AQ score = 5 | 114 / 115 (99%) | 64 / 115 (56%) | — |
| Rows with ext IA ≤ 2 | — | 5 / 115 | — |

Objective metrics unchanged: **75.7%** concept, **62.6%** structure, **18.3%** question exact match.

---

### Run 6 — Structure prompt pass 2 (`20260703_180434`)

**Purpose:** Target remaining structure-code errors (`xFD`, `xFy`, `xDpl`, `vIi`/`xIi`, `xDqu`, `xDti`) without fine-tuning.

**Code changes:**

#### 1. Assertion prompt — `assertion_developer.md`

- Corrected **Examples 2 & 8**: Action tendencies and Expectations use **`xFD`** (not `rFDy` / `xFDy`)
- Expanded structure disambiguation table; added rules for Feelings (`xFy`), Place/Procedures (`xDpl` / `xDpl, pro`), Quantities (`xDqu`), Time (`xDti`), Values vs Importance
- **7 new worked examples (10–16):** stress (`xFy`), country (`xDpl`), passport procedure, job security importance, societal values, household size, engagement duration
- Demographics phrasing guidance (factual status, not evaluative paraphrase)

#### 2. Concepts reference — `data/concepts.yaml`

- Synced allowed structure codes with gold set: Action tendencies + Expectations → `xFD`; Place/Procedures → `xDpl` / `xDpl, pro`; Values structure 3 → `xIi`

**Config:** `eval.run_judge: false` (objective metrics only). Smoke test `20260703_175707` (5 rows) then full 115-row run.

**Measured impact vs Run 4:**

| Metric | Run 4 | Run 6 | Δ |
|--------|-------|-------|---|
| Concept accuracy | 75.7% | **76.5%** | +0.9 pp |
| Structure accuracy | 62.6% | **75.7%** | **+13.0 pp** |
| Both correct | 60.9% | **73.9%** | +13.0 pp |
| Question non-empty | 100% | 100% | — |
| Question exact match | 18.3% | 17.4% | −0.9 pp |

**Structure codes fixed (27 rows that were wrong in Run 4):** all 8 `xFD` rows (except ID 19 concept error), 5/6 `xDpl`, 3/4 `xFy`, both `vIi`, both `xDti`, both `xDqu`, 3 Place rows, 4 Action tendencies intentions.

**New regressions (12 rows correct in Run 4, wrong in Run 6):** mainly **Norms** `o(H+I)y` → `vIi` (3 rows); plus scattered concept+structure slips (Evaluation, Preference, Causal relationship).

**Remaining structure errors:** 28/115. Hardest: Norms (0%), Evaluative belief `xP` (0%), Causal relationship (33%), Events (60%).

---

### Run 7 — Review response (`20260824`)

One SLURM allocation (`scripts/run7.sh`, job 5760085) covering every GPU-dependent fix the
paper review asked for. Three stages, seven output sets.

#### 1. Three-arm prompt ablation — one intervention each

| Arm | Prompt | Change isolated |
|-----|--------|-----------------|
| `v6repro` | `assertion_developer.md` | Run 6 prompt, repaired `concepts.yaml` — isolates the YAML fix |
| `v7a` | `assertion_developer_v7a.md` | Worked examples rewritten so **no gold item appears verbatim** — isolates leakage (W1) |
| `v7b` | `assertion_developer_v7b.md` | v7a **+ notation-derived Norms/Policies/Causal rule** — the targeted fix (W5) |

`assertion_developer.md` is deliberately **unchanged**, so Run 6 stays reproducible.

#### 2. External judge replaced — Qwen2.5-72B → Qwen3-32B

`Qwen2.5-72B-Instruct` was **deleted from the shared model store** after Run 5 and no
70B-class model remains anywhere in the project store. `Qwen3-32B` (65.5 GB, dense bf16,
17/17 shards) is the largest complete instruct model still on disk.

To keep the swap measurable rather than silent, Run 7 re-judges the **same Run 4 predictions**
the 72B scored, so both instruments can be compared on identical items. `--max-model-len` on
the judge server was raised 4096 → 8192 because Stage 2 also *generates* on that server and
the v7b prompt alone is 3573 tokens.

#### 3. 2×2 generator × judge design (W3)

The 32B also generates a full set, then both models judge both generation sets. This
separates *"a model prefers its own output"* from *"a bigger judge is simply stricter"* —
the two explanations Run 5 could not distinguish.

#### 4. Infrastructure fix

`stop_server` in `run7.sh` killed the wrapper `bash`, not `vllm serve` (the server scripts
pipe through `tee`). The orphaned server held ~90 GB and the next stage died with
`Free memory on device cuda:0 (3.87/93.09 GiB)`. Servers now start via `setsid` in their own
process group and are signalled as a group; the `sleep 20` drain guess was replaced with
`wait_gpu_free`, which polls until every GPU is below 5 GB and hard-fails with a process
listing. `RUN7_SKIP_STAGE1=1` added for resuming without repeating the 25-minute Stage 1.

---

### Summary: cumulative engineering vs metrics

| Layer | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 | Run 6 | Run 7 |
|-------|-------|-------|-------|-------|-------|-------|-------|
| vLLM JSON / thinking off | ✓ | | | | | | |
| Isolated eval harness | ✓ | | | | | | |
| Spelling-normalized scoring | | ✓ | | | | | |
| Concept `enum` in guided_json | | ✓ | | | | | |
| Concept disambiguation prompt | | ✓ | | | | | |
| Examples 4–6 (concepts) | | ✓ | | | | | |
| Structure disambiguation table | | | ✓ | | | | |
| Examples 7–9 (structures) | | | ✓ | | | | |
| Question JSON repair | | | ✓ | | | | |
| Confusion matrices / breakdown | | | ✓ | | | | |
| LLM-as-judge scoring | | | (code) | ✓ (self) | ✓ (ext) | | |
| Structure prompt pass 2 | | | | | | ✓ | |
| concepts.yaml gold alignment | | | | | | ✓ | |
| De-leaked worked examples (W1) | | | | | | | ✓ |
| Notation-derived deontic/causal rule | | | | | | | ✓ |
| Single-intervention ablation arms | | | | | | | ✓ |
| External judge → Qwen3-32B | | | | | | | ✓ |
| 2×2 generator × judge (W3) | | | | | | | ✓ |
| Gold-set correction (n=113) | | | | | | | ✓ |

| Metric | Run 1 | Run 2 | Run 3 | Run 4 | Run 6 | R1→R6 |
|--------|-------|-------|-------|-------|-------|--------|
| Concept accuracy | 57.4% | 69.6% | 75.7% | 75.7%* | **76.5%** | +19.1 pp |
| Structure accuracy | 51.3% | 55.7% | 62.6% | 62.6%* | **75.7%** | +24.4 pp |
| Both correct | 42.6% | 53.0% | 60.9% | 60.9%* | **73.9%** | +31.3 pp |
| Question non-empty | 99.1% | 99.1% | 100% | 100%* | 100% | +0.9 pp |
| Mean IA judge (1–5) | — | — | — | **4.51** (self) | — | — |
| Mean AQ judge (1–5) | — | — | — | **4.99** (self) | — | — |

| Metric | Run 5 (ext judge on Run 4 preds) |
|--------|----------------------------------|
| Mean IA judge (72B) | **4.09** |
| Mean AQ judge (72B) | **4.56** |
| Ext AQ score ≥ 4 | **100%** (115/115) |

\*Run 4 objective metrics match Run 3 (same generations; judge adds scoring only).

---

## Corrected results (n=113)

**These are the numbers to cite.** Every run re-scored on the corrected 113-item gold set
under today's normalizer, so all seven are directly comparable. Generated by
`python scripts/reanalysis.py` → `docs/reanalysis.json`.

| Run | Concept | Structure | Both correct | Question exact |
|-----|---------|-----------|--------------|----------------|
| Run 1 — Initial | 65.5% | 51.3% | 47.8% | 20.4% |
| Run 2 — Prompt tuning | 69.0% | 54.0% | 51.3% | 20.4% |
| Run 3 — Structure v1 | 75.2% | 61.1% | 59.3% | 18.6% |
| Run 6 — Structure v2 | 76.1% | 74.3% | 72.6% | 17.7% |
| Run 7a — `v6repro` | 78.8% | 76.1% | 74.3% | 20.4% |
| Run 7b — `v7a` (de-leaked) | 77.9% | 73.5% | 71.7% | 20.4% |
| **Run 7c — `v7b` (+notation rule)** | **85.0%** | **79.6%** | **79.6%** | 20.4% |

### Paired significance (exact McNemar, same items)

| Transition | Concept | Structure |
|------------|---------|-----------|
| Run 1 → Run 2 | b=8 c=12 **p=0.503** | b=7 c=10 p=0.629 |
| Run 2 → Run 3 | b=3 c=10 p=0.092 | b=3 c=11 p=0.057 |
| Run 3 → Run 6 | b=12 c=13 p=1.0 | b=12 c=27 **p=0.024** |
| Run 6 → v6repro | b=0 c=3 p=0.25 | b=1 c=3 p=0.625 |
| v6repro → v7a | b=2 c=1 p=1.0 | b=4 c=1 p=0.375 |
| **v7a → v7b** | b=2 c=10 **p=0.039** | b=2 c=9 p=0.065 |

Two results here matter more than the headline:

- **The Run 1 → Run 2 gain was mostly a scoring fix, not prompt engineering.** Re-scoring
  Run 1 under today's normalizer moves it from 57.5% to 65.5% — **8.0 pp of the 11.5 pp
  gain**. Once both runs are scored the same way the paired test is no longer significant
  (p=0.503, was p=0.013). The published Run 2 narrative overstates the prompt's contribution.
- **Only two transitions in the whole project are statistically significant**: the Run 3 → Run 6
  structure pass, and v7a → v7b. Everything else is within noise at n=113.

---

## Results at a glance

| Metric | Run 1 | Run 2 | Run 3 | Run 4 | Run 6 (**best**) | Δ (R4→R6) |
|--------|-------|-------|-------|-------|------------------|-----------|
| Concept accuracy | 57.4% | 69.6% | 75.7% | 75.7%* | **76.5%** (88/115) | +0.9 pp |
| Structure accuracy | 51.3% | 55.7% | 62.6% | 62.6%* | **75.7%** (87/115) | **+13.0 pp** |
| Both correct | 42.6% | 53.0% | 60.9% | 60.9%* | **73.9%** (85/115) | +13.0 pp |
| Question non-empty | 99.1% | 99.1% | 100% | 100%* | 100% | — |
| Question exact match | 20.0% | 20.0% | 18.3% | 18.3%* | 17.4% | −0.9 pp |
| Mean IA judge (1–5) | — | — | — | 4.51 (9B) | — | — |
| Mean AQ judge (72B, Run 5) | — | — | — | 4.56 | — | — |

| Run | Date | Timestamp | Artifacts |
|-----|------|-----------|-----------|
| 1 — Initial baseline | 2026-06-20 | `20260620_185119` | `docs/baseline/eval_*_20260620_185119.*` |
| 2 — Prompt tuning | 2026-06-20 | `20260620_194152` | `docs/baseline/eval_*_20260620_194152.*` |
| 3 — Structure prompt v1 | 2026-06-25 | `20260625_134833` | `docs/baseline/eval_*_20260625_134833.*` |
| 4 — Self-judge | 2026-06-25 | `20260625_160020` | `docs/baseline/eval_*_20260625_160020.*` |
| 5 — External judge (72B) | 2026-07-03 | `20260703_171851` | `docs/baseline/eval_*_ext_judge_20260703_171851.*` |
| 6 — Structure prompt v2 (**full eval report**) | 2026-07-03 | `20260703_180434` | `docs/baseline/eval_*_20260703_180434.*` |
| 7a — Ablation `v6repro` | 2026-08-24 | `v6repro_20260824_101855` | `docs/baseline/eval_*_vllm_v6repro_*.**` |
| 7b — Ablation `v7a` (de-leaked) | 2026-08-24 | `v7a_20260824_102619` | `docs/baseline/eval_*_vllm_v7a_*.*` |
| 7c — Ablation `v7b` (**best**) | 2026-08-24 | `v7b_20260824_103350` | `docs/baseline/eval_*_vllm_v7b_*.*` |
| 7 — 32B generations | 2026-08-24 | `gen32b_20260824_113423` | `docs/baseline/eval_*_vllm_gen32b_*.*` |
| 7 — External judge (32B) ×4 | 2026-08-24 | `20260824_11*` | `docs/baseline/eval_*_ext_judge_{run4_32b,run6,v7b,j32b_on_gen32b}_*.*` |
| 7 — Self-judge (9B) ×2 | 2026-08-24 | `20260824_1[15]*` | `docs/baseline/eval_*_ext_judge_j9b_on_gen{9b,32b}_*.*` |

\*Run 4 re-scores the same generations as Run 3; only judge columns are new.

Runtime copies also written to `outputs/` on each run. Run 3 also exports `concept_confusion_*.csv` and `structure_confusion_*.csv`.

## Evaluation protocol

Each gold row is scored in two independent stages (not chained):

1. **Assertion Developer** — input: `input_indicator` → predicted `basic_concept`, `semantic_structure`, `assertion`
2. **Question Developer** — input: gold `assertion` → predicted `question`, `answer_options`, `question_format`

Metrics are **exact match** after normalization (`src/sig/normalize.py`): lowercase, whitespace stripped; US/UK spelling unified (`Behavior`/`Behaviour`, `judgment`/`judgement`); structure codes extracted via regex (e.g. `xIe`, `xPRy`).

Question exact match compares normalized predicted vs gold question strings. **Run 4** adds self-judge (`judge.py`, 1–5 scale) using Qwen3.5-9B. **Run 5** re-scores the same predictions with Qwen2.5-72B via `scripts/run_judge_only.py` (see external judge caveat below). **Run 7** re-scores them again with Qwen3-32B, and adds the 2×2 generator×judge design.

---

## Run 1 — Initial baseline (20260620_185119)

First end-to-end **zero-shot prompting baseline** with thinking mode disabled.

| Metric | Result |
|--------|--------|
| Concept accuracy | 57.4% |
| Structure accuracy | 51.3% |
| Both correct | 42.6% |
| Question non-empty | 99.1% |

**Key issues:** Qwen3.5 thinking mode caused JSON failures before fix; 9 spelling-only concept errors; Preference ↔ Expectation confusions; row 114 JSON parse failure.

---

## Run 2 — Prompt tuning (20260620_194152)

Changes: spelling normalization, concept enum constraint, assertion prompt disambiguation table.

| Metric | Result |
|--------|--------|
| Concept accuracy | 69.6% |
| Structure accuracy | 55.7% |
| Both correct | 53.0% |
| Question non-empty | 99.1% |

**Gains vs Run 1:** +12.2 pp concept; Behavior 0%→86%; Preference concept 40%→80%. Structure lagged (+4.3 pp); Preference structure still 40% (`xPRy` vs `xIpr`).

---

## Run 3 — Structure prompt (20260625_134833)

Changes: structure disambiguation table and examples 7–9 in `assertion_developer.md`; JSON repair for malformed question responses; richer metrics export. `eval.run_judge: false`.

### Headline

| Metric | Result |
|--------|--------|
| Concept accuracy | **75.7%** |
| Structure accuracy | **62.6%** |
| Both correct | **60.9%** |
| Question non-empty | **100%** |
| Question exact match | 18.3% |
| Question format tagged | 100% (all "direct interrogative with WH word") |

### What improved (Run 2 → Run 3)

**Overall:** +6.1 pp concept, +6.9 pp structure, +7.8 pp both correct.

**Biggest win — Preference structure:** 40% → **90%** (concept also 80% → 90%). The `xPRy` default rule and structure examples fixed the main Run 2 gap.

**Other concept gains:**

| Concept | Run 2 | Run 3 |
|---------|-------|-------|
| Events | 0% | **60%** |
| Evaluative belief | 33% | **100%** |
| Demographics | 87% | **93%** |
| Evaluation | 85% | **80%** |

**Question stage:** Row 114 JSON repair worked — **115/115** non-empty questions (was 114/115). Exact match dipped slightly (23→21 rows); not meaningful without LLM-as-judge.

### Remaining weaknesses

**Concept (still hard):**

| Concept | n | Concept acc | Structure acc |
|---------|---|-------------|---------------|
| Policies | 3 | 0% | 67% |
| Place | 3 | 33% | 0% |
| Values | 3 | 33% | 0% |
| Time / Quantities | 3 each | 33% | 33% |
| Feelings | 4 | 50% | 0% |
| Cognitive judgment | 7 | 57% | 57% |

**Structure codes with 0% accuracy (despite correct concepts on some):**

| Code | n | Structure acc | Notes |
|------|---|---------------|-------|
| `xFD` | 8 | 0% | Expectations / Action tendencies — model picks wrong future-deed variant |
| `xFy` | 4 | 0% | Feelings structure |
| `xDpl` | 6 | 0% | Place / Procedures location codes |
| `vIi` | 2 | 0% | Values vs Importance (`xIi`) |

**Paradox rows:** Expectations of future events — **100% concept, 0% structure**; Action tendencies — **80% concept, 0% structure**. The model picks the right concept but wrong structure code within that concept.

### Cumulative progress (Run 1 → Run 3)

| Metric | Run 1 | Run 3 | Total gain |
|--------|-------|-------|------------|
| Concept accuracy | 57.4% | 75.7% | **+18.3 pp** |
| Structure accuracy | 51.3% | 62.6% | **+11.3 pp** |
| Both correct | 42.6% | 60.9% | **+18.3 pp** |
| Question non-empty | 99.1% | 100% | +0.9 pp |

Prompt engineering alone moved assertion accuracy from ~50% to ~76% concept / ~63% structure without fine-tuning.

---

## Run 4 — LLM-as-judge (`20260625_160020`)

**Purpose:** Semantic quality scoring on Run 3 outputs (same prompts, same temperature; **230 + 230 judge calls**).

**Config change only:** `eval.run_judge: true` in `config.yaml`. No prompt or model changes.

### Headline (objective metrics unchanged from Run 3)

| Metric | Result |
|--------|--------|
| Concept / structure / both correct | Same as Run 3 (75.7% / 62.6% / 60.9%) |
| Question non-empty | 100% |
| Question exact match | 18.3% |

### Judge scores (new)

| Metric | Result |
|--------|--------|
| **Indicator → assertion** (mean, 1–5) | **4.51** (median 5) |
| **Assertion → question** (mean, 1–5) | **4.99** (median 5) |
| Rows with IA score ≤ 2 | 18 / 115 |
| Rows with AQ score = 5 | 114 / 115 |
| Rows with AQ score = 4 | 1 / 115 |

**Score distributions:**

| IA score | Count | AQ score | Count |
|----------|-------|----------|-------|
| 1 | 2 | 4 | 1 |
| 2 | 16 | 5 | 114 |
| 5 | 97 | | |

### Key findings

**1. Question stage is strong semantically, not lexically.**

- Exact string match: **18.3%**
- Judge score ≥ 4: **99.1%** (114/115)
- **94** questions that are *not* exact matches still score ≥ 4 on assertion→question alignment
- Correlation exact match ↔ judge: **r ≈ 0.04** (no relationship)

*Conclusion:* For reporting, prefer judge alignment over exact match for the question developer.

**2. Assertion stage: high alignment but bimodal judge scores.**

- Mean IA **4.51/5** suggests assertions usually represent indicators well
- Yet only **75.7%** concept exact match — judge is more lenient than taxonomy matching
- When concept is **wrong** (n=28): mean IA **4.21**
- When concept is **right** (n=87): mean IA **4.61**
- **18 rows** scored IA ≤ 2 (including some with **correct** concept label — assertion wording or scope mismatch)

**Hardest concepts by mean IA score:** Causal relationship (2.0), Feelings (3.5), Procedures (3.7), Demographics (4.13), Cognitive judgment (4.14).

**3. Self-grading caveat (addressed in Run 5).**

Judge and generator are the **same model** (Qwen3.5-9B) in Run 4. Scores may be optimistic, especially for assertion→question (4.99/5). Run 5 external judge confirms this; see below.

**4. Objective vs semantic evaluation serve different roles.**

| Stage | Objective metric | Semantic (judge) | Interpretation |
|-------|------------------|------------------|----------------|
| Assertion | 75.7% concept | 4.51 IA | Taxonomy errors remain; assertions often still read as faithful paraphrases |
| Question | 18.3% exact | 4.99 AQ (self) | Wording differs from gold; meaning preserved |

---

## Run 5 — External judge (`20260703_171851`)

**Purpose:** Quantify self-grade bias by re-scoring Run 4 predictions with **Qwen2.5-72B-Instruct** (separate vLLM on port 8001, 2× H100). No changes to prompts, generations, or objective metrics.

### Headline

| Metric | Self-judge (9B, Run 4) | External judge (72B, Run 5) |
|--------|------------------------|-----------------------------|
| Mean indicator→assertion | **4.51** | **4.09** |
| Mean assertion→question | **4.99** | **4.56** |
| IA score = 5 | 97 / 115 (84%) | 43 / 115 (37%) |
| AQ score = 5 | 114 / 115 (99%) | 64 / 115 (56%) |
| AQ score ≥ 4 | 115 / 115 (100%) | **115 / 115 (100%)** |
| Rows with ext IA ≤ 2 | 18 (self) | **5** |

### External judge score distributions

| IA score (72B) | Count | AQ score (72B) | Count |
|----------------|-------|----------------|-------|
| 1 | 1 | 4 | 51 |
| 2 | 4 | 5 | 64 |
| 3 | 22 | | |
| 4 | 45 | | |
| 5 | 43 | | |

Self-judge IA was bimodal (97× score 5, 18× ≤2). External judge spreads scores across 3–5, with a more realistic median of **4** for IA.

### Key findings

**1. Self-grade bias confirmed, but conclusions largely hold.**

Both judge types drop ~0.43 points on average (IA and AQ). The 9B model was lenient when grading its own outputs. However, **external AQ remains 4.56/5** with **100% of rows ≥ 4**, so the Run 4 conclusion (question stage is strong semantically) survives external validation.

**2. Exact-match vs judge finding is robust to external judge.**

| Cohort | Mean ext AQ |
|--------|-------------|
| Exact question match (n=21) | 4.62 |
| Non-exact match (n=94) | 4.54 |
| Non-exact with ext AQ ≥ 4 | **94 / 94** |

Correlation self↔ext AQ: **r = 0.11** (self gave almost all 5s; external discriminates more). Correlation exact match ↔ ext AQ remains negligible.

**3. Assertion stage: external judge penalizes demographic phrasing.**

Largest self−ext gaps (self=5, ext=3) cluster on **Demographics** indicators even when the concept label is correct:

- *Living situation*, *Household composition*, *Employment status*, *Emergency contact phone number*

The 72B judge flags first-person paraphrases ("My employment status is…") as scope mismatches for factual demographic indicators, whereas the 9B self-judge rated them perfect.

**Worst external IA rows:**

| ID | Indicator | Ext IA | Self IA | Issue |
|----|-----------|--------|---------|-------|
| 59 | Medication details | 1 | 1 | Procedures → Demographics |
| 55 | Average stress level | 2 | 2 | Feelings, structure wrong |
| 57 | Medical conditions | 2 | 2 | Events → Demographics |
| 65 | Length of engagement | 2 | 5 | Time → Demographics; self over-rated |
| 70 | Areas for improvement | 2 | 2 | Evaluation → Preference |

**4. Concept correctness gap narrows under external judge.**

| Condition | Mean IA (self) | Mean IA (72B) |
|-----------|----------------|---------------|
| Concept wrong (n=28) | 4.21 | **3.89** |
| Concept correct (n=87) | 4.61 | **4.15** |

External judge penalizes wrong concepts more consistently. Self-judge still gave high IA scores to many taxonomy errors.

**Hardest concepts by external mean IA:** Procedures (3.00), Demographics (3.47), Behavior (3.57), Cognitive judgment (3.71).

**5. Correlation self ↔ external.**

| Pair | r |
|------|---|
| IA self vs ext | **0.52** |
| AQ self vs ext | **0.11** |

Moderate agreement on assertions; near-zero on questions because self-judge collapsed to 5.

### Figures

Run 5 figures: `fig12_self_vs_external_judge`, `fig13_ext_judge_distributions`, `fig14_exact_match_vs_ext_judge`.

---

## Run 6 — Structure prompt pass 2 (`20260703_180434`)

**Purpose:** Close the structure-code gap left after Run 3/4 without fine-tuning. Largest single-run gain in the project.

### Headline

| Metric | Run 4 | Run 6 | Δ |
|--------|-------|-------|---|
| Concept accuracy | 75.7% | **76.5%** | +0.9 pp |
| Structure accuracy | 62.6% | **75.7%** | **+13.0 pp** |
| Both correct | 60.9% | **73.9%** | +13.0 pp |
| Question non-empty | 100% | 100% | — |
| Question exact match | 18.3% | 17.4% | −0.9 pp |

### Structure code wins (Run 4 → Run 6)

| Code | Run 4 | Run 6 | Notes |
|------|-------|-------|-------|
| `xFD` | 0% (0/8) | **88%** (7/8) | Fixed repurchase, recommendation, follow-up, all 3 Expectations |
| `xDpl` | 0% (0/6) | **83%** (5/6) | Place + Procedures location/process |
| `xFy` | 0% (0/4) | **75%** (3/4) | Stress, belonging, work engagement |
| `xDti` | 0% (0/3) | **100%** (3/3) | Tenure, start year |
| `xDqu` | 0% (0/3) | **100%** (3/3) | Sleep hours, household size |
| `vIi` | 0% (0/2) | **100%** (2/2) | Societal values rows |

**27 rows** that had wrong structure in Run 4 are now correct. **12 rows** regressed (mostly Norms + concept confusions).

### Per-concept highlights

| Concept | Run 4 struct | Run 6 struct | Notes |
|---------|--------------|--------------|-------|
| Place | 0% | **100%** | `xDpl` examples fixed all 3 |
| Time | 33% | **100%** | `xDti` rule |
| Quantities | 33% | **100%** | `xDqu` rule |
| Expectations | 0% | **100%** | `xFD` direct future tense |
| Action tendencies | 0% | **80%** | 4/5; ID 19 still wrong concept |
| Feelings | 0% | **75%** | 3/4 |
| Norms | 100% | **0%** | **Regression:** all 3 → `vIi` instead of `o(H+I)y` |
| Policies | 67% | 67% | unchanged |
| Causal relationship | 33% | 33% | unchanged |

### Remaining errors (28 structure-wrong rows)

**By type:**

1. **Concept + structure both wrong** (majority): Evaluation↔Preference/Feelings, Events↔Demographics, Norms↔Values, Causal↔Cognitive judgment
2. **Concept right, structure wrong:** Evaluative belief `xP` vs `xPyc`/`xIc` (2 rows); Values `xIi` vs `vIi` (ID 4); Similarity `xIs` vs `xSy` (1 row)
3. **Norms structure:** model outputs `vIi` for all three "people should / ought to / should always" indicators

**Hardest remaining concepts:** Norms (0% concept, 0% structure), Policies (0% concept), Causal relationship (33%), Evaluative belief structure (33%).

### Key findings

**1. Structure pass 2 was the highest-leverage prompt change.**

Cumulative Run 1→Run 6: concept **+19.1 pp**, structure **+24.4 pp**, both correct **+31.3 pp**. Run 6 alone added more structure accuracy than Runs 1–3 combined.

**2. Fixing wrong teaching examples mattered.**

Run 3 Examples 2 and 8 taught `rFDy` and `xFDy`; gold labels use **`xFD`**. Aligning examples with gold + `concepts.yaml` resolved 7/8 `xFD` errors immediately.

**3. Trade-off: Norms regressed.**

Pass 2 strengthened Values/Importance (`vIi`/`xIi`) rules; the model now maps deontic "should/ought" indicators to Values (`vIi`) instead of Norms (`o(H+I)y`). A targeted Norms few-shot is the obvious Run 7 prompt fix.

**4. Question stage unchanged.**

100% non-empty; exact match ~17% (still not a quality signal; judge scores from Run 5 still apply to question semantics).

**5. LoRA is now optional, not urgent.**

**76% / 76%** objective accuracy from prompting alone exceeds the ~70% structure plateau threshold. Remaining gains likely need Norms/Policies/Causal few-shots or fine-tuning on rare concepts (n=3 each).

### Figures

Run 6 updates `fig01`–`fig07` (progression now includes Run 6; heatmaps/confusions from `20260703_180434`). Judge figures (`fig08`–`fig11`) remain from Run 4; external judge (`fig12`–`fig14`) from Run 5.

---

## Run 7 — Review response (`20260824`)

All numbers n=113 on the corrected gold set.

### Headline

| Metric | Run 6 | v6repro | v7a | **v7b** |
|--------|-------|---------|-----|---------|
| Concept accuracy | 76.1% | 78.8% | 77.9% | **85.0%** |
| Structure accuracy | 74.3% | 76.1% | 73.5% | **79.6%** |
| Both correct | 72.6% | 74.3% | 71.7% | **79.6%** |

### The ablation is surgical

v7b's gain lands almost entirely on the three concepts its rule was written to fix, and
**18 of 22 concepts are bit-identical between v7a and v7b**:

| Concept | n | v6repro | v7a | v7b |
|---------|---|---------|-----|-----|
| **Norms** | 3 | 33.3% | 0.0% | **100%** |
| **Policies** | 3 | 0.0% | 0.0% | **66.7%** |
| **Causal relationship** | 3 | 33.3% | 33.3% | **100%** |
| Evaluation | 20 | 80.0% | 80.0% | 90.0% |
| Preference | 10 | 80.0% | 90.0% | 80.0% |
| *18 others* | — | — | — | *unchanged* |

The arithmetic closes exactly: +3 Norms, +2 Policies, +2 Causal, +2 Evaluation, −1 Preference
= +8 items = the observed concept jump.

**State the caveat openly:** those three cells are **n=3 each**, so "100%" means 3/3 and the
effect rests on 7 items. The paired McNemar (p=0.039) is the defensible statistic, not the
per-cell percentages.

### Leakage (W1)

| Arm | Prompt | Gold items quoted verbatim | In-prompt | Held-out |
|-----|--------|---------------------------|-----------|----------|
| `v6repro` | `assertion_developer.md` | **15** | **100%** (15/15) | 75.5% (74/98) |
| `v7a` | `assertion_developer_v7a.md` | **0** | — | 77.9% |
| `v7b` | `assertion_developer_v7b.md` | **0** | — | 85.0% |

The leakage evidence is the **in-prompt vs held-out gap within `v6repro`** — a perfect 100% on
the memorised items against 75.5% on the rest. It is *not* the v7a drop: removing those
examples costs nothing statistically (p=1.0), which is a separate and useful finding — the
prompt was not depending on them.

### W3 — the self-judge is a degenerate instrument

2×2, mean indicator→assertion score:

| | judge 9B | judge 32B |
|---|---|---|
| **gen 9B** | 4.48 | 4.43 |
| **gen 32B** | 4.49 | 4.39 |

**No self-preference bias.** Each judge scores both generators almost identically; the 32B is
if anything *harsher* on its own output (−0.04). The variance is between judges, not
own-vs-other.

The means hide the real finding — the **distributions** do not:

| Judge / target | 1 | 2 | 3 | 4 | 5 | scored |
|---|---|---|---|---|---|---|
| 9B on gen9b | 2 | 16 | 0 | 1 | 91 | 110/113 |
| 32B on gen9b | 0 | 2 | 15 | 28 | 68 | 113/113 |

The 9B emits a 5 or a 2 and essentially nothing else — **zero 3s and one 4 across 113 items** —
and fails to return a parseable score on 3 items entirely. It is a binary pass/fail detector
wearing a 5-point scale. The 32B is unimodal and monotone. Report the *distribution*, not the
mean: the two means differ by 0.05 while the instruments are not comparable at all.

### The judge swap is measurable

Same 113 Run 4 predictions under both judges:

| Judge | 1 | 2 | 3 | 4 | 5 | mean |
|---|---|---|---|---|---|---|
| Qwen2.5-72B (Run 5) | 1 | 4 | 22 | 43 | 43 | 4.09 |
| Qwen3-32B (Run 7) | 0 | 1 | 12 | 28 | 72 | 4.51 |

Discrimination ordering is **72B > 32B > 9B**. The 32B is a valid instrument but more lenient
than the 72B was. **This gap cannot be decomposed** — the 72B no longer exists, so whether it
reflects scale, model family, or the fact that the 32B ran with thinking disabled is
unresolvable. Disclose it as a limitation.

### A bigger generator does not help

| Generator | Concept | Structure | Both |
|-----------|---------|-----------|------|
| Qwen3.5-9B (v7b prompt) | **85.0%** | **79.6%** | **79.6%** |
| Qwen3-32B (same prompt) | 77.0% | 68.1% | 68.1% |

The 32B is **worse** at the task despite 3.5× the parameters (McNemar p=0.064, so directional
rather than conclusive). Scale does not buy notation adherence — this is a framework-adherence
problem, not a capability problem. Useful support for the prompt-engineering approach.

### Remaining weaknesses

- **Structure is fully gated on concept.** P(structure correct | concept correct) = **93.8%**
  (90/96) vs **0.0%** (0/17) when the concept is wrong. Structure is never right when the
  concept is wrong, so concept errors cost twice.
- **Question exact match is flat at 20.4%** across every Run 7 arm — the prompt work does not
  touch it.
- **Question format is still degenerate**: 1 distinct value across all 113 items. It measures nothing.
- **Answer-option response-type agreement: 61.1%.**
- **The prompts now contradict the gold set.** `concepts.yaml` injects
  `Evaluative belief → xP(e)y,xP(e)`, but the hand-written tables in every assertion prompt
  still teach `xPyc` in four places. The prompts were **not** edited, because doing so would
  invalidate the Run 6 and Run 7 results. This is the natural next intervention (see below).

### No-LLM baselines (W6)

| Baseline | Concept | Structure |
|----------|---------|-----------|
| Majority class | 16.8% | — |
| Lexical 1-NN (TF-IDF, leave-one-out) | 32.7% | 31.0% |

v7b's 85.0% is well clear of both.

### Figures

`fig01`–`fig07` now include the three Run 7 arms and are computed on the corrected 113 items.
Judge figures (`fig08`–`fig11`) remain Run 4 self-judge; external-judge figures
(`fig12`–`fig14`) are regenerated from the **Qwen3-32B** re-judge of Run 4, so they remain
directly comparable to the Run 5 versions they replace.

---

## Interpretation

**Assertion stage:** Five prompt passes (Runs 1–3, 6, 7) brought concept accuracy to **85.0%**
and structure to **79.6%** without fine-tuning, on a de-leaked prompt and a corrected gold set.
The Run 7 notation rule closed the Norms/Policies/Causal gap that survived Run 6. Remaining
errors are dominated by **concept–structure coupling**: structure is never correct when the
concept is wrong.

**But the honest read is narrower than the trend line suggests.** Of six run-to-run
transitions, only two are statistically significant at n=113 (Run 3 → Run 6 structure,
p=0.024; v7a → v7b concept, p=0.039). The Run 1 → Run 2 "prompt tuning" gain is largely a
scoring-normalizer artifact (8.0 of 11.5 pp) and does not survive a paired test. The project's
real gains are the two structure/notation passes, not the accumulation of prompt edits.

**Question stage:** Coverage is solved (100%). Exact string match (20.4%) is misleading and
flat across every arm. Report judge alignment, and cite exact match only as a strict
automated baseline. Question *format* remains degenerate (1 distinct value) and should be
dropped as a metric or redefined.

**Evaluation strategy:** Report taxonomy exact-match (assertion) alongside external-judge
alignment (Qwen3-32B), and always report the judge's **score distribution**, not just its mean.
Run 7 showed two judges whose means differ by 0.05 while one uses four scale points and the
other effectively two.

**Scale is not the lever.** The 32B generator is *worse* than the 9B on the same prompt
(68.1% vs 79.6% both-correct). This is a framework-adherence task; prompt and notation work
dominate model size. LoRA remains optional and is not the highest-value next step.

## Recommended next steps

1. **v7c — align the prompt tables with the corrected notation.** `concepts.yaml` now injects
   `Evaluative belief → xP(e)y,xP(e)` while the hand-written tables still teach `xPyc` in four
   places. The model already produces `xPyc` with perfect consistency, so this is a 3-item
   (~2.7 pp structure) fix and the cheapest remaining win. Needs a GPU; do **not** edit the
   existing prompts in place — add `assertion_developer_v7c.md` so Runs 6 and 7 stay reproducible.
2. **A genuinely new test set (W1).** Nothing so far fully closes leakage: the *rules* in the
   prompt were still written while looking at these items. ~40 freshly annotated indicators
   would make this a real held-out set.
3. **Inter-annotator agreement (W7).** Two annotators on ~30 items gives a κ for §5.1.
4. **Human spot-check of the judge:** ~20 rows against expert ratings, now that the 32B is the
   instrument of record.
5. **Concept-error triage before more structure work** — structure accuracy is capped by
   concept accuracy (0% when concept is wrong), so concept errors are worth double.

## How to reproduce

```bash
# On LRZ compute node (vLLM running in another terminal)
cd ~/nlp-css-seminar
source scripts/activate_env.sh

# config.yaml: mock: false, eval.max_rows: null
python -m src.sig.evaluation.run_eval
```

Quick test (5 rows): set `eval.max_rows: 5` in `config.yaml`.

## Figures

Publication-quality plots (PDF + PNG) are generated from baseline artifacts:

```bash
python scripts/generate_figures.py            # defaults to v7b + the 32B judge
```

Figures are computed on the **corrected 113-item** gold set via `src/sig/gold_fixes.py`; the
`eval_summary_*.json` files are not used for accuracy figures because they are stale at n=115.
See `docs/figures/FIGURES.md` for the file list and suggested captions. Judge figures use
Run 4 (`--judge-run-id 20260625_160020`); external-judge figures use the Qwen3-32B re-judge.

Offline analysis (no GPU):

```bash
python scripts/analyze_eval.py docs/baseline/eval_report_vllm_20260703_180434.csv
```

With LLM-as-judge (Run 4, self):

```yaml
# config.yaml
eval:
  run_judge: true
```

External judge only (no pipeline rerun):

```bash
# Terminal 1: 2× GPU, start the Qwen3-32B judge server
bash scripts/start_vllm_judge.sh

# Terminal 2: re-score any prediction CSV
python scripts/run_judge_only.py docs/baseline/eval_report_vllm_20260625_160020.csv --tag run4_32b
```

### Run 7 in one allocation

```bash
sbatch scripts/run7.sh                    # 2 GPUs, 5 h, all three stages
RUN7_SKIP_STAGE1=1 bash scripts/run7.sh   # resume from the judge stage
```

Inside an existing `salloc`, `srun` onto the node **without `--overlap`** — an overlapping
step only sees one GPU and Stage 2 needs TP=2:

```bash
srun --jobid=<JOBID> --pty bash
```

### Offline re-analysis (no GPU) — the canonical numbers

```bash
python scripts/reanalysis.py              # writes docs/reanalysis.json
python scripts/reanalysis.py --self-check # asserts the statistics helpers
```
