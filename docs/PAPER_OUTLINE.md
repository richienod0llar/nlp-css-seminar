# Annotated Outline: Prompt-Engineered LLMs for Framework-Grounded Survey Item Generation

**Target:** ~15 pp IEEE double-column (incl. refs + appendix). Body ~10.5 pp, refs ~1.5 pp, appendix ~3 pp.
**Scope:** as-is (Runs 1-6; external judge on Run 4 predictions). No new experiments.
**Positioning:** novel research contribution (methods + findings emphasis).
**Authors:** placeholders (`1st Given Name Surname`, LMU placeholder).
**Deliverable status:** outline for review; `.tex` draft to follow after approval.

`[CITE: ...]` marks a real reference to be sourced later (none invented).
`[CONFIRM ...]` marks a fact to verify before drafting prose.

---

## What the project is (reference summary)

A prompt-driven, two-agent LLM pipeline that automates survey-item construction from a
linguistic framework (basic concept -> assertion -> request-for-answer three-step method),
evaluated against a hand-built gold set (115 rows as published; **113 after the 2026-08-24
correction** — two exact duplicates removed, one notation standardised).

- **Framework:** 22 basic concepts (14 subjective / 8 objective), 3 semantic structures, a
  structure-code notation (e.g. `xIe`, `xFD`, `xPRy`), 5 question formats. Encoded in
  `data/concepts.yaml`, injected dynamically into prompts.
- **Pipeline:** `Assertion_Developer` (indicator -> concept + structure code + assertion) and
  `Question_Developer` (assertion -> question + options + format). Both Qwen3.5-9B via a vLLM
  OpenAI-compatible server on an LRZ H100, with guided JSON decoding, concept `enum` constraint,
  and JSON-repair fallbacks.
- **Data:** 113 rows (was 115), 22 concepts, ~40 domains. See `src/sig/gold_fixes.py`.
- **Evaluation:** isolated per-agent protocol (question developer scored on gold assertions).
  Objective = normalized exact match on concept + structure; semantic = LLM-as-judge 1-5
  (self 9B; external Qwen2.5-72B in Run 5, **Qwen3-32B from Run 7**). Per-concept/per-structure
  breakdowns, confusion matrices, question-format distribution, plus a 2x2 generator x judge design.
- **Result arc (n=113):** 7 prompt-engineering runs (no fine-tuning) moved the assertion stage
  from 65.5%/51.3% (concept/structure) to **85.0%/79.6%**, both-correct 47.8% -> **79.6%**.
  The external judge confirms the question stage is strong semantically despite ~20% exact string
  match. 15 publication figures exist as PDF + PNG.
- **Two results that reframe the arc, and must not be buried:** (1) only **two** of six run-to-run
  transitions are statistically significant at n=113 (Run 3 -> Run 6 structure p=0.024;
  v7a -> v7b concept p=0.039) — the Run 1 -> Run 2 "prompt tuning" gain is mostly a scoring-normalizer
  artifact (8.0 of 11.5 pp) and does not survive a paired test; (2) the self-judge is a **degenerate
  instrument** — the 9B emits a 5 or a 2 and almost nothing else (zero 3s, one 4, across 113 items).
  There is **no self-preference bias**; the variance is between judges, not own-vs-other.

---

## Front matter (~0.5 pp)

- **Title** (working): *Prompt-Engineered Large Language Models for Framework-Grounded Survey
  Item Generation: A Baseline and Dual Evaluation.*
- **Abstract** (~200 words): problem, two-agent pipeline, 22-concept framework, 113-row gold set,
  dual objective + judge evaluation, headline results (65.5 -> **85.0%** concept, 51.3 -> **79.6%**
  structure via prompting alone), key findings (exact match understates quality; the small
  self-judge does not use the rating scale; a 3.5x larger generator is *worse* at the task).
- **Keywords:** survey methodology, large language models, prompt engineering, question
  generation, LLM-as-judge, computational social science.

## I. Introduction (~1 pp)

- Motivation: manual survey-item design is expert-intensive, slow, and inconsistent; CSS needs
  scalable, theory-consistent item generation.
- The three-step design method (concept -> assertion -> request-for-answer) as the theoretical
  backbone. `[CITE: Saris & Gallhofer three-step method]`
- Research question: how far does prompt engineering alone (no fine-tuning) take an open-weight
  LLM on framework-faithful item generation?
