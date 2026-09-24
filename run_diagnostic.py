#!/usr/bin/env python3
"""Run one diagnostic and print the whole trace.

    python run_diagnostic.py                      # offline, scripted findings
    python run_diagnostic.py "your question"      # offline, your question
    python run_diagnostic.py --live "question"    # real model, needs ANTHROPIC_API_KEY
    python run_diagnostic.py --invent             # see an ungrounded claim blocked
    python run_diagnostic.py --reject             # see the human gate decline

The offline path scripts the model's outputs so the run is deterministic. It
still exercises the real retriever, the real permission checks, the real
ceilings, the real scorer and the real gate — which is the point: the governance
layer does not know or care whether a model or a stub produced the findings.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from governed_agents.agents.base import StubModel  # noqa: E402
from governed_agents.config import BUDGET_CEILING_USD, GROUNDEDNESS_FLOOR  # noqa: E402
from governed_agents.graph import build_graph  # noqa: E402
from governed_agents.rag.store import DocumentStore  # noqa: E402

CORPUS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sample_org")

DEFAULT_QUESTION = (
    "fare collection dataset named owner warehouse access revocation "
    "automated quality checks"
)

# What the analyst "found", for the offline run. All three cite chunks the
# retriever actually returns, so the default run clears the floor. Pass --invent
# to append one that does not, and watch the writer get skipped.
SCRIPTED_FINDINGS = [
    {
        "claim": "The fare-collection dataset has no named owner while three teams write to it.",
        "evidence_ids": ["data-governance#1"],
        "severity": "high",
    },
    {
        "claim": "Warehouse access is per person with no revocation path; 12 accounts belong to people who have left.",
        "evidence_ids": ["data-governance#3"],
        "severity": "high",
    },
    {
        "claim": "There are no automated quality checks; errors surface through downstream consumers.",
        "evidence_ids": ["data-governance#4"],
        "severity": "medium",
    },
]

SCRIPTED_ROADMAP = """1. Name an owner for the fare-collection dataset and record it in the handbook.
2. Introduce a role layer for warehouse access and revoke the 12 dormant accounts.
3. Add automated quality checks to the nightly load, starting with row counts and null rates."""


INVENTED_FINDING = {
    "claim": "An external audit in 2019 found the Authority non-compliant with national standards.",
    "evidence_ids": ["audit-2019#0"],
    "severity": "high",
}


def offline_models(question, invent=False):
    findings = list(SCRIPTED_FINDINGS)
    if invent:
        findings.append(INVENTED_FINDING)
    return {
        "retriever": StubModel([question], cost_per_call=0.004),
        "analyst": StubModel([findings], cost_per_call=0.12),
        "writer": StubModel([SCRIPTED_ROADMAP], cost_per_call=0.08),
    }


def live_models():
    from governed_agents.models import AnthropicModel

    return {
        "retriever": AnthropicModel(),
        "analyst": AnthropicModel(expects_json=True),
        "writer": AnthropicModel(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    parser.add_argument("--live", action="store_true", help="use a real model")
    parser.add_argument("--reject", action="store_true", help="the reviewer declines")
    parser.add_argument(
        "--invent",
        action="store_true",
        help="add a finding citing a chunk that was never retrieved",
    )
    args = parser.parse_args()

    if args.live and not os.environ.get("ANTHROPIC_API_KEY"):
        print("--live needs ANTHROPIC_API_KEY. See .env.example.", file=sys.stderr)
        return 2

    if args.live:
        try:
            models = live_models()
        except ImportError:
            print(
                '--live needs the optional extra: pip install -e ".[anthropic]"',
                file=sys.stderr,
            )
            return 2
    else:
        models = offline_models(args.question, args.invent)

    def review(state):
        if args.reject:
            return False, "the scope does not match the engagement"
        n = len(state.get("findings", []))
        return True, "reviewed %d findings against the sources" % n

    app = build_graph(DocumentStore(CORPUS), models, review=review)
    final = app.invoke({"question": args.question, "spend": {}})

    print("mode        : %s" % ("live model" if args.live else "offline, scripted model"))
    print("question    : %s" % args.question)
    print("search query: %s" % final.get("query"))
    print("retrieved   : %s" % ", ".join(c["id"] for c in final.get("retrieved", [])))

    if final.get("halted_reason"):
        print("\nHALTED: %s" % final["halted_reason"])
        print("spend       : %s" % final.get("spend"))
        return 1

    print("\nfindings:")
    for f in final.get("findings", []):
        print("  [%-6s] %s" % (f.get("severity", "?"), f["claim"]))
        print("            evidence: %s" % (f.get("evidence_ids") or "NONE"))

    g = final.get("groundedness") or {}
    print(
        "\ngroundedness: %.2f (floor %.2f) -> %s"
        % (g.get("score", 0.0), GROUNDEDNESS_FLOOR, "PASS" if g.get("passed") else "BLOCK")
    )
    for claim in g.get("ungrounded_claims", []):
        print("  ungrounded: %s" % claim)

    maturity = final.get("maturity")
    if maturity:
        print("maturity    : %s (%s)" % (maturity["level"], maturity["label"]))

    print("\nhuman gate  : %s" % ("APPROVED" if final.get("approved") else "NOT APPROVED"))
    print("reviewer    : %s" % final.get("reviewer_note"))

    print("\nspend against ceilings:")
    for agent, ceiling in BUDGET_CEILING_USD.items():
        print(
            "  %-10s $%.4f / $%.2f" % (agent, final.get("spend", {}).get(agent, 0.0), ceiling)
        )

    if final.get("roadmap"):
        print("\nroadmap:\n%s" % final["roadmap"])
    else:
        print("\nroadmap: not written (the writer was skipped)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
