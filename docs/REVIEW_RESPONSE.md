# Review Response: changes made, new findings, and what to run next

Working document for addressing `Seminar_Paper/review.md` (overall rating: **Borderline**,
Statistical Rigor **1/5**, Experimental Design **2/5**).

> **Status 2026-08-24 — Parts 1, 2, 3 and 5 are DONE.** Run 7 executed on SLURM job 5760085;
> all seven output sets are in `docs/baseline/`. The Part 5 decisions have been taken and
> applied (gold set corrected to **n=113**). Only **Part 4** (paper prose) remains.
>
> **All numbers in this document below this line are the pre-correction n=115 values** and are
> kept as the record of the review response. The corrected n=113 numbers are in
> `docs/reanalysis.json` and `docs/BASELINE_REPORT.md` § Corrected results.

---

## Part 0 — TL;DR of what the numbers now say

### Outcome after Run 7 (2026-08-24)

| Objection | Resolution |
|---|---|
| Prompt leakage (W1) | **Fixed.** `v7a`/`v7b` prompts contain **zero** verbatim gold items. The leakage was real: 100% (15/15) on quoted items vs 75.5% held-out in `v6repro`. |
| Norms/Policies/Values collapse (W5) | **Fixed.** Norms 0→100%, Policies 0→66.7%, Causal 33.3→100%; 18 of 22 concepts unchanged. Paired McNemar **p=0.039**. |
| Self-preference bias (W3) | **Refuted, and replaced by something stronger.** The 2×2 shows no self-preference (±0.05). The real finding: the 9B judge emits only 5s and 2s — zero 3s, one 4, across 113 items. |
| Statistical rigor (1/5) | **Addressed.** Wilson CIs on every cell, exact McNemar on every transition, two no-LLM baselines. Result: only **2 of 6** transitions are significant. |
| Experimental design (2/5) | **Partly addressed.** Run 7 has a clean one-intervention-per-arm ablation. Still open: a genuinely new test set, and inter-annotator agreement. |
| Gold-set defects | **Fixed.** Two exact duplicates removed, evaluative-belief notation standardised → n=113. |
| Judge availability | Qwen2.5-72B was **deleted from the shared store**; replaced with Qwen3-32B and the swap measured on identical items. |

### Original pre-correction analysis (n=115, kept for the record)

| Claim in the paper | Status after re-analysis |
|---|---|
| 76.5% concept accuracy | Inflated by prompt leakage. **72.7%** on the 99 items not quoted in the prompt. |
| 75.7% structure accuracy | ~96% redundant with concept accuracy. Should be reported as **P(structure \| concept correct) = 96.6%**. |
| Run 6 is the best run | Concept gain over Run 3 is **not significant** (McNemar *p* = 1.0). The structure gain **is** (*p* = 0.024). |
| Run 2's +12.2 pp from prompt tuning | **7.8 pp of it is the spelling normalizer**, i.e. a scoring change, not a model improvement. |
| ~0.43-point self-grading bias | Real, but the better finding is that the 9B self-judge is **a degenerate instrument** (see below). |
| No baselines | Now have two: majority class **17.4%**, lexical 1-NN **33.9%**. The 72.7% is a genuine gain over both. |
| Question format field | **Degenerate**: 1 distinct value across all 115 items. It measures nothing. |
| Answer options never evaluated | Now evaluated: **60.9%** response-type agreement with gold. |

---

## Part 1 — Bugs found and fixed in the codebase

### 1.1 Prompt leakage (review W1) — the big one

**16 of the 115 gold items appear verbatim, with their gold labels, as worked examples in
`src/sig/prompts/assertion_developer.md`**: ids 1, 3, 5, 6, 7, 9, 47, 49, 55, 65, 71, 95, 101,
103, 113, 115. The review suspected tuning on the test set; this is stronger than that — 14% of
the test set is printed in the prompt with the answers.

| Subset | Concept | Structure | Both |
|---|---|---|---|
| All 115 (as published) | 76.5% [68.0–83.3] | 75.7% [67.1–82.6] | 73.9% [65.2–81.1] |
| The 16 items quoted in the prompt | **100%** (16/16) | **100%** | **100%** |
| The other 99 items | **72.7%** [63.2–80.5] | **71.7%** [62.2–79.6] | **69.7%** [60.0–77.9] |

The 16 memorised items score a perfect 100%. Reporting 72.7% costs 3.8 points and removes the
single most damaging objection in the review.

**Fixed by:** two new prompt variants whose worked examples are synthetic and share no indicator
or assertion with the gold set (verified programmatically, zero overlap):

