# Paper Review: *Assertion and Question Developer for Agentic Questionnaire Development*

## Metadata
- **Authors**: Lanre Oriowo, Rudraksha Samdhani (LMU Munich)
- **Venue**: IEEEtran template, seminar report (NLP/CSS), 2026 — 23 pp. as compiled
- **Type**: Empirical / systems
- **Domain**: Computational social science, LLM evaluation, survey methodology

## Executive Summary

The paper implements Saris & Gallhofer's three-step survey-design method as a two-agent prompted pipeline (Assertion Developer → Question Developer) over a ~9B open-weight model with schema-guided JSON decoding, and evaluates it against a hand-built 115-item gold set spanning all 22 basic concepts. Six prompt-engineering iterations lift concept accuracy 57.4→76.5% and structure accuracy 51.3→75.7%, with a dual protocol separating framework adherence (exact match on taxonomy labels) from semantic fidelity (LLM-as-judge), plus a self- vs. external-judge comparison quantifying ~0.43 points of self-grading bias.

The engineering is clean and the write-up is unusually well organized: the isolated-stage protocol, the enum-constrained concept field, and the dynamic taxonomy injection are all genuinely good design decisions, and the per-concept/per-structure diagnostics are more thorough than most seminar work. The honest reporting of the Norms regression (§7.3) is a highlight — most papers would have buried it.

The central problem is that **the headline accuracy is a training-set number**. All six prompt iterations were tuned by inspecting errors on the same 115 items the final 76.5% is reported on, and Run 6 additionally *edited the injected taxonomy file to match the gold structure codes*. With no held-out split, the reported figures are upper bounds on in-sample fit, not estimates of generalization. Combined with the absence of any confidence intervals on n=115 (and n=3 per-concept cells), the run-to-run comparisons that carry the paper's argument are not statistically supportable as stated. These are fixable — mostly by reframing claims and adding a split — but they need fixing before the numbers can be read the way the abstract and conclusion currently ask them to be read.

## Claims vs. Evidence

| # | Claim | Evidence | Strength |
|---|---|---|---|
| 1 | Prompt engineering alone reaches 76.5%/75.7% without fine-tuning | Tables V, VII — arithmetic checks out (88/115 and 87/115) | **Moderate** — in-sample only |
| 2 | Dual protocol separates adherence from fidelity | §5.4, Runs 4–5 | **Strong** |
| 3 | ~0.43-point self-grading bias | Run 4 vs. Run 5 on identical generations | **Moderate** — confounded (below, W3) |
| 4 | Exact match understates question quality | 17–20% EM vs. 4.56/5 AQ, all items ≥4 | **Strong** |
| 5 | Residual errors concentrate on rare, subtle concepts | Table VII: Norms 0%, Policies 0%, Causal 33% | **Weak** — n=3 each |
| 6 | Framing not previously applied to survey item construction | Assertion in §2.6 | **Weak** — see Literature Positioning |

## Strengths

### S1: The isolated evaluation protocol is the right call and is well justified
Running $f_Q$ on the *gold* assertion $a^\star$ rather than the predicted $a$ (§3.2, §5.2) cleanly prevents stage-1 errors from contaminating stage-2 measurement. Many pipeline papers conflate the two and then cannot attribute failures. The paper states the rationale explicitly and applies it consistently.

### S2: Constrained decoding is used to *eliminate* an error class, not decorate the method
Restricting the `concept` field to the 22-name enum (§4.4) makes out-of-taxonomy labels structurally impossible, which is what makes taxonomy-level scoring unambiguous in the first place. The JSON-repair fallback and the single-delimited-string answer-options design are pragmatic, honestly reported engineering fixes.

### S3: Dynamic taxonomy injection creates a real, demonstrated causal lever
Storing the framework in `concepts.yaml` and rendering it into both system prompts (§4.1) is more than tidiness — §7.2 shows that aligning that one file with the gold codes propagated corrected codes into the prompt and produced the largest single-run structure gain. This is a genuinely reusable design pattern.

