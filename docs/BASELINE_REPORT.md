# Prompting Baseline Report — Qwen3.5-9B (vLLM)

**Model:** Qwen3.5-9B (`/dss/dssmcmlfs01/pn25ju/pn25ju-dss-0000/models/Qwen3.5-9B`)  
**Server:** vLLM 0.23 on LRZ H100 (`scripts/start_vllm.sh`)  
**Gold set:** 115 rows (`data/gold_set.xlsx`)  
**Config:** `mock: false`, `enable_thinking: false`, `temperature: 0.0`, `max_tokens: 1024`

Three full eval runs document **prompt engineering** (Runs 1–3). **Run 4** adds self-judge semantic scores on Run 3 outputs. **Run 5** re-scores the same predictions with an external judge (Qwen2.5-72B).

## Run changelog — what changed between runs

All runs share unless noted:

- **Model:** Qwen3.5-9B via vLLM 0.23 on LRZ H100
- **Gold set:** 115 rows, **isolated eval** (assertion from indicator; question from gold assertion)
- **Config:** `mock: false`, `enable_thinking: false`, `temperature: 0.0`, `max_tokens: 1024`
- **Scoring:** exact match on concept/structure/question after `normalize.py`
- **Judge:** off in Runs 1–3; **self-judge (9B) in Run 4**; **external judge (72B) in Run 5** on Run 4 predictions

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

### Summary: cumulative engineering vs metrics

| Layer | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
|-------|-------|-------|-------|-------|-------|
| vLLM JSON / thinking off | ✓ | | | | |
| Isolated 115-row eval | ✓ | | | | |
| Spelling-normalized scoring | | ✓ | | | |
| Concept `enum` in guided_json | | ✓ | | | |
| Concept disambiguation prompt | | ✓ | | | |
| Examples 4–6 (concepts) | | ✓ | | | |
| Structure disambiguation table | | | ✓ | | |
| Examples 7–9 (structures) | | | ✓ | | |
| Question JSON repair | | | ✓ | | |
| Confusion matrices / breakdown | | | ✓ | | |
| LLM-as-judge scoring | | | (code) | ✓ (self) | ✓ (ext) |

| Metric | Run 1 | Run 2 | Run 3 | Run 4 | R1→R3 |
|--------|-------|-------|-------|-------|--------|
| Concept accuracy | 57.4% | 69.6% | 75.7% | 75.7%* | +18.3 pp |
| Structure accuracy | 51.3% | 55.7% | 62.6% | 62.6%* | +11.3 pp |
| Both correct | 42.6% | 53.0% | 60.9% | 60.9%* | +18.3 pp |
| Question non-empty | 99.1% | 99.1% | 100% | 100%* | +0.9 pp |
| Mean IA judge (1–5) | — | — | — | **4.51** (self) | — |
| Mean AQ judge (1–5) | — | — | — | **4.99** (self) | — |

| Metric | Run 5 (ext judge) |
|--------|-------------------|
| Mean IA judge (72B) | **4.09** |
| Mean AQ judge (72B) | **4.56** |
| Ext AQ score ≥ 4 | **100%** (115/115) |
| Non-exact Q with ext AQ ≥ 4 | **94/94** |

\*Run 4 objective metrics match Run 3 (same model outputs; judge adds 2 scoring calls per row).

---

## Results at a glance

| Metric | Run 1 — Initial | Run 2 — Prompt tuning | Run 3 — Structure prompt | Run 4 — Self judge | Run 5 — Ext judge | Δ (R2→R3) |
|--------|-----------------|----------------------|--------------------------|-------------------|-------------------|-----------|
| Concept accuracy | 57.4% (66/115) | 69.6% (80/115) | **75.7%** (87/115) | 75.7%* | 75.7%* | **+6.1 pp** |
| Structure accuracy | 51.3% (59/115) | 55.7% (64/115) | **62.6%** (72/115) | 62.6%* | 62.6%* | **+6.9 pp** |
| Both correct | 42.6% (49/115) | 53.0% (61/115) | **60.9%** (70/115) | 60.9%* | 60.9%* | **+7.8 pp** |
| Question non-empty | 99.1% (114/115) | 99.1% (114/115) | **100%** (115/115) | 100%* | 100%* | **+0.9 pp** |
| Question exact match | 20.0% (23/115) | 20.0% (23/115) | 18.3% (21/115) | 18.3%* | 18.3%* | −1.7 pp |
| Mean IA judge (1–5) | — | — | — | **4.51** (9B) | **4.09** (72B) | — |
| Mean AQ judge (1–5) | — | — | — | **4.99** (9B) | **4.56** (72B) | — |

