"""Gold-set corrections applied on 2026-08-24, and re-scoring of earlier runs.

Every eval report on disk was produced against the *uncorrected* 115-item gold
set. Rather than re-running the pipeline on a GPU just to change two labels and
drop two rows, the corrections are replayed here: the report's stale gold
columns are overwritten from the current gold set and the accuracy flags are
recomputed with the same normalizer the pipeline uses.

Two corrections, both decided deliberately and both disclosed in the paper:

1. Duplicates. Ids 71 and 67 are exact duplicates of 5 and 29 -- identical
   indicator, concept AND structure in both pairs. Id 71 is additionally one of
   the 16 items quoted verbatim in the v6 prompt, so leaving it in double-counts
   a memorised item in the headline accuracy. Dropped: n = 115 -> 113.

2. Evaluative-belief notation. Gold labelled three items of one concept three
   different ways (id 3 `xPyc`, id 107 `xP(e)`, id 108 `xP(e)y`) while
   concepts.yaml licensed a fourth pair (`xPy_e` / `xP_e`). Standardised on the
   notation-derived `(e)` form, so id 3 becomes `xP(e)y`.

   Note the direction: the prompt teaches `xPyc`, and the model predicts `xPyc`
   for all three items. Standardising on `xPyc` instead would have raised
   structure accuracy by ~1.7pp -- by moving gold toward what the prompt already
   teaches. That is why it was not done. The model is now scored wrong on all
   three, which is the honest reading: it does not yet produce the standard form.
"""

from __future__ import annotations

import pandas as pd

from src.sig.normalize import concepts_match, structures_match

# Exact duplicates; see (1) above.
EXCLUDED_EXAMPLE_IDS: tuple[int, ...] = (67, 71)

# Applied to the gold set itself; kept here so the re-scoring of older reports
# is self-documenting rather than depending on when the .xlsx was edited.
GOLD_STRUCTURE_OVERRIDES: dict[int, str] = {3: "xP(e)y"}

N_ITEMS = 113


def apply_gold_corrections(df: pd.DataFrame, gold: pd.DataFrame) -> pd.DataFrame:
    """Re-score one eval report against the corrected gold set.

    Drops the duplicate items, refreshes the gold columns from `gold` (which
    already carries the overrides), and recomputes concept/structure accuracy.
    Safe to call on a report that was generated *after* the corrections: the
    drop is a no-op and the recomputation is idempotent.
    """
    out = df[~df["example_id"].isin(EXCLUDED_EXAMPLE_IDS)].copy()

    valid_concepts = sorted(set(gold["basic_concept"]))
    by_id = gold.set_index("example_id")
    out["gold_concept"] = out["example_id"].map(by_id["basic_concept"])
    out["gold_structure"] = out["example_id"].map(by_id["semantic_structure"])

    out["concept_accuracy"] = [
        concepts_match(g, p, valid_concepts)
        for g, p in zip(out["gold_concept"], out["pred_concept"].fillna(""))
    ]
    out["structure_accuracy"] = [
        structures_match(g, p)
        for g, p in zip(out["gold_structure"], out["pred_structure"].fillna(""))
    ]
    return out.reset_index(drop=True)