- `src/sig/prompts/assertion_developer_v7a.md` — same 16 examples' *lessons*, none from gold.
- `src/sig/prompts/assertion_developer_v7b.md` — v7a plus the new rule in §1.2.

### 1.2 The Norms/Policies/Values collapse is one missing sentence

5 of Run 6's 27 concept errors are the same mistake, and the framework already contains the fix.
`concepts.yaml` defines `o` = "anyone / general subject" and `g` = "government", but the prompt's
disambiguation tables never explain either symbol, so all deontic "should" indicators route to Values:

| id | Indicator | Gold | Predicted |
|---|---|---|---|
| 89, 90, 91 | "Belief that people/citizens should …" | Norms `o(H+I)y` | Values `vIi` |
| 105, 106 | "Belief that the government should …" | Policies `g(H+I)y` | Norms `g(H+I)y` ← structure already right |
| 83, 84 | "Belief that X affects Y" | Causal relationship `xCy` | Cognitive judgement `xIc` |

For 105/106 the model already emits the correct structure code and only mislabels the concept, so
this is a labelling rule, not a generation problem. v7b adds a subject-symbol table (`o` → Norms,
`g` → Policies, `v` → Values) and a causal-belief rule, **derived from the notation key rather
than from inspecting these errors** — which is what makes it defensible under W1. If it works,
it is worth ~7 items (≈ +6 pp).

### 1.3 Scoring bug in `src/sig/normalize.py`

`extract_structure_code()` truncated at `(` and `,`:

- `xDpl, pro` (Procedures) → `xDpl`, **identical to Place**. The review guessed this from the
  printed table; it was real, in code.
- `xP(e)` and `xP(e)y` both → `xP`, so two distinct Evaluative-belief codes collapsed into one.
- The old regex also matched ordinary words — `"Structure code: xPRy"` matched **"code"**.

**Fixed.** The pattern now keeps parenthesised groups and trailing qualifiers, and requires the
second symbol to be uppercase or a parenthesis, which is what excludes English words.

**Important for the paper: this bug never fired in any reported run.** All four runs re-scored
under the fixed normalizer give byte-identical structure accuracy (51.3 / 55.7 / 62.6 / 75.7).
Report it as found-and-fixed, not as a correction to the results.

Regression test: `test_normalize.py` (`python test_normalize.py` → `normalize ok`).

### 1.4 `data/concepts.yaml` did not parse as intended

Three defects, all of which surfaced in the paper's Appendix A as the notation gaps the review flagged:

1. `structures:` and `question_formats:` were written `1:"..."` and `-"..."` with no space after
   the `:`/`-`. YAML collapsed each **entire block into a single flat string** instead of a mapping
   and a list. `prompt_loader.py` has a `isinstance(structures, str)` branch that silently absorbed
   this, so the prompt received one run-on line.
2. The `notation` block defined **`y` twice**; YAML keeps the last, so "object / second entity"
   was silently discarded. Now merged into one entry.
3. `v` (used in `vIi`) and the `(e)` qualifier (used in `xP(e)y`) were **never defined**. Added.

**Note:** this changes the injected prompt text, so it is a prompt intervention. That is why the
GPU job below runs a `v6repro` arm — to isolate its effect before stacking anything else on top.

### 1.5 Taxonomy inconsistency — needs *your* decision, not a code fix

Four structure codes in the gold set are not licensed by `concepts.yaml`: `xPRy`, `xPyc`,
`xP(e)`, `xP(e)y`. Evaluative belief is the worst case — three notations for one concept:

- gold id 3 → `xPyc`, gold ids 107/108 → `xP(e)` / `xP(e)y`
- `concepts.yaml` licenses → `xPy or xPy_e` / `xP_e`
- the prompt teaches → `xPyc`

So the model is told to emit a code that two of the three gold rows can never match. This is why
Evaluative belief scores badly. **I have not touched this**, because picking a notation changes
the gold labels and therefore the results — that is your call. See Part 5.

### 1.6 Duplicate gold items

Two duplicate pairs in a 115-item set:

- **ids 5 and 71** — "Desired improvement", same concept, same structure, **same domain**. A true
  duplicate; the effective set size is 114.
- **ids 29 and 67** — "Communication quality", same concept and structure, different domain. The
  model sees identical input, so it is a duplicated measurement either way.

Also worth a pass: gold id 85's assertion reads "Goverment spending reduce unemployment"
(misspelling + agreement error), and id 91's assertion is missing its final period.

