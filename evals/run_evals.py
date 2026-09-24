#!/usr/bin/env python3
"""Run the golden cases in cases.yaml against the graph.

This is the regression suite: the thing that re-runs when a prompt, a model or a
threshold changes and tells you whether the governance guarantees still hold. It
runs offline against StubModel, so it costs nothing and can sit in CI, which is
the only reason a suite like this survives past its first month.

Usage:
    python evals/run_evals.py            # run all cases
    python evals/run_evals.py --json     # machine-readable
"""
import argparse
import json
import os
import sys

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from governed_agents.agents.base import StubModel  # noqa: E402
from governed_agents.graph import build_graph  # noqa: E402
from governed_agents.rag.store import DocumentStore  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, "..", "data", "sample_org")
CASES = os.path.join(HERE, "cases.yaml")

DEFAULT_COST = 0.01
DRAFT = "1. Assign a named owner. 2. Add a revocation path. 3. Automate checks."


def _reviewer(mode):
    if mode == "reject":
        return lambda _state: (False, "scope does not match the engagement")
    return lambda _state: (True, "reviewed and approved")


def run_case(case, store):
    """Execute one case and return (passed, observed, failures)."""
    models = {
        # The retriever's scripted response is the search query it would have
        # written. Cases pass the question through verbatim so the retrieval
        # under test is the store's, not a rewrite's.
        "retriever": StubModel(
            [case["question"]], cost_per_call=case.get("retriever_cost", DEFAULT_COST)
        ),
        "analyst": StubModel(
            [case.get("findings", [])], cost_per_call=case.get("analyst_cost", DEFAULT_COST)
        ),
        "writer": StubModel(
            [DRAFT], cost_per_call=case.get("writer_cost", DEFAULT_COST)
        ),
    }

    app = build_graph(store, models, review=_reviewer(case.get("reviewer", "approve")))
    final = app.invoke({"question": case["question"], "spend": {}})

    grounding = final.get("groundedness") or {}
    observed = {
        "halted": bool(final.get("halted_reason")),
        "halted_reason": final.get("halted_reason"),
        "groundedness_passed": grounding.get("passed"),
        "groundedness_score": grounding.get("score"),
        "ungrounded_claims": grounding.get("ungrounded_claims", []),
        "approved": final.get("approved"),
        "reviewer_note": final.get("reviewer_note"),
        "roadmap_written": bool(final.get("roadmap")),
        "maturity_level": (final.get("maturity") or {}).get("level"),
        "spend": final.get("spend", {}),
    }

    failures = []
    for key, expected in (case.get("expect") or {}).items():
        actual = observed.get(key)
        if actual != expected:
            failures.append("%s: expected %r, got %r" % (key, expected, actual))

    return (not failures), observed, failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    store = DocumentStore(CORPUS)
    with open(CASES, "r", encoding="utf-8") as handle:
        cases = yaml.safe_load(handle)

    results = []
    for case in cases:
        passed, observed, failures = run_case(case, store)
        results.append(
            {"id": case["id"], "passed": passed, "failures": failures, "observed": observed}
        )

    failed = [r for r in results if not r["passed"]]

    if args.json:
        print(json.dumps({"total": len(results), "failed": len(failed), "cases": results}, indent=2))
    else:
        for r in results:
            mark = "PASS" if r["passed"] else "FAIL"
            o = r["observed"]
            score = o["groundedness_score"]
            print(
                "%-4s %-28s groundedness=%s approved=%s%s"
                % (
                    mark,
                    r["id"],
                    "n/a" if score is None else "%.2f" % score,
                    o["approved"],
                    "  halted: %s" % o["halted_reason"] if o["halted"] else "",
                )
            )
            for failure in r["failures"]:
                print("       - %s" % failure)
        print("\n%d/%d cases passed" % (len(results) - len(failed), len(results)))

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