- **Contributions** (explicit bullet list):
  1. Reproducible two-agent pipeline operationalizing the framework with constrained JSON decoding.
  2. Dual evaluation protocol: framework adherence (taxonomy exact match) vs semantic fidelity
     (LLM-as-judge), plus self- vs external-judge bias analysis.
  3. Empirical baseline + per-concept error analysis over 6 prompt-engineering iterations.
- Roadmap sentence.

## II. Background and Related Work (~1.25 pp)

- **A. Survey design frameworks:** basic concepts, semantic structures, notation; subjective vs
  objective variables. `[CITE: framework source(s)]`
- **B. LLMs for questionnaire / text-to-item generation.** `[CITE: 2-3]`
- **C. LLM-as-judge and self-grading bias.** `[CITE: e.g. MT-Bench / judge literature]`
- **D. Constrained / structured decoding and guided JSON.** `[CITE: vLLM, guided decoding]`
- **E. Open-weight LLM serving** (vLLM, Qwen). `[CITE: vLLM, Qwen technical report]`
- Positioning paragraph: what is new here (framework-grounded, dual eval, prompt-only baseline).

## III. Framework and Task Formalization (~1 pp)

- Formal definitions: indicator, basic concept `c in C` (|C| = 22), semantic structure +
  structure code, assertion, question, question format.
- The 3 semantic structure templates and the notation key (compact table).
- Two subtasks: Assertion Development, Question Development.
- **Table I:** the 22 concepts with type (subj/obj) and allowed structure codes
  (from `concepts.yaml`). Full version to appendix if too large.
- Source: `data/concepts.yaml`, `assertion_developer.md`.

## IV. Method: The Two-Agent Pipeline (~2 pp)

- **A. Architecture overview.** **Fig. 1** = pipeline diagram (redraw `fig02` / the mermaid).
  Indicator -> Assertion Developer -> (concept, structure, assertion) -> Question Developer ->
  (question, options, format).
- **B. Dynamic framework injection:** `{{CONCEPTS_BLOCK}}` from YAML so prompts always reflect the
  taxonomy (`prompt_loader.py`).
- **C. Assertion Developer:** system prompt structure (role, strict rules, confusable-concept
  table, structure-disambiguation table, worked examples), concept `enum` constraint in
  `guided_json`, canonical concept mapping (`match_concept`).
- **D. Question Developer:** prompt, format taxonomy, single-string options rule.
- **E. Structured decoding + robustness:** per-stage JSON schemas, `enable_thinking=false` +
  `/no_think` for Qwen JSON reliability, `parse_json_response`, `_repair_broken_question_json`.
- **F. Serving/infra:** Qwen3.5-9B via vLLM 0.23 on LRZ H100; temp 0.0, max_tokens 1024; LRZ CUDA
  workarounds noted briefly (detail to appendix). `[CONFIRM exact model string]`
- Source: `agents.py`, `llm_client.py`, `pipeline.py`, prompts, `config.yaml`,
  `scripts/start_vllm.sh`.

## V. Experimental Setup (~1.25 pp)

- **A. Gold set:** 113 rows (115 as originally built; corrections in `gold_fixes.py` disclosed
  in Limitations), construction, columns; **Table II** =
  concept counts + domain spread. Note rare concepts (n = 3). Source: `data/gold_set.xlsx`.
- **B. Isolated evaluation protocol:** each agent scored independently; question developer on gold
  assertions (justify: avoids error propagation, matches framework criteria tables). Source:
  `pipeline.evaluate_row`, README.
- **C. Normalization:** lowercasing, whitespace, US/UK spelling unification, regex structure-code
  extraction; rationale (fair scoring without editing gold). Source: `normalize.py`.
- **D. Metrics:**
  - Objective: concept accuracy, structure accuracy, both-correct, question non-empty, question
    exact match, format-tagged.
  - Semantic: LLM-as-judge 1-5 for indicator->assertion (IA) and assertion->question (AQ);
    rubric. Source: `metrics.py`, `judge.py`.
- **E. Judge models:** self-judge Qwen3.5-9B (Run 4); external Qwen2.5-72B (Run 5, TP = 2) and
  **Qwen3-32B (Run 7, TP = 2)** after the 72B was deleted from the shared store. Both judges
  scored the same Run 4 predictions, so the swap is measurable rather than silent.
  Source: `config.yaml`, `run_judge_only.py`, `start_vllm_judge.sh`.