### 1.7 LaTeX build (review: "Blocking")

- `\bibliographystyle{IEEEtran}` → **`ieeetr`**. `IEEEtran.bst` is neither in `Seminar_Paper/`
  nor in TeX Live, which is why **every citation rendered as `[?]`**. Verified: bibtex now runs
  clean, **0 undefined citations**.
- Deleted the empty `\section*{Contributions}` — the contribution list already exists in the
  Introduction, so the empty section was a leftover.
- `[h]` → `[ht]` on all appendix floats (silences the 5 float-specifier warnings).

### 1.8 Plumbing for ablation arms

So one GPU job can run several prompt variants without hand-editing config between runs:

- `config.yaml` gains an optional `prompts:` block (`assertion`, `question`); defaults unchanged.
- `run_eval.py` gains `--assertion-prompt`, `--tag`, `--max-rows`, `--model`, `--base-url`.
- `run_judge_only.py` gains `--judge-model`, `--judge-base-url`, `--tag` (needed for the 2×2 control).

---

## Part 2 — New results from offline re-analysis

All of this comes from `scripts/reanalysis.py` → `docs/reanalysis.json`. No GPU, no LLM calls.
Re-run any time with `python scripts/reanalysis.py`.

### 2.1 Confidence intervals and significance (W4)

| Run | Concept | 95% CI | Structure | 95% CI |
|---|---|---|---|---|
| Run 1 | 57.4% (66/115) | 48.3–66.0 | 51.3% (59/115) | 42.3–60.2 |
| Run 2 | 69.6% (80/115) | 60.6–77.2 | 55.7% (64/115) | 46.5–64.4 |
| Run 3 | 75.7% (87/115) | 67.1–82.6 | 62.6% (72/115) | 53.5–70.9 |
| Run 6 | 76.5% (88/115) | 68.0–83.3 | 75.7% (87/115) | 67.1–82.6 |

Exact McNemar on paired per-item correctness (*b* = broken, *c* = fixed):

| Transition | Concept | Structure |
|---|---|---|
| Run 1 → Run 2 | *b*=7, *c*=21, **p = 0.013** | *b*=7, *c*=12, p = 0.359 |
| Run 2 → Run 3 | *b*=3, *c*=10, p = 0.092 | *b*=3, *c*=11, p = 0.057 |
| Run 3 → Run 6 | *b*=12, *c*=13, **p = 1.000** | *b*=12, *c*=27, **p = 0.024** |

**Run 6 is not a significant improvement on Run 3 for concept accuracy.** The +0.9 pp headline
is 13 items fixed and 12 items broken — churn, not progress. The structure gain is real. Every
CI overlaps its neighbour, so the paper cannot claim a monotone run-over-run improvement; it can
claim Run 1 → Run 6 overall, and the structure result specifically.

### 2.2 Structure accuracy is not independent (W2)

- P(structure correct **|** concept correct) = **96.6%** (85/88) [90.5–98.8]
- P(structure correct **|** concept wrong) = **7.4%** (2/27) [2.1–23.4]

Once the concept is right the structure is essentially determined. Report the conditional number
as the structure metric and drop "both correct" as a third headline.

### 2.3 Run 2 decomposed (W5)

Re-scoring **Run 1's own predictions** under the current normalizer: 57.4% → **65.2%**.

So of Run 2's +12.2 pp concept gain, **7.8 pp is the spelling normalizer** (a scoring change) and
only **4.4 pp** is the enum constraint plus the confusable-concept table. The paper currently
attributes all 12.2 pp to prompt engineering.

### 2.4 Baselines (W6)

| System | Concept | 95% CI |
|---|---|---|
| Majority class ("Evaluation") | 17.4% | 11.5–25.3 |
| Lexical 1-NN over indicators (TF-IDF, leave-one-out) | 33.9% | 25.9–43.0 |
| **Pipeline, held-out items** | **72.7%** | 63.2–80.5 |

This is good news and it was missing: the pipeline more than doubles a non-trivial lexical
baseline. Cheap, and it fills the "no baselines of any kind" objection.

### 2.5 The judge finding is better than the paper's version (W3)

Score distributions on the same 115 items:

| Judge | Indicator→assertion | Assertion→question |
|---|---|---|
| Self (9B) | {1: 2, 2: 16, **5: 97**} | {4: 1, **5: 114**} |
| External (72B) | {1: 1, 2: 4, 3: 22, 4: 45, 5: 43} | {4: 51, 5: 64} |

