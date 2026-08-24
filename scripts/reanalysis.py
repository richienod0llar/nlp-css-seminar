#!/usr/bin/env python3
"""Offline re-analysis of the existing eval runs (no LLM calls, no GPU).

Produces the numbers the paper review asks for:
  W1  few-shot leakage split (items quoted verbatim in the prompt vs the rest)
  W2  structure accuracy conditional on a correct concept
  W4  Wilson 95% CIs on every headline; exact McNemar between runs; per-concept counts
  W5  Run 1 re-scored under the current normalizer (isolates the spelling fix)
  W6  no-LLM baselines: majority class + leave-one-out lexical nearest neighbour
  W8  answer-option response-type agreement; question-format degeneracy

Usage: python scripts/reanalysis.py [--out-dir docs/]
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.sig.normalize import concepts_match, extract_structure_code, structures_match

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "docs" / "baseline"

# Run label -> per-item report CSV. Runs 4 and 5 reuse Run 3 generations (judge-only passes).
# The v* arms are Run 7 (2026-08-24): one intervention each, so consecutive
# McNemar tests isolate the YAML repair, the de-leaking, and the notation rule.
RUNS = {
    "Run 1": BASELINE / "eval_report_vllm_20260620_185119.csv",
    "Run 2": BASELINE / "eval_report_vllm_20260620_194152.csv",
    "Run 3": BASELINE / "eval_report_vllm_20260625_134833.csv",
    "Run 6": BASELINE / "eval_report_vllm_20260703_180434.csv",
    "v6repro": BASELINE / "eval_report_vllm_v6repro_20260824_101855.csv",
    "v7a": BASELINE / "eval_report_vllm_v7a_20260824_102619.csv",
    "v7b": BASELINE / "eval_report_vllm_v7b_20260824_103350.csv",
}

# Each arm was generated under a DIFFERENT prompt, so the leakage split has to
# be computed against the prompt that actually produced the run. De-leaking the
# worked examples is the whole point of v7a; scoring it against the v6 prompt
# would report leakage that is no longer there.
RUN_PROMPTS = {
    "v7a": "assertion_developer_v7a.md",
    "v7b": "assertion_developer_v7b.md",
}
DEFAULT_PROMPT = "assertion_developer.md"

# Qwen2.5-72B-Instruct was deleted from the shared model store after Run 5, so
# Run 7 re-judged the SAME Run 4 predictions with Qwen3-32B. Keeping both makes
# the judge swap itself measurable instead of a silent change of instrument.
EXT_JUDGE = BASELINE / "eval_report_ext_judge_run4_32b_vllm_20260625_160020_20260824_110758.csv"
EXT_JUDGE_OLD = BASELINE / "eval_report_ext_judge_20260703_171851.csv"

# W3, the 2x2: generator x judge on the same 115 items. Separates "a model
# prefers its own output" from "a bigger judge is simply stricter".
JUDGE_2X2 = {
    ("gen9b", "judge32b"): BASELINE / "eval_report_ext_judge_v7b_vllm_v7b_20260824_103350_20260824_112633.csv",
    ("gen9b", "judge9b"): BASELINE / "eval_report_ext_judge_j9b_on_gen9b_vllm_v7b_20260824_103350_20260824_115228.csv",
    ("gen32b", "judge32b"): BASELINE / "eval_report_ext_judge_j32b_on_gen32b_vllm_gen32b_20260824_113423_20260824_114348.csv",
    ("gen32b", "judge9b"): BASELINE / "eval_report_ext_judge_j9b_on_gen32b_vllm_gen32b_20260824_113423_20260824_120021.csv",
}
GEN32B = BASELINE / "eval_report_vllm_gen32b_20260824_113423.csv"
BEST = "v7b"


# --------------------------------------------------------------------------
# statistics (stdlib only -- no statsmodels/scipy dependency for four formulas)
# --------------------------------------------------------------------------

def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion, as percentages."""
    if n == 0:
        return (0.0, 0.0)
    centre = (k + z * z / 2) / (n + z * z)
    half = z / (n + z * z) * math.sqrt(k * (n - k) / n + z * z / 4)
    return (round(max(0.0, centre - half) * 100, 1), round(min(1.0, centre + half) * 100, 1))


def mcnemar_exact(before: pd.Series, after: pd.Series) -> dict:
    """Exact (binomial) McNemar test on paired per-item correctness."""
    b = int((before & ~after).sum())  # fixed -> broken
    c = int((~before & after).sum())  # broken -> fixed
    n = b + c
    if n == 0:
        return {"b": 0, "c": 0, "p": 1.0}
    lo = min(b, c)
    tail = sum(math.comb(n, i) for i in range(lo + 1)) / (2 ** n)
    return {"b": b, "c": c, "p": round(min(1.0, 2 * tail), 4)}


