# Prompting Baseline Report — Qwen3.5-9B (vLLM)

**Date:** 2026-06-20  
**Model:** Qwen3.5-9B (`/dss/dssmcmlfs01/pn25ju/pn25ju-dss-0000/models/Qwen3.5-9B`)  
**Server:** vLLM 0.23 on LRZ H100 (`scripts/start_vllm.sh`)  
**Gold set:** 115 rows (`data/gold_set.xlsx`)  
**Config:** `mock: false`, `enable_thinking: false`, `temperature: 0.0`, `max_tokens: 1024`

## Summary

First end-to-end **zero-shot prompting baseline** for Caro's two-agent survey item pipeline, evaluated in **isolated mode** (assertion from gold indicator; question from gold assertion).

| Metric | Result |
|--------|--------|
| Rows evaluated | 115 |
| Concept accuracy | **57.4%** (66/115) |
| Structure accuracy | **51.3%** (59/115) |
| Concept + structure both correct | **42.6%** (49/115) |
| Question non-empty | **99.1%** (114/115) |
| Question exact match | **20.0%** (23/115) |

**Artifacts (local run):**

- Per-row report: `outputs/eval_report_vllm_20260620_185119.csv`
- Summary JSON: `outputs/eval_summary_vllm_20260620_185119.json`
- Committed snapshot: `docs/baseline/eval_summary_vllm_20260620_185119.json`, `docs/baseline/eval_report_vllm_20260620_185119.csv`

## Evaluation protocol

Each gold row is scored in two independent stages (not chained):

1. **Assertion Developer** — input: `input_indicator` → predicted `basic_concept`, `semantic_structure`, `assertion`
2. **Question Developer** — input: gold `assertion` → predicted `question`, `answer_options`, `question_format`

Metrics are **exact match** after normalization (`src/sig/normalize.py`): lowercase, whitespace stripped; structure codes extracted via regex (e.g. `xIe`, `xPRy`).

Question exact match compares normalized predicted vs gold question strings. It does **not** measure semantic similarity (LLM-as-judge not yet implemented).

## Key findings

### Pipeline stability

After disabling Qwen3.5 thinking mode (`enable_thinking: false`, `/no_think`, `chat_template_kwargs`), JSON parsing is reliable:

- **0/115** rows with empty assertion fields
- **1/115** question-stage JSON parse failure (row 114: malformed `answer_options` string)

Earlier 5-row smoke runs without thinking disabled produced frequent "Thinking Process:" prose instead of JSON.

### Assertion stage (~50% accuracy)

The model often produces plausible assertions but mislabels the **taxonomy** (concept + structure code). Common error patterns:

**Spelling variants (counted as wrong, fixable in normalization):**

- `Behavior` → `Behaviour` (5 rows)
- `Cognitive judgment` → `Cognitive judgement` (4 rows)

Adjusting for these 9 rows would raise concept accuracy to **~65%** without re-running the model.

**Concept confusions (semantic):**

| Gold concept | Often predicted as |
|--------------|-------------------|
| Preference | Expectations of future events |
| Action tendencies | Preference |
| Values | Importance |
| Events | Feelings |

**Structure confusions:**

| Gold structure | Often predicted as |
|----------------|-------------------|
| `xPRy` (preference) | `xFD`, `xIpr` |
| `xFD` (future deed) | `xFDy`, `xIpr` |
| `vIi` (value/importance) | `xIi` (information) |
| `rDy` (deed frequency) | `rDqu` |

**Hardest concepts** (by concept accuracy on gold labels):

| Concept | n | Concept acc | Structure acc |
|---------|---|-------------|---------------|
| Behavior | 7 | 0% | 29% |
| Cognitive judgment | 7 | 0% | 57% |
| Policies | 3 | 0% | 67% |
| Action tendencies | 5 | 20% | 20% |

**Easiest concepts:**

| Concept | n | Concept acc | Structure acc |
|---------|---|-------------|---------------|
| Similarity relationship | 3 | 100% | 100% |
| Importance, Knowledge, Norms | 3 each | 100% | 100% |
| Demographics | 15 | 87% | 87% |
| Evaluation | 20 | 85% | 85% |

Demographics and Evaluation dominate the gold set and are learned reasonably well. Rare or confusable categories (Behavior, Cognitive judgment, Preference vs Expectation) drive most errors.

### Question stage (~99% coverage)

The question developer reliably turns gold assertions into survey items. Exact-match score (20%) understates quality: gold allows many valid paraphrases and response formats (rating scale vs open-ended).

Exact matches (23 rows) skew toward straightforward demographic and frequency items, e.g. employment status, income source, "how often do you buy shoes."

**Single failure (row 114):** model returned nearly-valid JSON but embedded answer options inside the string value, breaking the parser.

## Interpretation

This baseline establishes a **pre-fine-tuning reference point** for the prompt-driven pipeline:

- **Question generation** is largely solved at the coverage level; improvement needs semantic scoring (LLM-as-judge), not just exact string match.
- **Assertion taxonomy** is the main bottleneck; errors are concentrated in adjacent concept/structure pairs rather than total incoherence.
- **115 examples** is enough for evaluation but small for supervised fine-tuning; LoRA on the assertion stage is the most promising next training step.

## Recommended next steps

1. **Quick wins (no training):** spelling normalization, few-shot exemplars, constrain concept output to valid YAML list
2. **LLM-as-judge:** implement `judge.py` for concept-assertion and assertion-question alignment (1–5)
3. **Richer metrics:** per-concept confusion matrix, question-format classification
4. **LoRA SFT:** assertion developer only, train/val split (~90/25), re-run same eval protocol
5. **Batch eval:** `scripts/run_evaluation.sh` sbatch wrapper for unattended runs

## How to reproduce

```bash
# On LRZ compute node (vLLM running in another terminal)
cd ~/nlp-css-seminar
source scripts/activate_env.sh

# config.yaml: mock: false, eval.max_rows: null
python -m src.sig.evaluation.run_eval
```

Quick test (5 rows): set `eval.max_rows: 5` in `config.yaml`.
