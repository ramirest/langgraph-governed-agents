"""End to end, offline. Every guarantee the README claims is asserted here."""
from governed_agents.config import BUDGET_CEILING_USD
from governed_agents.graph import build_graph

GROUNDED = [
    {
        "claim": "The fare-collection dataset has no named owner.",
        "evidence_ids": ["data-governance#1"],
        "severity": "high",
    }
]
INVENTED = [
    {
        "claim": "An external audit found the Authority non-compliant.",
        "evidence_ids": ["audit-2019#0"],
        "severity": "high",
    }
]

QUESTION = "fare collection dataset named owner"


def approve(_state):
    return True, "reviewed"


def run(store, models, findings, **kwargs):
    app = build_graph(store, models(findings, QUESTION, **kwargs), review=approve)
    return app.invoke({"question": QUESTION, "spend": {}})


def test_happy_path_delivers_an_approved_roadmap(store, models):
    final = run(store, models, GROUNDED)
    assert final["groundedness"]["passed"]
    assert final["approved"] is True
    assert final["roadmap"]
    assert final["maturity"]["level"]


def test_invented_evidence_never_reaches_a_draft(store, models):
    final = run(store, models, INVENTED)
    assert final["groundedness"]["passed"] is False
    assert final["approved"] is False
    # The writer is skipped entirely: no draft to be mistaken for a reviewed one,
    # and no tokens spent dressing up a claim with nothing behind it.
    assert "roadmap" not in final
    assert "writer" not in final["spend"]


def test_the_failing_claim_reaches_the_reviewer_not_just_the_score(store, models):
    final = run(store, models, INVENTED)
    assert final["groundedness"]["ungrounded_claims"] == [INVENTED[0]["claim"]]
    assert "below floor" in final["reviewer_note"]


def test_a_budget_ceiling_halts_the_run_at_the_first_hop(store, models):
    over = BUDGET_CEILING_USD["retriever"] + 0.01
    final = run(store, models, GROUNDED, retriever_cost=over)
    assert "ceiling" in final["halted_reason"]
    # Halting means halting: nothing downstream ran, and nothing was approved.
    assert "retrieved" not in final
    assert "approved" not in final


def test_spend_is_attributed_per_agent(store, models):
    final = run(store, models, GROUNDED)
    assert set(final["spend"]) == {"retriever", "analyst", "writer"}
    for agent, spent in final["spend"].items():
        assert spent <= BUDGET_CEILING_USD[agent]


def test_the_default_gate_refuses_when_no_reviewer_is_wired(store, models):
    app = build_graph(store, models(GROUNDED, QUESTION))  # no review= argument
    final = app.invoke({"question": QUESTION, "spend": {}})
    assert final["groundedness"]["passed"] is True
    assert final["approved"] is False
    assert final["reviewer_note"] == "no reviewer attached"
