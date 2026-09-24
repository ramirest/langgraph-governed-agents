# Diagnostic rubric — v1

This file is the rubric. It is versioned with the code because a rubric that
lives in a reviewer's head produces a score only that reviewer can reproduce,
and a score nobody else can reproduce is an opinion with a number on it.

Two things are scored separately, and they are not the same thing.

---

## 1. Groundedness (automated, gating)

Scored by `governance/groundedness.py` on every run. This is the structural
half: it asks whether a claim cites evidence that was actually retrieved, not
whether the evidence supports it.

A finding is **grounded** when both hold:

1. `evidence_ids` is non-empty.
2. Every id in `evidence_ids` appears in the chunks retrieved during this run.

`score = grounded_findings / total_findings`. A run with no findings scores 1.0:
finding nothing is a valid diagnostic result and should not be punished as if it
were a fabrication.

**Floor: 0.80** (`config.GROUNDEDNESS_FLOOR`). Below it the writer is skipped
and the run ends at the human gate with the failing claims listed.

Why 0.80 and not 1.0: a single finding that cites a chunk retrieved on an
earlier hop is a bug worth seeing, not a reason to throw away four good
findings. The threshold is a starting position, and it is a constant in one file
precisely so that moving it is a visible, reviewable change.

### What this does not catch

Citing a real chunk that does not support the claim passes this check. That is
semantic faithfulness, it needs judgement, and it is scored below.

---

## 2. Semantic faithfulness (judged, per case)

Scored by a human reviewer, or a judge model, against the golden cases in
`cases.yaml`. Four levels, applied per finding:

| Level | Meaning |
|-------|---------|
| **3 — supported** | The cited chunk states the claim, or states something the claim follows from directly. |
| **2 — partial** | The chunk is on topic and consistent with the claim, but the claim goes further than the text. |
| **1 — misattributed** | The chunk is real and retrieved, but does not bear on the claim. |
| **0 — invented** | The claim's substance appears nowhere in the corpus. |

A case passes at **mean ≥ 2.5 with no finding scored 0**. One invented claim
fails the case regardless of the mean: in a diagnostic delivered to an
institution, a single confident fabrication costs more than four vague
sentences.

---

## 3. Maturity level (deterministic)

`tools.score_maturity` folds findings into a 1-5 level, weighted by severity
(`low` 1, `medium` 2, `high` 3) because five cosmetic gaps are not one missing
data owner.

| Weighted gap score | Level | Label |
|--------------------|-------|-------|
| 0 | 5 | optimising |
| 1–2 | 4 | managed |
| 3–5 | 3 | defined |
| 6–9 | 2 | developing |
| 10+ | 1 | initial |

The arithmetic is trivial on purpose: a reviewer has to be able to redo it by
hand and get the same number, or the level is not defensible in the room where
it is presented.

---

## 4. Human review (gating, not scored)

No diagnostic is delivered without a person approving it. The gate is reached on
every path, including the failing one, and the reviewer sees the groundedness
score and the ungrounded claims next to the draft. With no reviewer attached the
gate refuses: the default has to be the safe one, because the default is what
runs at 2am when nobody configured anything.