**The 9B self-judge uses 3 of the 5 scale points and gives 97/115 fives on IA and 114/115 fives
on AQ.** It is not a lenient rater; it is a rubber stamp with almost no variance. Inter-judge
Pearson *r* = 0.52, exact agreement 40.9%.

This resolves the review's W3 confound in your favour: instead of the weak, confounded claim
"0.42–0.43 points of self-preference", report the strong claim **"a 9B judge is not a usable
measurement instrument — it is near-constant, so its mean is uninformative"**. That is a
methodological finding, not an artefact of model size.

One correction the paper needs: §7.4 currently says the external judge "discriminates more
sharply by correctness" than the self-judge. **That does not hold.** Mean IA gap between
concept-correct and concept-wrong items is **+0.39 for the self-judge** and **+0.26 for the
external judge**. Delete or rewrite that sentence.

### 2.6 The two unevaluated output fields (W8)

- **Question format**: 1 distinct value across 115 items ("direct interrogative (with WH word)"),
  in every run. The field is degenerate and cannot support any claim. Either drop it or report
  the degeneracy as a finding.
- **Answer options**: now scored. Mapping both gold and predictions to a coarse response-type
  taxonomy (open / ordinal / nominal / binary / ranked) gives **60.9% agreement** (70/115)
  [51.7–69.3]. Predictions over-produce ordinal scales (63 vs 50) and never produce binary or
  ranked formats (gold has 4 and 2).

---

## Part 3 — The LRZ job — ✅ DONE (2026-08-24, job 5760085)

Executed in one 5 h / 2-GPU allocation. All three stages completed; the log ends at `=== DONE`
with no errors. Two things had to be fixed mid-flight and are now in `run7.sh`:

- **`--max-model-len` 4096 → 8192** on the judge server. Stage 2 also *generates* on that
  server and the v7b prompt alone is 3573 tokens, so 4096 would have failed mid-run.
- **`stop_server` killed the wrapper `bash`, not `vllm serve`** (the server scripts pipe through
  `tee`). The orphaned server held ~90 GB and Stage 2 died with `Free memory on device cuda:0`.
  Servers now start with `setsid` and are signalled as a process group; `wait_gpu_free` polls
  until the GPUs are actually free instead of `sleep 20`.

Results: `docs/BASELINE_REPORT.md` § Run 7. Numbers: `docs/reanalysis.json`.

### Original instructions (kept for reference)

One allocation does all the GPU work: 3 ablation arms, the external judge on Run 6 and on the
new best arm, and the full 2×2 judge control. Script: `scripts/run7.sh`.

### Step 0 — push the changes from your Mac first

```bash
cd ~/Desktop/nlp-css-seminar
git checkout -b review-fixes
git add -A
git commit -m "Fix scoring bug, concepts.yaml parsing, prompt leakage; add re-analysis"
git push -u origin review-fixes
```

### Step 1 — connect and pull

```bash
ssh <username>@login.ai.lrz.de
tmux new -s run7                      # so the job survives a dropped connection
cd ~/nlp-css-seminar
git fetch origin && git checkout review-fixes && git pull
```

### Step 2 — validate the plumbing without a GPU (30 seconds, do not skip)

This catches a typo before you burn an allocation. It runs the whole pipeline with the mock
client, on 3 rows, for each of the three prompt arms.

```bash
source ~/nlp-css-seminar/scripts/activate_env.sh
cd ~/nlp-css-seminar
python test_normalize.py              # expect: normalize ok
python scripts/reanalysis.py          # expect: writes docs/reanalysis.json
bash -n scripts/run7.sh               # expect: no output

sed 's/mock: false/mock: true/' config.yaml > /tmp/mock.yaml
for arm in assertion_developer assertion_developer_v7a assertion_developer_v7b; do
  python -m src.sig.evaluation.run_eval --config /tmp/mock.yaml --tag "smoke_$arm" \
    --max-rows 3 --assertion-prompt "src/sig/prompts/$arm.md"
done
rm -f outputs/*smoke_*                # clean up the mock artifacts
```

Every arm should print an evaluation summary and write files to `outputs/`.

### Step 3 — submit the job

`run7.sh` requests **2 GPUs for 5 hours** (the 72B judge needs both; the 9B stages use one).

```bash
cd ~/nlp-css-seminar
mkdir -p outputs/logs
sbatch scripts/run7.sh
squeue -u $USER                       # note the JOBID
```

Watch it:

```bash
tail -f outputs/logs/run7_<JOBID>.log
```

If you would rather run it interactively (easier to debug, but you must stay connected):

