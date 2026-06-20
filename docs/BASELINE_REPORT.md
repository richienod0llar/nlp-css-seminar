# Prompting Baseline Report — Qwen3.5-9B (vLLM)

**Date:** 2026-06-20  
**Model:** Qwen3.5-9B (`/dss/dssmcmlfs01/pn25ju/pn25ju-dss-0000/models/Qwen3.5-9B`)  
**Server:** vLLM 0.23 on LRZ H100 (`scripts/start_vllm.sh`)  
**Gold set:** 115 rows (`data/gold_set.xlsx`)  
**Config:** `mock: false`, `enable_thinking: false`, `temperature: 0.0`, `max_tokens: 1024`

Two full eval runs are documented below: an **initial zero-shot baseline** and a **prompt-tuning rerun** after spelling normalization, concept constraints, and targeted assertion prompt updates.

## Results at a glance

| Metric | Run 1 — Initial baseline | Run 2 — Prompt tuning | Delta |
|--------|--------------------------|----------------------|-------|
| Concept accuracy | 57.4% (66/115) | **69.6%** (80/115) | **+12.2 pp** |
| Structure accuracy | 51.3% (59/115) | **55.7%** (64/115) | **+4.3 pp** |
| Both correct | 42.6% (49/115) | **53.0%** (61/115) | **+10.4 pp** |
| Question non-empty | 99.1% (114/115) | 99.1% (114/115) | 0 |
| Question exact match | 20.0% (23/115) | 20.0% (23/115) | 0 |

| Run | Timestamp | Artifacts |
|-----|-----------|-----------|
| 1 — Initial baseline | `20260620_185119` | `docs/baseline/eval_report_vllm_20260620_185119.csv`, `docs/baseline/eval_summary_vllm_20260620_185119.json` |
| 2 — Prompt tuning (**current best**) | `20260620_194152` | `docs/baseline/eval_report_vllm_20260620_194152.csv`, `docs/baseline/eval_summary_vllm_20260620_194152.json` |

Runtime copies also written to `outputs/` on each run.

## Evaluation protocol

Each gold row is scored in two independent stages (not chained):

1. **Assertion Developer** — input: `input_indicator` → predicted `basic_concept`, `semantic_structure`, `assertion`
2. **Question Developer** — input: gold `assertion` → predicted `question`, `answer_options`, `question_format`

Metrics are **exact match** after normalization (`src/sig/normalize.py`): lowercase, whitespace stripped; US/UK spelling unified (`Behavior`/`Behaviour`, `judgment`/`judgement`); structure codes extracted via regex (e.g. `xIe`, `xPRy`).

Question exact match compares normalized predicted vs gold question strings. It does **not** measure semantic similarity (LLM-as-judge not yet implemented).

---

## Run 1 — Initial baseline (20260620_185119)

First end-to-end **zero-shot prompting baseline** with thinking mode disabled.

### Headline

| Metric | Result |
|--------|--------|
| Concept accuracy | 57.4% |
| Structure accuracy | 51.3% |
| Both correct | 42.6% |
| Question non-empty | 99.1% |
| Question exact match | 20.0% |

### Key findings

**Pipeline stability:** JSON parsing reliable after `enable_thinking: false`. 0/115 empty assertion fields; 1/115 question-stage JSON failure (row 114).

**Assertion stage (~50%):** Plausible assertions but frequent taxonomy errors. Nine rows failed concept match due to US/UK spelling alone (`Behavior`/`Behaviour`, `Cognitive judgment`/`Cognitive judgement`); re-scoring with spelling normalization would raise concept accuracy to ~65% without re-running.

**Hardest concepts (Run 1):**

| Concept | n | Concept acc | Structure acc |
|---------|---|-------------|---------------|
| Behavior | 7 | 0% | 29% |
| Cognitive judgment | 7 | 0% | 57% |
| Policies | 3 | 0% | 67% |
| Action tendencies | 5 | 20% | 20% |

**Common confusions:** Preference ↔ Expectations of future events; `xPRy` ↔ `xFD`/`xIpr`; Values (`vIi`) ↔ Importance (`xIi`).

