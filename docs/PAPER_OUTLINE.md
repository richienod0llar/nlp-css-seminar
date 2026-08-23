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
evaluated against a hand-built 115-row gold set.

- **Framework:** 22 basic concepts (14 subjective / 8 objective), 3 semantic structures, a
  structure-code notation (e.g. `xIe`, `xFD`, `xPRy`), 5 question formats. Encoded in
  `data/concepts.yaml`, injected dynamically into prompts.
- **Pipeline:** `Assertion_Developer` (indicator -> concept + structure code + assertion) and
  `Question_Developer` (assertion -> question + options + format). Both Qwen3.5-9B via a vLLM
  OpenAI-compatible server on an LRZ H100, with guided JSON decoding, concept `enum` constraint,
  and JSON-repair fallbacks.
- **Data:** 115 rows, 22 concepts, 73 subjective / 42 objective, ~40 domains.
- **Evaluation:** isolated per-agent protocol (question developer scored on gold assertions).
  Objective = normalized exact match on concept + structure; semantic = LLM-as-judge 1-5
  (self 9B and external 72B). Per-concept/per-structure breakdowns, confusion matrices,
  question-format distribution.
- **Result arc:** 6 prompt-engineering runs (no fine-tuning) moved the assertion stage from
  57%/51% (concept/structure) to 76.5%/75.7%, both-correct 43% -> 74%. External 72B judge
  confirms the question stage is strong semantically (AQ 4.56/5, 100% >= 4) despite ~17% exact
  string match, and quantifies a ~0.43-point self-grading bias. 14 publication figures exist as
  PDF + PNG.

---

## Front matter (~0.5 pp)

- **Title** (working): *Prompt-Engineered Large Language Models for Framework-Grounded Survey
  Item Generation: A Baseline and Dual Evaluation.*
- **Abstract** (~200 words): problem, two-agent pipeline, 22-concept framework, 115-row gold set,
  dual objective + judge evaluation, headline results (57 -> 76.5% concept, 51 -> 75.7% structure
  via prompting alone; judge AQ 4.56/5), key finding (exact match understates quality; self-grade
  bias ~0.43).
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

- **A. Gold set:** 115 rows, construction, columns; 73 subjective / 42 objective; **Table II** =
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
- **E. Judge models:** self-judge Qwen3.5-9B (Run 4) and external Qwen2.5-72B (Run 5, TP = 2).
  Source: `config.yaml`, `run_judge_only.py`.
- **F. Reproducibility:** config-driven, commit hashes per run, deterministic temp 0.

## VI. Prompt-Engineering Iterations (~1 pp)

- Narrative of Runs 1 -> 6 as controlled interventions; **Table III** = changelog matrix (which
  technique entered which run), mirroring the BASELINE_REPORT matrix.
- Per-run one-liners: R1 baseline; R2 spelling-norm + concept enum + confusable table; R3 structure
  table + examples 7-9 + JSON repair; R4 self-judge; R5 external judge; R6 structure pass 2 + YAML
  alignment.
- Source: `docs/BASELINE_REPORT.md`, `docs/PLAN.md`.

## VII. Results (~2 pp)

- **A. Overall progression:** **Fig. 2** (`fig01`) + **Table IV** (all metrics x runs). Headline:
  concept 57.4 -> 76.5, structure 51.3 -> 75.7, both 42.6 -> 73.9.
- **B. Per-concept & per-structure:** **Fig. 3** (`fig03`), **Fig. 4** (`fig06` concept-structure
  gap). Which concepts hit 100% vs 0%.
- **C. Question stage:** coverage 100%; **Fig. 5** (`fig09`) exact-match vs judge; format
  distribution note.
- **D. Semantic (judge) results:** IA 4.51 / AQ 4.99 self; **Fig. 6** (`fig12`) self vs external;
  **Fig. 7** (`fig13`) external distributions; external IA 4.09 / AQ 4.56, 100% AQ >= 4. Source:
  summaries + BASELINE_REPORT.

## VIII. Error Analysis and Discussion (~1.75 pp)

- **A. Concept confusions:** **Fig. 8** (`fig04`/`fig07`), Evaluation <-> Preference,
  Events <-> Demographics, Norms <-> Values.
- **B. Structure confusions & the coupling paradox:** **Fig. 9** (`fig05`), Expectations 100%
  concept but structure fixed only in R6; `xFD`/`xDpl`/`xFy` story.
- **C. Trade-offs:** Norms regression from strengthening Values rules (a concrete
  prompt-engineering cost).
- **D. Self- vs external-judge bias:** ~0.43 drop; 72B penalizes first-person demographic phrasing;
  implications for using self-judge.
- **E. Exact match is misleading** for generative question quality (r ~ 0.04); argue for
  judge-based reporting.
- **F. Prompt engineering vs fine-tuning:** ~76% reached without training; where LoRA would/wouldn't
  help.

## IX. Limitations (~0.5 pp)

- Small gold set; rare concepts n = 3 (high-variance estimates); single model family; self-judge
  bias; no human-expert validation yet; single-facet indicator granularity; English only.

## X. Conclusion and Future Work (~0.5 pp)

- Recap contributions + headline. Future: Norms prompt fix (Run 7), external judge on Run 6
  predictions, human spot-check vs 72B, optional LoRA on rare concepts.

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
  matrix), Table IV (metrics x runs). Built from `concepts.yaml`, `gold_set.xlsx`, and the summary
  JSONs in `docs/baseline/`.

## Open items before drafting prose

1. `[CONFIRM]` exact generator model string (repo says "Qwen3.5-9B", unusual; matters for
   reproducibility).
2. `[CITE]` real citations for Section II (framework origin, LLM-as-judge, vLLM, Qwen, constrained
   decoding).
3. Minor methods footnote: `concepts.yaml` spells "Behaviour"/"Cognitive judgement" vs gold
   "Behavior"/"Cognitive judgment" (handled by `normalize.py`).

## Key numbers (quick reference, from committed artifacts)

| Metric | Run 1 | Run 2 | Run 3 | Run 4 | Run 6 (best) |
|--------|-------|-------|-------|-------|--------------|
| Concept accuracy | 57.4% | 69.6% | 75.7% | 75.7%* | 76.5% |
| Structure accuracy | 51.3% | 55.7% | 62.6% | 62.6%* | 75.7% |
| Both correct | 42.6% | 53.0% | 60.9% | 60.9%* | 73.9% |
| Question non-empty | 99.1% | 99.1% | 100% | 100% | 100% |
| Question exact match | 20.0% | 20.0% | 18.3% | 18.3% | 17.4% |

\*Run 4 re-scores Run 3 generations; judge columns added.

- Self-judge (Run 4, 9B): mean IA 4.51, mean AQ 4.99.
- External judge (Run 5, 72B on Run 4 preds): mean IA 4.09, mean AQ 4.56, 100% AQ >= 4;
  self-grade bias ~ -0.43 on both metrics.