def pct(series: pd.Series) -> float:
    return round(series.mean() * 100, 1)


def rate(series: pd.Series) -> dict:
    """Percentage + count + Wilson CI, the way small-n cells should be reported."""
    k, n = int(series.sum()), len(series)
    return {"pct": pct(series), "k": k, "n": n, "ci95": wilson(k, n)}


# --------------------------------------------------------------------------
# W1: which gold items are quoted verbatim in the prompts?
# --------------------------------------------------------------------------

def _key(text: str) -> str:
    return re.sub(r"\W+", "", str(text).lower())


def fewshot_gold_ids(gold: pd.DataFrame, prompt_name: str = DEFAULT_PROMPT) -> list[int]:
    """Gold example_ids whose indicator appears verbatim as a worked example."""
    prompt = (ROOT / "src" / "sig" / "prompts" / prompt_name).read_text(encoding="utf-8")
    quoted = {_key(m) for m in re.findall(r"Input Indicator:\n(.+)", prompt)}
    return sorted(int(r.example_id) for r in gold.itertuples() if _key(r.input_indicator) in quoted)


# --------------------------------------------------------------------------
# W5: re-score an old run under today's normalizer
# --------------------------------------------------------------------------

def rescore(df: pd.DataFrame, valid_concepts: list[str]) -> pd.DataFrame:
    out = df.copy()
    out["concept_accuracy"] = [
        concepts_match(g, p, valid_concepts)
        for g, p in zip(df["gold_concept"], df["pred_concept"].fillna(""))
    ]
    out["structure_accuracy"] = [
        structures_match(g, p)
        for g, p in zip(df["gold_structure"], df["pred_structure"].fillna(""))
    ]
    return out


# --------------------------------------------------------------------------
# W6: baselines that use no LLM at all
# --------------------------------------------------------------------------

def baselines(gold: pd.DataFrame) -> dict:
    """Majority class and leave-one-out lexical nearest neighbour over indicators."""
    from sklearn.feature_extraction.text import TfidfVectorizer

    concepts = gold["basic_concept"].tolist()
    structures = [extract_structure_code(s) for s in gold["semantic_structure"]]
    majority = max(set(concepts), key=concepts.count)

    tfidf = TfidfVectorizer(sublinear_tf=True, ngram_range=(1, 2), stop_words="english")
    matrix = tfidf.fit_transform(gold["input_indicator"].astype(str))
    sim = (matrix @ matrix.T).toarray()
    for i in range(len(sim)):
        sim[i, i] = -1.0  # leave-one-out: an item may not retrieve itself
    nn = sim.argmax(axis=1)

    nn_concept = pd.Series([concepts[j] == concepts[i] for i, j in enumerate(nn)])
    nn_structure = pd.Series([structures[j] == structures[i] for i, j in enumerate(nn)])
    return {
        "majority_class": {"label": majority, **rate(pd.Series([c == majority for c in concepts]))},
        "lexical_1nn_concept": rate(nn_concept),
        "lexical_1nn_structure": rate(nn_structure),
    }


# --------------------------------------------------------------------------
# W8: response-type taxonomy for answer options
# --------------------------------------------------------------------------

def option_type(raw: str) -> str:
    """Coarse response format, so predicted and gold options are comparable."""
    text = str(raw or "").strip().lower()
    if not text or text == "nan":
        return "(empty)"
    if "open-ended" in text or "open ended" in text:
        return "open"
    if "rank" in text:
        return "ranked"
    if re.fullmatch(r"yes\s*/\s*no|yes or no|yes, no", text):
        return "binary"
    if any(w in text for w in ("scale", "likert", "strongly", "very ", "not at all", "extremely")):
        return "ordinal"
    if "–" in text or "-" in text or " to " in text:
        return "ordinal"
    return "nominal"


# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=ROOT / "docs")
    args = ap.parse_args()

    gold = pd.read_excel(ROOT / "data" / "gold_set.xlsx")
    valid_concepts = sorted(set(gold["basic_concept"]))
    runs = {label: pd.read_csv(path) for label, path in RUNS.items() if path.exists()}
    best = runs[BEST]
    leak_ids = fewshot_gold_ids(gold, RUN_PROMPTS.get(BEST, DEFAULT_PROMPT))
    report: dict = {"fewshot_gold_ids": leak_ids, "best_run": BEST}

    # --- W1: how much leakage does each arm's own prompt carry? ------------
    report["leakage_by_arm"] = {}
    for label in ("v6repro", "v7a", "v7b"):
        if label not in runs:
            continue
        ids = fewshot_gold_ids(gold, RUN_PROMPTS.get(label, DEFAULT_PROMPT))
        df = runs[label]
        seen_arm = df["example_id"].isin(ids)
        report["leakage_by_arm"][label] = {
            "prompt": RUN_PROMPTS.get(label, DEFAULT_PROMPT),
            "n_leaked_gold_items": len(ids),
            "leaked_ids": ids,
            "concept_in_prompt": rate(df.loc[seen_arm, "concept_accuracy"]) if seen_arm.any() else None,
            "concept_held_out": rate(df.loc[~seen_arm, "concept_accuracy"]),
            "both_in_prompt": rate(df.loc[seen_arm, "concept_accuracy"].astype(bool)
                                   & df.loc[seen_arm, "structure_accuracy"].astype(bool)) if seen_arm.any() else None,
            "both_held_out": rate(df.loc[~seen_arm, "concept_accuracy"].astype(bool)
                                  & df.loc[~seen_arm, "structure_accuracy"].astype(bool)),
        }

    # --- W1: leakage split -------------------------------------------------
    seen = best["example_id"].isin(leak_ids)
    report["leakage_split"] = {}
    for name, sub in (("all", best), ("in_prompt", best[seen]), ("held_out", best[~seen])):
        report["leakage_split"][name] = {
            "concept": rate(sub["concept_accuracy"]),
            "structure": rate(sub["structure_accuracy"]),
            "both": rate(sub["concept_accuracy"] & sub["structure_accuracy"]),
        }

    # --- W2: conditional structure accuracy --------------------------------
    ok = best["concept_accuracy"].astype(bool)
    report["conditional_structure"] = {
        "given_concept_correct": rate(best.loc[ok, "structure_accuracy"]),
        "given_concept_wrong": rate(best.loc[~ok, "structure_accuracy"]),
    }

    # --- W4: CIs per run + McNemar between consecutive runs ----------------
    report["per_run"] = {
        label: {
            "concept": rate(df["concept_accuracy"]),
            "structure": rate(df["structure_accuracy"]),
            "both": rate(df["concept_accuracy"].astype(bool) & df["structure_accuracy"].astype(bool)),
            "question_exact_match": rate(df["question_exact_match"]),
        }
        for label, df in runs.items()
    }
    labels = list(runs)
    report["mcnemar"] = {
        f"{a} -> {b}": {
            metric: mcnemar_exact(
                runs[a].set_index("example_id")[metric].astype(bool),
                runs[b].set_index("example_id")[metric].astype(bool),
            )
            for metric in ("concept_accuracy", "structure_accuracy")
        }
        for a, b in zip(labels, labels[1:])
    }

    # --- W4: per-concept cells as counts -----------------------------------
    report["per_concept"] = {
        str(concept): {
            "n": len(grp),
            "concept": f"{int(grp['concept_accuracy'].sum())}/{len(grp)}",
            "structure": f"{int(grp['structure_accuracy'].sum())}/{len(grp)}",
            "concept_ci95": wilson(int(grp["concept_accuracy"].sum()), len(grp)),
        }
        for concept, grp in best.groupby("gold_concept")
    }

    # --- W5: decompose Run 2 (spelling normalizer vs prompt work) ----------
    r1 = runs["Run 1"]
    r1_rescored = rescore(r1, valid_concepts)
    report["run1_rescored_under_current_normalizer"] = {
        "as_reported": rate(r1["concept_accuracy"]),
        "rescored": rate(r1_rescored["concept_accuracy"]),
        "delta_pp_from_normalizer": round(
            pct(r1_rescored["concept_accuracy"]) - pct(r1["concept_accuracy"]), 1
        ),
        "run2_total_delta_pp": round(
            pct(runs["Run 2"]["concept_accuracy"]) - pct(r1["concept_accuracy"]), 1
        ),
    }

    # --- W6: baselines -----------------------------------------------------
    report["baselines"] = baselines(gold)

    # --- W3: judge agreement ------------------------------------------------
    if EXT_JUDGE.exists():
        ej = pd.read_csv(EXT_JUDGE)
        pairs = ej.dropna(subset=["indicator_assertion_score", "ext_indicator_assertion_score"])
        correct = pairs["concept_accuracy"].astype(bool)
        report["judge"] = {
            "mean_self_ia": round(pairs["indicator_assertion_score"].mean(), 2),
            "mean_ext_ia": round(pairs["ext_indicator_assertion_score"].mean(), 2),
            "pearson_r_ia": round(
                pairs["indicator_assertion_score"].corr(pairs["ext_indicator_assertion_score"]), 3
            ),
            "exact_agreement_ia_pct": pct(
                pairs["indicator_assertion_score"] == pairs["ext_indicator_assertion_score"]
            ),
            "self_ia_gap_correct_minus_wrong": round(
                pairs.loc[correct, "indicator_assertion_score"].mean()
                - pairs.loc[~correct, "indicator_assertion_score"].mean(),
                2,
            ),
            "ext_ia_gap_correct_minus_wrong": round(
                pairs.loc[correct, "ext_indicator_assertion_score"].mean()
                - pairs.loc[~correct, "ext_indicator_assertion_score"].mean(),
                2,
            ),
        }

    # --- W3: the 2x2, generator x judge ------------------------------------
    cells = {}
    for (gen, judge), path in JUDGE_2X2.items():
        if not path.exists():
            continue
        df = pd.read_csv(path)
        ia = pd.to_numeric(df["ext_indicator_assertion_score"], errors="coerce").dropna()
        aq = pd.to_numeric(df["ext_assertion_question_score"], errors="coerce").dropna()
        cells[f"{gen}/{judge}"] = {
            "mean_ia": round(ia.mean(), 2),
            "mean_aq": round(aq.mean(), 2),
            # A judge that cannot return a parseable score is itself a finding.
            "n_scored_ia": int(len(ia)),
            "n_rows": int(len(df)),
            "ia_distribution": {str(k): int(v) for k, v in sorted(ia.round().astype(int).value_counts().items())},
            "distinct_ia_values": int(ia.round().nunique()),
        }
    if cells:
        report["judge_2x2"] = cells
        def _m(key):
            return cells[key]["mean_ia"] if key in cells else None
        # Self-preference would show as each judge scoring ITS OWN generator
        # higher. A pure judge main effect shows as both columns shifting together.
        report["judge_effects"] = {
            "self_preference_9b": None if None in (_m("gen9b/judge9b"), _m("gen32b/judge9b"))
                else round(_m("gen9b/judge9b") - _m("gen32b/judge9b"), 2),
            "self_preference_32b": None if None in (_m("gen32b/judge32b"), _m("gen9b/judge32b"))
                else round(_m("gen32b/judge32b") - _m("gen9b/judge32b"), 2),
            "judge_leniency_9b_minus_32b_on_gen9b": None if None in (_m("gen9b/judge9b"), _m("gen9b/judge32b"))
                else round(_m("gen9b/judge9b") - _m("gen9b/judge32b"), 2),
        }

    # --- W3: did swapping the judge model change the instrument? -----------
    if EXT_JUDGE.exists() and EXT_JUDGE_OLD.exists():
        swap = {}
        for name, path in (("qwen3_32b", EXT_JUDGE), ("qwen2.5_72b", EXT_JUDGE_OLD)):
            df = pd.read_csv(path)
            ia = pd.to_numeric(df["ext_indicator_assertion_score"], errors="coerce").dropna()
            swap[name] = {
                "mean_ia": round(ia.mean(), 2),
                "ia_distribution": {str(k): int(v) for k, v in sorted(ia.round().astype(int).value_counts().items())},
                "distinct_ia_values": int(ia.round().nunique()),
            }
        swap["note"] = ("Same 115 Run 4 predictions under both judges. The 32B is the more "
                        "lenient instrument; the gap cannot be decomposed because the 72B "
                        "is no longer available.")
        report["judge_swap"] = swap

    # --- generator comparison: does a bigger GENERATOR help? ---------------
    if GEN32B.exists() and "v7b" in runs:
        g32 = pd.read_csv(GEN32B)
        report["generator_comparison"] = {
            "gen9b_v7b": {
                "concept": rate(runs["v7b"]["concept_accuracy"]),
                "structure": rate(runs["v7b"]["structure_accuracy"]),
                "both": rate(runs["v7b"]["concept_accuracy"].astype(bool) & runs["v7b"]["structure_accuracy"].astype(bool)),
            },
            "gen32b_v7b": {
                "concept": rate(g32["concept_accuracy"]),
                "structure": rate(g32["structure_accuracy"]),
                "both": rate(g32["concept_accuracy"].astype(bool) & g32["structure_accuracy"].astype(bool)),
            },
            "mcnemar_concept": mcnemar_exact(
                runs["v7b"].set_index("example_id")["concept_accuracy"].astype(bool),
                g32.set_index("example_id")["concept_accuracy"].astype(bool),
            ),
        }

    # --- W8: options + format ----------------------------------------------
    gold_by_id = gold.set_index("example_id")
    gold_types = best["example_id"].map(lambda i: option_type(gold_by_id.loc[i, "answer_options"]))
    pred_types = best["pred_options"].map(option_type)
    report["answer_options"] = {
        "response_type_agreement": rate(pd.Series((gold_types == pred_types).values)),
        "gold_distribution": gold_types.value_counts().to_dict(),
        "pred_distribution": pred_types.value_counts().to_dict(),
    }
    report["question_format"] = {
        "distribution": best["pred_format_normalized"].value_counts().to_dict(),
        "distinct_values": int(best["pred_format_normalized"].nunique()),
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out = args.out_dir / "reanalysis.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    ls = report["leakage_split"]
    print(f"Best run: {BEST}  (prompt {RUN_PROMPTS.get(BEST, DEFAULT_PROMPT)})")
    print(f"Few-shot gold items quoted in that prompt: {len(leak_ids)} -> {leak_ids}")
    print(f"  all 115      concept {ls['all']['concept']['pct']}%  CI {ls['all']['concept']['ci95']}")
    if leak_ids:
        print(f"  in prompt    concept {ls['in_prompt']['concept']['pct']}%  (n={ls['in_prompt']['concept']['n']})")
        print(f"  held out     concept {ls['held_out']['concept']['pct']}%  CI {ls['held_out']['concept']['ci95']}")
    else:
        print("  (prompt is de-leaked: no gold item appears verbatim, so there is no split)")
    leaky = report.get("leakage_by_arm", {}).get("v6repro")
    if leaky and leaky["concept_in_prompt"]:
        print(f"  leaked-prompt arm v6repro: in-prompt {leaky['concept_in_prompt']['pct']}% "
              f"(n={leaky['concept_in_prompt']['n']}) vs held-out {leaky['concept_held_out']['pct']}% "
              f"(n={leaky['concept_held_out']['n']})")
    cs = report["conditional_structure"]
    print(f"P(structure | concept correct) = {cs['given_concept_correct']['pct']}%  "
          f"vs {cs['given_concept_wrong']['pct']}% when wrong")
    b = report["baselines"]
    print(f"Baselines: majority {b['majority_class']['pct']}%  lexical-1NN {b['lexical_1nn_concept']['pct']}%")
    print(f"Answer-option type agreement: {report['answer_options']['response_type_agreement']['pct']}%")

    if "leakage_by_arm" in report:
        print("\nLeakage carried by each arm's own prompt:")
        for label, d in report["leakage_by_arm"].items():
            print(f"  {label:<9} {d['n_leaked_gold_items']:>2} leaked gold items "
                  f"({d['prompt']})")
    if "judge_2x2" in report:
        print("\n2x2 generator x judge (mean indicator->assertion):")
        for cell, d in report["judge_2x2"].items():
            print(f"  {cell:<18} {d['mean_ia']:>5}   scored {d['n_scored_ia']}/{d['n_rows']}"
                  f"   dist {d['ia_distribution']}")
        for k, v in report["judge_effects"].items():
            print(f"  {k}: {v:+}" if v is not None else f"  {k}: n/a")
    if "judge_swap" in report:
        print("\nJudge swap on identical Run 4 predictions:")
        for name in ("qwen2.5_72b", "qwen3_32b"):
            d = report["judge_swap"][name]
            print(f"  {name:<12} mean {d['mean_ia']}   dist {d['ia_distribution']}")
    if "generator_comparison" in report:
        gc = report["generator_comparison"]
        print(f"\nGenerator: 9B {gc['gen9b_v7b']['both']['pct']}% both-correct "
              f"vs 32B {gc['gen32b_v7b']['both']['pct']}%  (McNemar p={gc['mcnemar_concept']['p']})")
    print(f"\nWrote {out}")


def _self_check() -> None:
    assert wilson(88, 115) == (68.0, 83.3), wilson(88, 115)
    assert wilson(0, 3)[0] == 0.0
    assert mcnemar_exact(pd.Series([True] * 12), pd.Series([False] * 12))["p"] < 0.001
    assert mcnemar_exact(pd.Series([True, False]), pd.Series([True, False]))["p"] == 1.0
    assert option_type("Open-ended") == "open" and option_type("Yes/No") == "binary"
    assert option_type("Very unlikely–Very likely") == "ordinal"
    assert option_type("Department list") == "nominal"
    print("self-check ok")


if __name__ == "__main__":
    if "--self-check" in sys.argv:
        _self_check()
    else:
        main()