### S4: Negative results are reported
§7.3's Norms regression (Values-vs-Importance rules bled into deontic indicators, dropping Norms to 0%) is exactly the kind of non-monotonicity that prompt-engineering papers usually suppress. Reporting it, and naming the targeted fix, materially raises the paper's credibility.

### S5: Diagnostics are thorough for the scope
Per-concept accuracy for all 22 concepts (Table VII), both confusion matrices (App. D), the concept–structure gap plot (Fig. 6), and the hardest-items table (Table VIII) let a reader independently reconstruct where the system fails. I verified Table VII against the headline numbers — 88/115 = 76.5% and 87/115 = 75.7% both reconcile exactly.

## Weaknesses

### W1 (Major): No held-out split — the reported accuracy is in-sample
§6 describes six iterations in which each run's errors were inspected and the prompt (disambiguation tables, worked examples, and in Run 6 the reference file itself) was edited in response. The final 76.5% is then reported on those same 115 items. This is prompt-tuning on the test set. It is compounded by the Run 6 intervention: the paper writes that "the machine-readable reference file was aligned with the gold structure codes" — the gold labels were, by the paper's own description, written into the prompt.

**Impact**: The abstract's and §8's headline figures cannot be read as generalization estimates, and the "prompt engineering reaches a strong baseline" conclusion is weakened in precisely the way the paper wants to be strong.

**Fix**: Split the 115 items (e.g. stratified 60 dev / 55 test, or leave-one-domain-out), iterate on dev only, and report the final run on test once. If the sample is too small to spare items, say plainly in §9 that all numbers are in-sample and report them as fit rather than generalization. Either is acceptable; silence is not.

### W2 (Major): Structure accuracy is not an independent metric
In Table VII, concept % and structure % are *identical* for 18 of 22 concepts; they differ only for Values, Similarity, Policies, and Evaluative belief. Table II shows why: most concepts license exactly one structure code, so once the concept is chosen the code is nearly determined — and after Run 6 the correct codes were injected into the prompt. Reporting concept and structure accuracy as two headline results (and "both correct" as a third) over-counts what is close to one underlying decision.

**Fix**: Report structure accuracy *conditional on a correct concept* ($P(s\text{ correct} \mid c\text{ correct})$) as the primary structure metric. That is the number that isolates what the structure prompt actually contributes; the current figure mostly re-reports concept accuracy.

### W3 (Major): The self-grading-bias result confounds self-preference with judge scale/strictness
§5.5 and §7.4 compare a 9B self-judge against a 72B external judge and attribute the entire 0.42–0.43 drop to self-preference. But the two judges differ in *both* identity and capacity. A larger, more capable judge being stricter on the same items is an equally consistent explanation, and the paper's own evidence points that way: §7.4 notes the 72B judge separates correct from incorrect concept labels while the 9B judge does not — that is a *discrimination* difference, i.e. the 9B judge is a poor judge, which is not the same finding as self-preference.

**Impact**: The claim is one of three stated contributions, and as designed the experiment cannot support it.

**Fix**: The clean control is cheap — have the 72B judge score outputs *it* generated, and/or have the 9B judge score the 72B's outputs. Only the 2×2 separates self-preference from strictness. Failing that, retitle the finding "judge-scale disagreement" and drop the causal reading. Also note that a mean AQ of 4.99/5 from the self-judge (Table V) is effectively a degenerate metric and worth calling out as such.

### W4 (Major): No statistical treatment, and "best run" rests on one item
Run 3 → Run 6 concept accuracy moves 75.7 → 76.5, which on n=115 is **a single item**, yet 76.5 is bolded as best and Run 6 is designated "our best configuration" throughout. A Wilson interval on 88/115 is roughly ±7.8pp; per-concept cells with n=3 have intervals spanning most of the unit interval, so "Norms 0%" and "Rights 100%" are, statistically, barely distinguishable.