```bash
salloc -p lrz-hgx-h100-94x4 --time=0-5:00:00 --gres=gpu:2 --cpus-per-task=16 --mem=96G
srun --jobid=<JOBID> --overlap --pty bash
source ~/nlp-css-seminar/scripts/activate_env.sh
cd ~/nlp-css-seminar && bash scripts/run7.sh
```

**What it does, in order:**

| Stage | Server | Produces | Answers |
|---|---|---|---|
| 1 | 9B, 1 GPU | `eval_report_vllm_v6repro_*` — current prompt on the repaired YAML | isolates §1.4 |
| 1 | 9B | `eval_report_vllm_v7a_*` — de-leaked examples | **W1**: the real cost of leakage |
| 1 | 9B | `eval_report_vllm_v7b_*` — + Norms/Policies/Causal rule | the targeted fix |
| 2 | 72B, 2 GPUs | `eval_report_ext_judge_run6_*` | **rec #1**: judge on the best config |
| 2 | 72B | `eval_report_ext_judge_v7b_*` | judge on the new best |
| 2 | 72B | `eval_report_vllm_gen72b_*` — 72B generates its own items | **W3** |
| 2 | 72B | `..._j72b_on_gen72b_*` — 72B judges itself | **W3** |
| 3 | 9B | `..._j9b_on_gen9b_*`, `..._j9b_on_gen72b_*` | **W3**: completes the 2×2 |

Each arm is **one** intervention on top of the previous one, which is what answers the review's
complaint that Run 2 bundled three changes at once.

The 2×2 is the part that settles W3. If the 72B rates its own generations higher than the 9B's
generations by roughly the same margin that the 9B favours itself, the effect is self-preference.
If instead the 72B is uniformly stricter on both, it is judge strictness, and the "self-grading
bias" framing has to go.

### Step 4 — collect the results

```bash
cd ~/nlp-css-seminar
ls -t outputs/eval_summary_* | head -12

# keep the artifacts the paper will cite
cp outputs/eval_report_vllm_v7b_*.csv       docs/baseline/
cp outputs/eval_summary_vllm_v7b_*.json     docs/baseline/
cp outputs/eval_report_vllm_v7a_*.csv       docs/baseline/
cp outputs/eval_summary_vllm_v7a_*.json     docs/baseline/
cp outputs/eval_report_vllm_v6repro_*.csv   docs/baseline/
cp outputs/eval_summary_vllm_v6repro_*.json docs/baseline/
cp outputs/eval_report_ext_judge_run6_*.csv docs/baseline/
cp outputs/eval_summary_ext_judge_run6_*.json docs/baseline/
cp outputs/*gen72b*.csv outputs/*gen72b*.json docs/baseline/
cp outputs/*j9b_on*.csv outputs/*j72b_on*.csv docs/baseline/

python scripts/reanalysis.py
python scripts/generate_figures.py --run-id <new v7b timestamp>

git add -A && git commit -m "Run 7: ablation arms, external judge on Run 6, 2x2 judge control"
git push
```

Then tell me and I will fold the numbers into the paper.

### Known caveats in the job

- `run7.sh` hardcodes `PROJECT_ROOT="${HOME}/nlp-css-seminar"` — correct for LRZ, adjust if your
  checkout lives elsewhere.
- When the 72B generates (stage 2), `_build_user_prompt` still appends `/no_think`, which is a
  Qwen3 control token and is inert for Qwen2.5. Harmless, but mention it if a reviewer asks why
  the prompts are not byte-identical across models.
- Stage 3 restarts the 9B server, which costs ~5 minutes. That is the price of the 2×2 without a
  third GPU.
- I was **not** able to smoke-test the arms locally, so Step 2 is the first real execution of the
  new `--assertion-prompt` / `--tag` / `--judge-model` flags. Run it.

---

## Part 4 — Paper edits still outstanding

### 4.1 Must change, no new data needed

> **Pass 1 complete (2026-08-24).** `Seminar_Paper/conference_101719.tex` +103/−46.
> Every stale number is updated and the one **contradicted** claim is removed. Audit for
> `76.5 / 75.7 / 73.9 / 57.4 / $115$` returns clean. Structural checks pass: no dangling
> refs, no duplicate labels, braces balanced, all 10 `tabular` column counts consistent.
> The 10 stale figure PDFs in `Seminar_Paper/` were refreshed — they were pre-Run-7 copies.
>
> **Not verified: the paper does not compile on the login node (no `pdflatex`).** The
> changelog table went 7 → 10 columns, so an overfull `hbox` is the realistic risk.
> Compile locally before submitting.
>
> Added during pass 1 because the paper would otherwise have been incoherent:
> Table VI (McNemar), Table VII (2×2), Fig. 15 (judge degeneracy), a Run 7 paragraph in §6,
> and three Run 7 columns in the changelog table.