- **F. Reproducibility:** config-driven, commit hashes per run, deterministic temp 0.

## VI. Prompt-Engineering Iterations (~1 pp)

- Narrative of Runs 1 -> 7 as controlled interventions; **Table III** = changelog matrix (which
  technique entered which run), mirroring the BASELINE_REPORT matrix.
- Per-run one-liners: R1 baseline; R2 spelling-norm + concept enum + confusable table; R3 structure
  table + examples 7-9 + JSON repair; R4 self-judge; R5 external judge; R6 structure pass 2 + YAML
  alignment; **R7 three-arm ablation (YAML repair / de-leaked examples / notation rule), judge
  replacement, 2x2 generator x judge**.
- **R7 is the only run with a clean single-intervention design** — say so, and use it rather than
  the R1-R6 narrative to support causal claims about prompt content.
- Source: `docs/BASELINE_REPORT.md`, `docs/PLAN.md`.

## VII. Results (~2 pp)

- **A. Overall progression:** **Fig. 2** (`fig01`) + **Table IV** (all metrics x runs, n=113).
  Headline: concept 65.5 -> **85.0**, structure 51.3 -> **79.6**, both 47.8 -> **79.6**.
  Report exact-McNemar p-values per transition, not just the trend.
- **B. Per-concept & per-structure:** **Fig. 3** (`fig03`), **Fig. 4** (`fig06` concept-structure
  gap). Which concepts hit 100% vs 0%.
- **C. Question stage:** coverage 100%; **Fig. 5** (`fig09`) exact-match vs judge; format
  distribution note.
- **D. Semantic (judge) results:** IA 4.51 / AQ 4.99 self; **Fig. 6** (`fig12`) self vs external;
  **Fig. 7** (`fig13`) external distributions. **Report score distributions, not means** — the 9B
  and 32B judges differ by 0.05 in mean while using four and two effective scale points
  respectively. Add the 2x2 table. Source: `docs/reanalysis.json`.

## VIII. Error Analysis and Discussion (~1.75 pp)

- **A. Concept confusions:** **Fig. 8** (`fig04`/`fig07`), Evaluation <-> Preference,
  Events <-> Demographics, Norms <-> Values.
- **B. Structure confusions & the coupling paradox:** **Fig. 9** (`fig05`), Expectations 100%
  concept but structure fixed only in R6; `xFD`/`xDpl`/`xFy` story.
- **C. Trade-offs:** Norms regression from strengthening Values rules (a concrete
  prompt-engineering cost).
- **D. Judge as instrument, not oracle:** there is **no self-preference bias** (2x2: each judge
  scores both generators within 0.05; the 32B is harsher on its own output). The finding is that
  the small judge does not use the scale. Discrimination ordering 72B > 32B > 9B.
- **E. Exact match is misleading** for generative question quality (r ~ 0.04); argue for
  judge-based reporting.
- **F. Prompt engineering vs fine-tuning:** 85% reached without training. **Scale is not the
  lever**: the Qwen3-32B generator scores 68.1% both-correct against the 9B's 79.6% on the same
  prompt. This is a framework-adherence problem, so LoRA is not obviously the next step.

## IX. Limitations (~0.5 pp)

- Small gold set (n=113); rare concepts n = 3, so the headline Norms/Policies/Causal gains rest on
  7 items; single model family; no human-expert validation yet; single-facet indicator granularity;
  English only.
- **Gold-set corrections** (2 duplicates dropped, 1 notation standardised) — state them explicitly.
- **Residual leakage:** the de-leaked prompts remove verbatim gold items, but the *rules* were
  still written while looking at these items. Only a genuinely new test set closes this.
- **Judge swap is confounded:** the 72B was deleted mid-project, so the 72B/32B leniency gap
  cannot be decomposed into scale vs model family vs thinking-mode.

## X. Conclusion and Future Work (~0.5 pp)

- Recap contributions + headline. Future: **v7c** aligning the prompt tables with the corrected
  `xP(e)y` notation (prompts still teach `xPyc` in four places); a genuinely new annotated test
  set; inter-annotator agreement; human spot-check of the 32B judge.

## References (~1.5 pp)

- ~15-20 entries. Placeholders now; real, verifiable citations to be sourced before the final
  draft; any that cannot be confirmed will be flagged.

## Appendix (~3 pp)

- **A. Full concept-structure taxonomy** (all 22 concepts, all structure codes, notation key) from
  `concepts.yaml`.
