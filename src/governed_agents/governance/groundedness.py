"""Groundedness scoring against a written rubric.

The rubric lives in evals/rubric.md, versioned alongside the code, because a
rubric that lives in one reviewer's head produces a score only that reviewer
can reproduce.

What is scored here is structural, not semantic: does every claim cite evidence
that was actually retrieved in this run? That check is cheap, deterministic and
catches the failure that matters most in a diagnostic, which is a confident
finding with nothing behind it. Semantic faithfulness (does the evidence really
support the claim?) is the judged half and belongs in evals/, where a human or a
judge model scores the golden cases.
"""
from typing import Dict, Iterable, List, Sequence

from governed_agents.config import GROUNDEDNESS_FLOOR
from governed_agents.state import Finding


def score_groundedness(
    findings: Sequence[Finding],
    retrieved: Iterable[Dict[str, str]],
) -> Dict[str, object]:
    """Fraction of findings whose evidence ids all came from this run's retrieval.

    Returns the score, the floor it was measured against, whether it passed, and
    the findings that failed, so a reviewer sees what to look at rather than a
    bare number.
    """
    available = {chunk["id"] for chunk in retrieved}
    ungrounded: List[str] = []

    for finding in findings:
        ids = finding.get("evidence_ids") or []
        if not ids or not set(ids).issubset(available):
            ungrounded.append(finding["claim"])

    total = len(findings)
    score = 1.0 if total == 0 else (total - len(ungrounded)) / total

    return {
        "score": round(score, 4),
        "floor": GROUNDEDNESS_FLOOR,
        "passed": score >= GROUNDEDNESS_FLOOR,
        "ungrounded_claims": ungrounded,
        "n_findings": total,
    }