| Where | Change |
|---|---|
| ✅ Abstract, §8, §10 | **Done.** Now leads with 85.0% / 79.6% on the de-leaked prompt and corrected n=113. Leakage is quantified separately (see 4.2) |
| ✅ Abstract | **Done.** Rounding consistent with the body throughout |
| ✅ §5.4, §7.1 | **Done.** Added as a defined metric in §5.4 and reported in §7.1: **93.8%** (90/96) vs **0.0%** (0/17) |
| ✅ §7.1, Table V | **Done.** Wilson CIs added under concept and structure; "our best configuration" removed from the Run 6 paragraph |
| ✅ §6 | **Done.** Split as 8.0 pp normalizer + 3.5 pp prompt; paired test reported as non-significant (p=0.503) |
| ✅ §7.4 | **Done.** Sentence removed and replaced with what the 2×2 supports |
| ✅ §7.4 | **Done.** Reframed around mid-scale occupancy (1% vs 38%) + Fig. 15. "0.42 and 0.43" used |
| ✅ §7.3 | **Done, and the claim is TRUE.** Traced Norms/Policies/Values across all 7 runs: Norms is 3/3 in R1–R3, collapses to 0/3 in R6, recovers to 3/3 in R7c, while Values moves 1/3→3/3 over the same interval. Added as Table X |
| ✅ §7.5 | **Done.** Now "including all 94 questions that do not exactly match", unhedged |
| ✅ §7.1 | **Done.** Now "nine concepts, namely …" (nine, not seven, at Run 7c) |
| ✅ Table VII | **Done.** Rebuilt on Run 7c as raw counts, with a note on why |
| ✅ Table II / App. A | **Done.** `v` and `(e)` added; `z` qualified as licensed-but-unused; Table II's Evaluative belief row updated to `xP(e)y`/`xP(e)`. **The review's `xDpl, pro` suggestion was wrong** — see note below |
| §4.6, App. F | ~~"Qwen3.5-9B" is not a real model name~~ **This was wrong** — `Qwen/Qwen3.5-9B` is real; the model card on disk confirms it (apache-2.0, post-trained, base `Qwen/Qwen3.5-9B-Base`). Name the exact checkpoints: generator `Qwen/Qwen3.5-9B`; judges `Qwen/Qwen2.5-72B-Instruct` (Run 5) and **`Qwen/Qwen3-32B` (Run 7)**. State that the 72B was deleted from the shared store mid-project, which is why the judge changed. Add the code URL that §10 promises. |
| ✅ §9 Limitations | **Done.** Rewritten, leading with "all reported numbers are in-sample"; adds leakage, the gold-set corrections, and the missing inter-annotator agreement |
| Whole doc | With `onecolumn`, `figure*`/`table*` are no-ops — simplify. Remove `\tableofcontents` if this goes anywhere but the seminar. |

### 4.2 New content to add

> **Pass 2 complete (2026-08-24).** `conference_101719.tex` now +184/−76 overall.
> Added Table VI (McNemar), Table VII (2×2 judge), Table VIII (baselines), Table IX
> (leakage split), Fig. 15 (judge degeneracy), the conditional-structure metric, and the
> W8 paragraph on the degenerate format field and the unscored answer options (61.1%).
>
> **One review claim turned out to be wrong.** The review suspected `$xDpl,\,pro$` for
> Procedures was a typo for `$xDpro$`, on the grounds that it collides with Place `$xDpl$`.
> It is not a typo: gold ids 59, 113 and 114 all use `xDpl, pro`, and `concepts.yaml`
> licenses it. A procedure is encoded as a deed situated at a place, further marked by
> `pro`; the codes are distinguished by the presence of `pro`, and scoring compares the full
> token, so they never collide. Renaming it would have corrupted the data. Added an
> explanatory footnote instead.
>
> **Still not verified: the paper does not compile here (no `pdflatex`).** Structural checks
> pass — no dangling refs, braces balanced, all tabular column counts consistent — but the
> changelog table is now 10 columns wide and needs a real compile.