**Fix**: Add Wilson or bootstrap CIs to Table V, add McNemar's test for the paired run-to-run comparisons (the runs are on identical items, so paired tests are available and appropriate), and either drop per-concept percentages for n=3 cells or print them as raw counts (`0/3`, `2/3`) so readers cannot over-read them. Note that the Run 2 (+12.2) and Run 6 (+13.1) gains would likely survive this; the Run 3→6 concept claim will not.

### W5 (Moderate): Run 2 bundles three interventions, one of which is a scoring change
§6 opens by claiming each iteration "introduced one coherent change," but Table IV shows Run 2 introducing spelling-normalized *scoring*, the enum constraint, and the disambiguation table simultaneously. The first of these changes no model behavior at all — it changes the measuring instrument. So an unknown share of the +12.2-point "largest jump" is a scoring artifact, not a capability gain.

**Fix**: Trivially recoverable — re-score the Run 1 outputs under the Run 2 normalizer and report that number. The gap between it and 57.4 is the artifact; the rest is real. This single number would strengthen the paper's central progression claim considerably.

### W6 (Moderate): No baselines of any kind
There is no unprompted/naive-prompt baseline, no comparison against the 72B model doing generation, no random or majority-class floor (majority class = Evaluation at 20/115 ≈ 17.4%), and no human/expert ceiling. Without at least a floor and a larger-model point, "76.5% via prompt engineering" has no scale attached — a reader cannot tell whether this is close to ceiling or well below what a bigger model does zero-shot. The last is especially relevant since a 72B model is already deployed for judging.

### W7 (Moderate): The gold set has no reported inter-annotator agreement
§5.1 says the 115 items were "constructed by expert annotation," but does not say by how many annotators, with what agreement, or how disagreements were resolved. Every objective metric in the paper is exact match against this set. §7.1 itself observes that the failing distinctions "are exactly the distinctions that expert annotators find hardest" — which raises the possibility that some scored errors are gold-label disagreements rather than model errors. Even a double-annotated 25-item subset with a Cohen's κ would settle this.

### W8 (Moderate): Two of the six output fields are defined but never evaluated
The task formalization defines $f_Q: a \mapsto (q, o, \phi)$ and the gold tuple includes $o^\star$, but answer options are never scored against gold anywhere in the paper. And §7.3 reports that *every* generated question received the same format tag (direct interrogative with WH word) — meaning $\phi$ is a constant, the five-format space $\Phi$ is unused, and format is never scored against a reference either (the gold tuple in §3.2 omits $\phi^\star$). A degenerate output field deserves a sentence in §9, not a passing remark in Results.

### W9 (Minor–Moderate): Abstract mixes runs
The abstract pairs "4.56 out of 5" (external judge, scoring **Run 4** generations) with "about 17 percent match the reference wording exactly" (**Run 6**, 17.4%). The corresponding Run 4 figure is 18.3%. The conclusion concedes the underlying gap — "the semantic evaluation should be extended by re-scoring the best configuration with the external judge" — i.e. the best configuration was never externally judged. Either quote both numbers from Run 4, or run the external judge on Run 6 (a re-scoring pass, no regeneration needed; this is the single highest-value additional experiment in the paper and it is cheap).

## Methodology Assessment

| Criterion | Rating | Assessment |
|---|:--:|---|
| Soundness | 3/5 | Pipeline and isolated protocol are sound; the evaluation loop leaks (W1) and the bias claim is confounded (W3) |
| Novelty | 2/5 | Sensible engineering combination, but each ingredient is standard and near-identical prior work exists uncited |
| Reproducibility | 3/5 | Deterministic decoding, config-driven runs, exported artifacts — good. But no exact checkpoints, no code URL, no gold-set release stated |
| Experimental Design | 2/5 | No held-out split, no baselines, no ceiling, bundled interventions in Run 2 |
| Statistical Rigor | 1/5 | No CIs, no significance tests, n=3 cells reported as percentages, "best" run decided by one item |
| Scalability | 3/5 | Serving setup described; no throughput, latency, cost, or GPU-hour figures, and no scaling argument beyond 115 items |