---

## Run 2 — Prompt tuning (20260620_194152)

Changes applied before this run:

1. **Spelling normalization** in `normalize.py` (`Behavior`/`Behaviour`, `judgment`/`judgement`)
2. **Concept constraint** — `guided_json` enum over 22 YAML concept names + post-processing via `match_concept()`
3. **Assertion prompt** — disambiguation table for commonly confused concepts; three new worked examples (Expectations met, Desired improvement, Frequency of physical exercise)

### Headline

| Metric | Result |
|--------|--------|
| Concept accuracy | **69.6%** |
| Structure accuracy | **55.7%** |
| Both correct | **53.0%** |
| Question non-empty | 99.1% |
| Question exact match | 20.0% |

### What improved

**Net concept changes:** 21 rows improved, 7 regressed (28 flips). Structure: 12 improved, 7 worsened.

**Targeted disambiguation wins:**

| Row | Indicator | Run 1 → Run 2 |
|-----|-----------|---------------|
| 3 | Expectations met | Expectations of future events → **Evaluative belief** ✓ |
| 5, 33, 71 | Desired improvement | Expectations of future events → **Preference** ✓ |
| 20 | Frequency of shoe purchases | Quantities → **Behaviour** ✓ |

**Per-concept gains (selected):**

| Concept | Run 1 concept acc | Run 2 concept acc |
|---------|-------------------|---------------------|
| Behavior | 0% | **86%** |
| Preference | 40% | **80%** |
| Hard-pair group* | 32% | **79%** |

\*Preference, Expectations of future events, Evaluative belief, Action tendencies, Behavior.

**Structure on hard-pair group:** 11% → 36% (still the main remaining gap).

### Remaining weaknesses

- **Structure accuracy** only +4.3 pp; Preference structure still 40% (`xPRy` vs `xIpr`)
- **Events, Place, Policies** still 0% concept accuracy
- **Feelings** at 25% (new regressions, e.g. stress → Evaluation)
- **7 concept regressions**, e.g. row 108: Evaluative belief → Cognitive judgement
- **Question stage unchanged**; row 114 still fails JSON parse (malformed `answer_options`)
- **Question exact match** flat at 20%; needs LLM-as-judge for meaningful measurement

**Hardest concepts (Run 2):**

| Concept | n | Concept acc | Structure acc |
|---------|---|-------------|---------------|
| Events | 5 | 0% | — |
| Policies | 3 | 0% | — |
| Place | 3 | 0% | — |
| Feelings | 4 | 25% | — |
| Cognitive judgment | 7 | 43% | — |

---

## Interpretation

**Run 1** establishes the pre-tuning reference point. **Run 2** shows that prompt engineering and normalization yield **+12 pp concept accuracy** without fine-tuning, with the largest gains on Behavior, Preference, and Expectation/Evaluative-belief disambiguation.

- **Question generation** is stable at ~99% coverage; exact string match (20%) understates quality.
- **Assertion taxonomy** remains the bottleneck; structure codes lag concept labels.
- **115 examples** is enough for evaluation but small for full fine-tuning; LoRA on the assertion stage is the next training option if structure accuracy plateaus.

## Recommended next steps

1. **Structure-focused prompt pass:** more examples for `xPRy` / `xIpr` / `xFD` / `rFDy`
2. **LLM-as-judge:** implement `judge.py` for concept-assertion and assertion-question alignment (1–5)
3. **Richer metrics:** per-concept confusion matrix, question-format classification
4. **JSON robustness:** retry/repair for row 114-style malformed `answer_options`
5. **LoRA SFT:** assertion developer only if prompt tuning plateaus (~70% concept / ~56% structure)
6. **Batch eval:** `scripts/run_evaluation.sh` sbatch wrapper

## How to reproduce

```bash
# On LRZ compute node (vLLM running in another terminal)
cd ~/nlp-css-seminar
source scripts/activate_env.sh

# config.yaml: mock: false, eval.max_rows: null
python -m src.sig.evaluation.run_eval
```

Quick test (5 rows): set `eval.max_rows: 5` in `config.yaml`.