- **Table: baselines** (majority 17.4%, lexical 1-NN 33.9%, pipeline 72.7%) — §7.1.
- **Table: leakage split** (all / in-prompt / held-out) — §5 or §7.1.
- **Table: McNemar** per transition — §7.1.
- **Judge distribution figure** — the {1,2,5} vs full-range histogram is the single most convincing
  figure you can add. `fig08`/`fig13` already have the data; a side-by-side version makes the point.
- **§2 literature**: engage the two 2025–26 papers the review names, and soften "to our knowledge,
  this framing has not previously been applied". Discuss **SQP** as the methodologically-native
  quality metric the framework's own authors built.

### 4.3 Pass 3 complete + the paper now compiles

> **Pass 3 done (2026-08-24).** Limitations rewritten (in-sample framing first, plus gold
> corrections and the IAA gap), future work reordered, §7.3 evidenced with a new cross-run
> table, and §2 literature engagement added with three new references.
>
> **The paper compiles.** No `pdflatex` on the login node and conda's `texlive-core` ships
> binaries with **zero** macro packages, so I installed `tectonic` instead.
> Result: **29 pages, 0 undefined citations, 0 undefined references, all 15 bib entries cited.**
> Only two overfull `hbox`es, both pre-existing (the abstract and the tikz pipeline diagram) —
> the 10-column changelog table does **not** overflow, so that earlier concern was unfounded.
> Note tectonic uses XeTeX; a pdfLaTeX build may differ slightly in font handling.
>
> Build: `conda activate tectonic && tectonic -X compile conference_101719.tex`

### 4.4 Two review claims that did NOT survive checking

1. **`$xDpl,\,pro$` is not a typo.** The review suspected it should be `$xDpro$` because it
   collides with Place `$xDpl$`. Gold ids 59, 113 and 114 all use `xDpl, pro` and
   `concepts.yaml` licenses it; scoring compares the full token, so they never collide.
   Renaming would have corrupted three gold items. Added an explanatory footnote instead.
2. **The CUI 2025 paper does not say what the review says it says.** The review describes
   Adhikari et al. as finding LLM-generated items "too broad, generic in wording, and lack
   specificity", and frames it as *contradicting* our near-ceiling judge scores. The
   published abstract reports the opposite: participants found LLM-generated text *clearer*
   and LLM-adapted questions *less biased* than traditional ones. We cite it accurately
   rather than repeating the review's framing. (Fetched from arXiv:2501.05985.)

   Worth noting the second new reference, Fuchs, Haensch and Weber (2026), is partly LMU —
   a natural point of contact.

### 4.3 Ratings this should move

| Criterion | Now | After Parts 1–4 |
|---|---|---|
| Statistical Rigor | 1/5 | 3–4/5 (CIs, McNemar, counts, leakage split) |
| Experimental Design | 2/5 | 3–4/5 (baselines, unbundled arms, held-out reporting, 2×2 control) |
| Soundness | 3/5 | 4/5 (leakage quantified, W3 resolved either way) |
| Novelty | 2/5 | 2–3/5 (only literature engagement + SQP moves this) |

---

## Part 5 — Decisions — ✅ 1 and 2 TAKEN (2026-08-24)

**1. Evaluative-belief notation — decided: standardise on `xP(e)y` / `xP(e)`.**
Gold id 3 relabelled from `xPyc`; `concepts.yaml` updated to license `xP(e)y` / `xP(e)`
instead of the phantom `xPy_e` / `xP_e`. The model predicts `xPyc` for all three
evaluative-belief items, so it is now scored **wrong on all three** — structure accuracy is
~0.9 pp *lower* than the alternative. That was the point: standardising on `xPyc` would have
raised the score by moving gold toward what the prompt already teaches.

> **Consequence, still open:** the assertion prompts now contradict the gold set. They inject
> `Evaluative belief → xP(e)y,xP(e)` from the YAML while their hand-written tables still teach
> `xPyc` in four places. The prompts were **deliberately not edited** — doing so would
> invalidate Run 6 and Run 7. Fixing this is **v7c** and needs a GPU: add
> `assertion_developer_v7c.md`, do not edit the existing files. Expected gain ~2.7 pp structure.

**2. Duplicate gold items — decided: drop both, n=113.**
Ids 71 and 67 are exact duplicates of 5 and 29 — identical indicator, concept *and* structure.
Id 71 was additionally one of the 16 prompt-leaked items, so keeping it double-counted a
memorised item. Applied to `data/gold_set.xlsx`; replayed onto existing reports by
`src/sig/gold_fixes.py` so no run had to be repeated on a GPU.

**3 and 4 remain open** — they need people, not compute:


1. **Evaluative-belief notation** (§1.5). Gold uses `xPyc` for id 3 and `xP(e)`/`xP(e)y` for ids
   107/108, the YAML licenses `xPy_e`/`xP_e`, and the prompt teaches `xPyc`. One of them has to
   win. Fixing gold's internal inconsistency is legitimate data cleaning, but it changes the
   numbers, so it is your call. Cheapest defensible option: standardise gold on `xP(e)y` / `xP(e)`,
   update the YAML and prompt to match, disclose it in §5.
2. **Duplicate gold items** (§1.6). Drop id 71 (and possibly 67), or keep and disclose? Dropping
   changes every denominator from 115 to 114/113.
3. **A genuinely new test set.** Nothing above fully fixes W1 — the *rules* in the prompt were
   still written while looking at these 115 items. The only complete fix is new items. If you and
   Lanre can annotate ~40 fresh indicators, that becomes a real held-out test set and moves
   Experimental Design to 4/5. I can generate candidate indicators across the 22 concepts for you
   to label, which cuts most of the work.
4. **Inter-annotator agreement** (W7). How many people built the gold set, and is there any
   double-annotated subset? If two of you can re-label ~30 items independently, that is a κ for
   §5.1 and closes the objection.

---

## Appendix — files changed

| File | Change |
|---|---|
| `src/sig/normalize.py` | Structure-code regex: keep `(…)` and `, pro`; require uppercase second symbol |
| `test_normalize.py` | **new** — regression test for the above |
| `data/concepts.yaml` | Fixed `structures`/`question_formats` parsing; merged duplicate `y`; added `v` and `(e)` |
| `src/sig/agents.py` | Assertion prompt path read from `config["prompts"]["assertion"]` |
| `src/sig/pipeline.py` | Question prompt path read from `config["prompts"]["question"]` |
| `src/sig/evaluation/run_eval.py` | argparse: `--assertion-prompt`, `--tag`, `--max-rows`, `--model`, `--base-url` |
| `scripts/run_judge_only.py` | argparse: `--judge-model`, `--judge-base-url`, `--tag` |
| `scripts/reanalysis.py` | **new** — the whole of Part 2; `--self-check` runs its assertions |
| `scripts/run7.sh` | **new** — the batched LRZ job |
| `src/sig/prompts/assertion_developer_v7a.md` | **new** — de-leaked worked examples |
| `src/sig/prompts/assertion_developer_v7b.md` | **new** — v7a + notation-derived deontic/causal rule |
| `docs/reanalysis.json` | **new** — machine-readable output of Part 2 |
| `Seminar_Paper/conference_101719.tex` | `ieeetr` bib style, removed empty Contributions, `[h]`→`[ht]` |

`src/sig/prompts/assertion_developer.md` is **unchanged**, so Run 6 stays reproducible.

### Added 2026-08-24 (Run 7 + gold-set correction)

| File | Change |
|---|---|
| `data/gold_set.xlsx` | n 115 → **113** (dropped duplicate ids 67, 71); id 3 structure `xPyc` → `xP(e)y` |
| `data/concepts.yaml` | Evaluative belief now licenses `xP(e)y` / `xP(e)` (was the phantom `xPy_e` / `xP_e`) |
| `src/sig/gold_fixes.py` | **new** — replays the gold corrections onto existing reports, so no run was repeated on a GPU |
| `config.yaml` | `judge.model` → Qwen3-32B |
| `scripts/start_vllm_judge.sh` | Judge model → Qwen3-32B; `--max-model-len` 4096 → **8192** (Stage 2 also generates on this server) |
| `scripts/run7.sh` | Judge → 32B; tags renamed; added `run4_32b` judge stage; **`setsid` process-group teardown + `wait_gpu_free`**; `RUN7_SKIP_STAGE1` resume |
| `scripts/reanalysis.py` | Run 7 arms added; per-arm prompt for the leakage split; 2×2 judge table; judge-swap and generator comparisons; corrections applied to every run |
| `scripts/generate_figures.py` | `EXT_JUDGE_NAME` constant; Run 7 arms in the progression; accuracy recomputed on corrected gold instead of the stale summaries |
| `docs/BASELINE_REPORT.md` | Run 7 changelog + results sections; corrected-results table; correction banner |
| `docs/PLAN.md`, `docs/PAPER_OUTLINE.md` | Run 7 progress entry; all headline numbers moved to n=113 |

**Do not quote `docs/baseline/eval_summary_*.json`** — they are stale at n=115.
`docs/reanalysis.json` is the single source of truth.