**Contribution level**: Moderate. **Overall**: **Borderline** — solid seminar work, clearly presented, but not yet workshop-ready as written. **Confidence**: High on internal consistency (all arithmetic verified and the source compiled); Medium on novelty positioning (single literature search, not exhaustive).

## Literature Positioning

The cited foundation is appropriate — Saris & Gallhofer for the framework, Zheng et al. for LLM-as-judge, Panickssery et al. and Wang et al. for self-preference, Willard & Louf for guided decoding, Kwon et al. for serving. All 12 bib entries are cited and all 12 citations resolve; nothing dangling in either direction.

The gap is in §2.2 and §2.6. The claim that "to our knowledge, this framing has not previously been applied to automated survey item construction" is too strong — there is a small but directly adjacent 2025–2026 literature the paper does not engage:

- **[Exploring LLMs for Automated Generation and Adaptation of Questionnaires](https://arxiv.org/abs/2501.05985)** (ACM CUI 2025) — an LLM pipeline for creating and adapting questionnaires, with the finding that LLM-generated items are "too broad, generic in wording, and lack specificity." That is a direct, and partly contradicting, comparison point for the near-ceiling AQ scores reported here.
- **[AI for Survey Design: Generating and Evaluating Survey Questions with LLMs](https://ideas.repec.org/p/osf/socarx/fzn7t_v1.html)** — evaluates LLM-generated items across models and prompting strategies, reporting chain-of-thought as strongest. This is the closest existing baseline to Runs 1–6 and should be discussed.
- **SQP (Survey Quality Predictor)** — the quality-estimation instrument from the *same* Saris tradition the paper builds on, used by that work to score generated items. Its absence is the most conspicuous omission: SQP would give an external, non-LLM, methodologically-native quality metric, which is exactly what §9 concedes is lacking ("we do not yet validate either judge against expert human ratings").

Adding SQP scoring would be a substantive upgrade, not just a citation fix — it converts the weakest evaluation axis into the strongest, using a tool the framework's own authors built.

## Build and LaTeX Issues (verified by compiling)

**Blocking**: `bibtex` fails — `IEEEtran.bst` is not in the directory and not in the local TeX Live install, so **every citation currently renders as `[?]`**. Either drop `IEEEtran.bst` next to the `.cls`, or change line 623 to `\bibliographystyle{ieeetr}` (confirmed present in the distribution). Compiles to 23 pages otherwise, no errors.

**Blocking**: `\section*{Contributions}` (line 476) is **empty**. Fill it or delete it.

**Notation gaps in App. A (Table VI)** — three symbols used in Table II are undefined:
- `$v$` in the Values code `$vIi$`
- the `_e` suffix in the Evaluative belief codes `$xPy\_e$`, `$xP\_e$`
- `$z$` (comparison referent) is defined but never used in Table II

**Likely typo, Table II**: Procedures is listed as `$xDpl,\,pro$` — `pl` is the *place* symbol per App. A, and Place is already `$xDpl$`. Should this be `$xDpro$`? As printed, Place and Procedures share a code prefix, which would make them indistinguishable at scoring.

**Ambiguous parse**: `$xFD$` (future deed) vs. `$xFy$` (feeling + object) — `F` is "feeling" and `FD` is "future deed" in App. A, so the codes are only disambiguated by greedy matching. Worth one clarifying sentence in §3.1. Related: Action tendencies and Expectations of future events are both licensed *only* `$xFD$` (Table II), so structure can never discriminate them — yet §7.2 says Expectations' "structure code was consistently wrong" before Run 6, which under Table II means the model emitted an unlicensed code. Clarify.

**Model identification**: the generator is described only as "roughly nine billion parameters," "reasoning-capable," "thinking mode disabled," citing the Qwen technical report. Name the exact checkpoint (Qwen3-8B? — there is no 9B Qwen, so "nine billion" is imprecise) and likewise for the 72B judge; if the judge is Qwen2.5-72B and the generator is Qwen3-8B, "a larger model from the same family" is a stretch worth qualifying, since it also affects the W3 confound. §10 promises "the code release" but no URL/DOI appears anywhere.

**Other**:
- §7.1: "Seven concepts, **including** ... [seven listed]" — should be "namely"; Table VII confirms exactly seven at 100/100.
- §6.4 Results: "**94 of the 94** questions that do not exactly match" — awkward; and it sits oddly beside §7.5's hedged "every non-matching question **that we examined**." Pick one; if it's all 94, say so unhedged.
- "a drop of roughly 0.43 points on each metric" — it is 0.42 (IA) and 0.43 (AQ); say "0.42 and 0.43."
- Abstract says "57 to 77 percent"; body says 57.4 to 76.5. Round consistently (76.5 → 77 is defensible but jars against the body).
- §7.3's claim that Norms was "previously correct" is not evidenced — no per-concept table exists for Runs 3/4. Add the Run 4 per-concept column, or soften.
- Table VII, Policies: concept 0% but structure 66.7% — this directly contradicts §7.2's "when the concept is wrong, the structure is almost always wrong too." Worth one explanatory sentence.
- Formatting: with `onecolumn`, `figure*`/`table*` are no-ops and `width=\columnwidth` equals `\textwidth`; harmless but simplifiable. `\tableofcontents` is non-standard for IEEEtran — fine for a seminar report, remove if submitting elsewhere.
- 5× `LaTeX Warning: 'h' float specifier changed to 'ht'` in the appendices — change `[h]` to `[ht]` to silence.

## Questions for the Authors

1. Were the disambiguation tables and worked examples written by inspecting errors on the same 115 items the final numbers are reported on? If yes, can any subset be reserved as held-out?
2. In Run 6, what exactly changed in `concepts.yaml`? If gold structure codes were copied in, how do you distinguish "correcting the framework file" from "supplying the answers"?
3. How much of Run 2's +12.2 points is the spelling normalizer rather than the enum constraint and prompt table? (Re-scoring Run 1 outputs under the Run 2 normalizer answers this directly.)
4. How many annotators built the gold set, and what was their agreement — particularly on the Norms/Values/Policies cluster the model fails on?
5. Why was the external judge never run on Run 6, given it is a re-scoring pass over existing generations?
6. Given that every question was tagged with the same format, is the format field doing any work? Was it ever scored against a reference?

## Top Recommendations, in priority order

1. **Run the external judge on Run 6** — cheapest fix, closes the abstract's cross-run inconsistency (W9), and is already listed as future work.
2. **Add a held-out split, or state plainly that all numbers are in-sample** (W1). This is the difference between a defensible result and an overclaim.
3. **Add the 2×2 judge control** (72B judging its own output) or retitle the bias finding (W3).
4. **Add Wilson CIs + McNemar tests to Table V; print n=3 cells as counts** (W4). Then stop calling Run 6 "best" on a one-item margin.
5. **Report structure accuracy conditional on correct concept** (W2), and re-score Run 1 under the Run 2 normalizer (W5).
6. **Fix the build**: `\bibliographystyle{ieeetr}`, fill or cut §Contributions, patch the three App. A notation gaps and the `$xDpl,\,pro$` typo.
7. **Engage the 2025 LLM-questionnaire literature and add SQP scoring** — softens the novelty claim, but replaces the weakest evaluation axis with a methodologically-native external metric.

---

Sources: [Exploring LLMs for Automated Generation and Adaptation of Questionnaires](https://arxiv.org/abs/2501.05985) · [AI for Survey Design: Generating and Evaluating Survey Questions with LLMs](https://ideas.repec.org/p/osf/socarx/fzn7t_v1.html) · [ACM CUI 2025 proceedings version](https://dl.acm.org/doi/full/10.1145/3719160.3736606)
