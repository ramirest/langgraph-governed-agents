"""Tool implementations.

Two tools, both deterministic and offline. They are the objects the permission
grants in config.py refer to: `search_documents` reads the corpus,
`score_maturity` applies the rubric's levels to a set of findings.

Determinism is the point. When a tool is deterministic, a failing eval case
means the agent behaved differently, not that the tool drifted.
"""
from typing import Callable, Dict, List, Sequence

from governed_agents.rag.store import DocumentStore
from governed_agents.state import Finding

# evals/rubric.md is the written version of this table. Keep them in step.
SEVERITY_WEIGHT = {"low": 1, "medium": 2, "high": 3}

MATURITY_LEVELS = {
    5: "optimising",
    4: "managed",
    3: "defined",
    2: "developing",
    1: "initial",
}


def score_maturity(findings: Sequence[Finding]) -> Dict[str, object]:
    """Map findings onto a 1-5 maturity level.

    Weighted by severity, because five cosmetic gaps are not one missing data
    owner. The arithmetic is trivial on purpose: a reviewer has to be able to
    redo it by hand and get the same number, or the score is not defensible.
    """
    weight = sum(SEVERITY_WEIGHT.get(f.get("severity", "low"), 1) for f in findings)

    if weight == 0:
        level = 5
    elif weight <= 2:
        level = 4
    elif weight <= 5:
        level = 3
    elif weight <= 9:
        level = 2
    else:
        level = 1

    return {
        "level": level,
        "label": MATURITY_LEVELS[level],
        "weighted_gap_score": weight,
        "n_findings": len(findings),
    }


def make_tools(store: DocumentStore) -> Dict[str, Callable]:
    """The tool registry handed to every agent.

    Every agent receives the same registry; what differs is the grant. That is
    deliberate: the grant is the single place permissions are expressed, so
    there is one thing to read when asking what an agent can reach.
    """

    def search_documents(query: str, k: int = 4) -> List[Dict[str, str]]:
        return store.search(query, k=k)

    return {
        "search_documents": search_documents,
        "score_maturity": score_maturity,
    }