| Run | Date | Timestamp | Artifacts |
|-----|------|-----------|-----------|
| 1 — Initial baseline | 2026-06-20 | `20260620_185119` | `docs/baseline/eval_*_20260620_185119.*` |
| 2 — Prompt tuning | 2026-06-20 | `20260620_194152` | `docs/baseline/eval_*_20260620_194152.*` |
| 3 — Structure prompt | 2026-06-25 | `20260625_134833` | `docs/baseline/eval_*_20260625_134833.*` |
| 4 — Self-judge (**full eval report**) | 2026-06-25 | `20260625_160020` | `docs/baseline/eval_*_20260625_160020.*` |
| 5 — External judge (72B, judge-only) | 2026-07-03 | `20260703_171851` | `docs/baseline/eval_*_ext_judge_20260703_171851.*` |

\*Run 4 re-scores the same generations as Run 3; only judge columns are new.

Runtime copies also written to `outputs/` on each run. Run 3 also exports `concept_confusion_*.csv` and `structure_confusion_*.csv`.

## Evaluation protocol

Each gold row is scored in two independent stages (not chained):

1. **Assertion Developer** — input: `input_indicator` → predicted `basic_concept`, `semantic_structure`, `assertion`
2. **Question Developer** — input: gold `assertion` → predicted `question`, `answer_options`, `question_format`

Metrics are **exact match** after normalization (`src/sig/normalize.py`): lowercase, whitespace stripped; US/UK spelling unified (`Behavior`/`Behaviour`, `judgment`/`judgement`); structure codes extracted via regex (e.g. `xIe`, `xPRy`).

Question exact match compares normalized predicted vs gold question strings. **Run 4** adds self-judge (`judge.py`, 1–5 scale) using Qwen3.5-9B. **Run 5** re-scores the same predictions with Qwen2.5-72B via `scripts/run_judge_only.py` (see external judge caveat below).

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

## Interpretation

**Assertion stage:** Three prompt passes yielded steady gains. Concept labeling is now reasonable on frequent categories (Demographics, Evaluation, Preference). Remaining errors concentrate on rare concepts (Policies, Place, Values) and **fine-grained structure codes** within correctly chosen concepts (`xFD` vs `xFDy`, `xFy`, `vIi` vs `xIi`).

**Question stage:** Coverage is solved (100%). Exact string match (~18%) is misleading. **Run 4 self-judge** showed 4.99/5; **Run 5 external judge** confirms strong alignment at **4.56/5** with **100% ≥ 4**. Report external judge scores in the paper; cite exact match only as a strict automated baseline.

**Evaluation strategy:** Report **both** taxonomy exact-match (assertion) and LLM-as-judge alignment. Use **external judge (72B)** as the primary semantic metric; self-judge (9B) scores are included for comparison only.

**Fine-tuning decision:** Prompt tuning reached **76% concept / 63% structure** objectively. LoRA on the assertion stage targets taxonomy/structure codes (`xFD`, rare concepts) and demographic phrasing, not question generation.

## Recommended next steps

1. **Structure prompt pass 2:** target `xFD`/`xFDy`, `xFy`, `vIi`, Place/Procedures (`xDpI`)
2. **Demographics assertion phrasing:** reduce first-person scope errors flagged by external judge
3. **LoRA SFT:** assertion developer if structure plateaus below ~70%
4. **Human spot-check:** ~20 rows to validate 72B judge against expert ratings

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
python scripts/generate_figures.py --run-id 20260625_160020
```

See `docs/figures/FIGURES.md` for file list and suggested captions (includes judge figures `fig08`–`fig11`).

Offline analysis (no GPU):

```bash
python scripts/analyze_eval.py docs/baseline/eval_report_vllm_20260625_160020.csv
```

With LLM-as-judge (Run 4, self):

```yaml
# config.yaml
eval:
  run_judge: true
```

External judge only (Run 5, no pipeline rerun):

```bash
# Terminal 1: 2× GPU, start 72B judge server
bash scripts/start_vllm_judge.sh

# Terminal 2: re-score Run 4 CSV
python scripts/run_judge_only.py docs/baseline/eval_report_vllm_20260625_160020.csv
```

Or batch: `sbatch scripts/run_external_judge.sh`