- **B. Full prompts** (Assertion + Question system prompts, abridged worked examples).
- **C. Complete per-concept results table** (n, concept %, structure % for all 22) from Run 6
  summary JSON.
- **D. Confusion matrices** (concept + structure) as full tables/heatmaps: `fig04`, `fig05`,
  `fig07`.
- **E. Judge rubric + example rationales**, worst-scoring rows (IDs 55/57/59/65/70).
- **F. LRZ/vLLM reproduction details** (CUDA workarounds, flags, commands).

---

## Figure / table inventory

All figure assets already exist as PDF + PNG in `docs/figures/`.

- **Body figures:** `fig01`, `fig02`, `fig03`, `fig06`, `fig09`, `fig12`, `fig13`.
- **Appendix/discussion figures:** `fig04`, `fig05`, `fig07`, `fig10`, `fig11`, `fig14`.
- **New tables:** Table I (taxonomy), Table II (gold-set distribution), Table III (run changelog
  matrix), Table IV (metrics x runs). Built from `concepts.yaml`, `gold_set.xlsx`, and
  **`docs/reanalysis.json`** — NOT the `eval_summary_*.json` files, which are stale at n=115.
- **New table (recommended):** the 2x2 generator x judge cell means plus each judge's score
  distribution. It carries the W3 argument better than any figure.

## Open items before drafting prose

1. ~~`[CONFIRM]` exact generator model string~~ **Resolved:** `Qwen/Qwen3.5-9B` is real — the
   model card on disk confirms it (apache-2.0, post-trained, base `Qwen/Qwen3.5-9B-Base`).
   Add the judge models alongside it: `Qwen/Qwen2.5-72B-Instruct` (Run 5) and `Qwen/Qwen3-32B`
   (Run 7).
2. `[CITE]` real citations for Section II (framework origin, LLM-as-judge, vLLM, Qwen, constrained
   decoding).
3. Minor methods footnote: `concepts.yaml` spells "Behaviour"/"Cognitive judgement" vs gold
   "Behavior"/"Cognitive judgment" (handled by `normalize.py`).

## Key numbers (quick reference, from committed artifacts)

All corrected to **n=113** (`docs/reanalysis.json`). Do not mix these with the as-published
n=115 figures in the per-run sections of `BASELINE_REPORT.md`.

| Metric | Run 1 | Run 2 | Run 3 | Run 6 | v6repro | v7a | **v7b (best)** |
|--------|-------|-------|-------|-------|---------|-----|----------------|
| Concept accuracy | 65.5% | 69.0% | 75.2% | 76.1% | 78.8% | 77.9% | **85.0%** |
| Structure accuracy | 51.3% | 54.0% | 61.1% | 74.3% | 76.1% | 73.5% | **79.6%** |
| Both correct | 47.8% | 51.3% | 59.3% | 72.6% | 74.3% | 71.7% | **79.6%** |
| Question exact match | 20.4% | 20.4% | 18.6% | 17.7% | 20.4% | 20.4% | 20.4% |

**Paired significance (exact McNemar):** only two transitions reach p < 0.05 —
Run 3 -> Run 6 structure (**p=0.024**) and v7a -> v7b concept (**p=0.039**).
Run 1 -> Run 2 concept is **p=0.503**.

**Judges (mean indicator->assertion, n=113):**

| | judge 9B | judge 32B |
|---|---|---|
| gen 9B | 4.48 | 4.43 |
| gen 32B | 4.49 | 4.39 |

- No self-preference bias; the 32B is *harsher* on its own output (-0.04).
- 9B score distribution on gen9b: `1:2, 2:16, 3:0, 4:1, 5:91` (+3 unparseable) — **degenerate**.
- 32B on gen9b: `2:2, 3:15, 4:28, 5:68`.
- Judge swap on identical Run 4 predictions: 72B mean **4.09**, 32B mean **4.51**.

**Other headline numbers:**

- Leakage (v6repro): **100%** (15/15) on prompt-quoted items vs **75.5%** (74/98) held-out.
- P(structure correct | concept correct) = **93.8%**; **0.0%** when concept is wrong.
- No-LLM baselines: majority class **16.8%**, lexical 1-NN **32.7%** concept / **31.0%** structure.
- Qwen3-32B *as generator*: **68.1%** both-correct vs the 9B's **79.6%** on the same prompt.
- Answer-option response-type agreement: **61.1%**. Question format: **1 distinct value** (degenerate).
