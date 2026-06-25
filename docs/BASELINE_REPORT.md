# Prompting Baseline Report — Qwen3.5-9B (vLLM)

**Model:** Qwen3.5-9B (`/dss/dssmcmlfs01/pn25ju/pn25ju-dss-0000/models/Qwen3.5-9B`)  
**Server:** vLLM 0.23 on LRZ H100 (`scripts/start_vllm.sh`)  
**Gold set:** 115 rows (`data/gold_set.xlsx`)  
**Config:** `mock: false`, `enable_thinking: false`, `temperature: 0.0`, `max_tokens: 1024`

Three full eval runs are documented: **initial zero-shot baseline**, **prompt tuning** (spelling + concept constraint), and **structure prompt pass** (current best).

## Run changelog — what changed between runs

All three runs share the same setup unless noted below:

- **Model:** Qwen3.5-9B via vLLM 0.23 on LRZ H100
- **Gold set:** 115 rows, **isolated eval** (assertion from indicator; question from gold assertion)
- **Config:** `mock: false`, `enable_thinking: false`, `temperature: 0.0`, `max_tokens: 1024`
- **Scoring:** exact match on concept/structure/question after `normalize.py` (as of each run’s code version)
- **Judge:** not used in any of the three runs (`eval.run_judge: false`)

Git commits bracketing each run: `1fdd4bf` → Run 1; `7fd51fa` → Run 2; `3485c2d` → Run 3.

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

### Summary: cumulative engineering vs metrics

| Layer | Run 1 | Run 2 added | Run 3 added |
|-------|-------|-------------|-------------|
| vLLM JSON / thinking off | ✓ | | |
| Isolated 115-row eval | ✓ | | |
| Spelling-normalized scoring | | ✓ | |
| Concept `enum` in guided_json | | ✓ | |
| Concept disambiguation prompt | | ✓ | |
| Examples 4–6 (concepts) | | ✓ | |
| Structure disambiguation table | | | ✓ |
| Examples 7–9 (structures) | | | ✓ |
| Question JSON repair | | | ✓ |
| Confusion matrices / breakdown | | | ✓ |
| LLM-as-judge (scoring only) | | | (code only, not run) |

| Metric | Run 1 | Run 2 | Run 3 | R1→R3 |
|--------|-------|-------|-------|--------|
| Concept accuracy | 57.4% | 69.6% | 75.7% | +18.3 pp |
| Structure accuracy | 51.3% | 55.7% | 62.6% | +11.3 pp |
| Both correct | 42.6% | 53.0% | 60.9% | +18.3 pp |
| Question non-empty | 99.1% | 99.1% | 100% | +0.9 pp |

---

## Results at a glance

| Metric | Run 1 — Initial | Run 2 — Prompt tuning | Run 3 — Structure prompt | Δ (R2→R3) |
|--------|-----------------|----------------------|--------------------------|-----------|
| Concept accuracy | 57.4% (66/115) | 69.6% (80/115) | **75.7%** (87/115) | **+6.1 pp** |
| Structure accuracy | 51.3% (59/115) | 55.7% (64/115) | **62.6%** (72/115) | **+6.9 pp** |
| Both correct | 42.6% (49/115) | 53.0% (61/115) | **60.9%** (70/115) | **+7.8 pp** |
| Question non-empty | 99.1% (114/115) | 99.1% (114/115) | **100%** (115/115) | **+0.9 pp** |
| Question exact match | 20.0% (23/115) | 20.0% (23/115) | 18.3% (21/115) | −1.7 pp |

| Run | Date | Timestamp | Artifacts |
|-----|------|-----------|-----------|
| 1 — Initial baseline | 2026-06-20 | `20260620_185119` | `docs/baseline/eval_*_20260620_185119.*` |
| 2 — Prompt tuning | 2026-06-20 | `20260620_194152` | `docs/baseline/eval_*_20260620_194152.*` |
| 3 — Structure prompt (**current best**) | 2026-06-25 | `20260625_134833` | `docs/baseline/eval_*_20260625_134833.*` |

Runtime copies also written to `outputs/` on each run. Run 3 also exports `concept_confusion_*.csv` and `structure_confusion_*.csv`.

## Evaluation protocol

Each gold row is scored in two independent stages (not chained):

1. **Assertion Developer** — input: `input_indicator` → predicted `basic_concept`, `semantic_structure`, `assertion`
2. **Question Developer** — input: gold `assertion` → predicted `question`, `answer_options`, `question_format`

Metrics are **exact match** after normalization (`src/sig/normalize.py`): lowercase, whitespace stripped; US/UK spelling unified (`Behavior`/`Behaviour`, `judgment`/`judgement`); structure codes extracted via regex (e.g. `xIe`, `xPRy`).

Question exact match compares normalized predicted vs gold question strings. LLM-as-judge is implemented (`judge.py`) but was **not** used in Run 3 (`eval.run_judge: false`).

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

## Interpretation

**Assertion stage:** Three prompt passes yielded steady gains. Concept labeling is now reasonable on frequent categories (Demographics, Evaluation, Preference). Remaining errors concentrate on rare concepts (Policies, Place, Values) and **fine-grained structure codes** within correctly chosen concepts (`xFD` vs `xFDy`, `xFy`, `vIi` vs `xIi`).

**Question stage:** Coverage is solved (100%). Exact string match (~18%) is a weak quality signal; semantic evaluation via LLM-as-judge is the next step.

**Fine-tuning decision:** Prompt tuning is not yet plateaued for concepts (+18 pp total) but structure gains are slowing on hard codes. LoRA on the assertion stage is worth considering if structure accuracy stalls after a targeted `xFD`/`xFy` prompt pass.

## Recommended next steps

1. **Run with LLM-as-judge:** set `eval.run_judge: true`, re-run eval (~345 LLM calls)
2. **Structure prompt pass 2:** target `xFD`/`xFDy`, `xFy`, `vIi`, Place/Procedures (`xDpI`)
3. **Error analysis:** review `concept_confusion_*.csv` and `structure_confusion_*.csv` from Run 3
4. **LoRA SFT:** assertion developer if structure plateaus below ~70%
5. **Report for Caro:** share Run 3 summary + per-concept table from `eval_summary_*.json`

## How to reproduce

```bash
# On LRZ compute node (vLLM running in another terminal)
cd ~/nlp-css-seminar
source scripts/activate_env.sh

# config.yaml: mock: false, eval.max_rows: null
python -m src.sig.evaluation.run_eval
```

Quick test (5 rows): set `eval.max_rows: 5` in `config.yaml`.

Offline analysis (no GPU):

```bash
python scripts/analyze_eval.py docs/baseline/eval_report_vllm_20260625_134833.csv
```

With LLM-as-judge:

```yaml
# config.yaml
eval:
  run_judge: true
```
