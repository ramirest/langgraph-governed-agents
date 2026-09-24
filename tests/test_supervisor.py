"""The router is a pure function, so it can be tested without a graph."""
from governed_agents.agents.supervisor import supervisor


def test_first_hop_is_retrieval():
    assert supervisor({"question": "q"})["next_agent"] == "retriever"


def test_retrieval_having_run_is_not_the_same_as_retrieval_having_found_something():
    # The retriever ran and found nothing. Routing on truthiness would send it
    # back in and loop; routing on key presence moves on.
    assert supervisor({"question": "q", "retrieved": []})["next_agent"] == "analyst"


def test_an_empty_finding_set_does_not_re_dispatch_the_analyst():
    state = {"retrieved": [], "findings": [], "groundedness": {"passed": True}}
    assert supervisor(state)["next_agent"] == "writer"


def test_a_failing_groundedness_score_skips_the_writer():
    state = {"retrieved": [], "findings": [], "groundedness": {"passed": False}}
    assert supervisor(state)["next_agent"] is None


def test_a_halted_run_is_never_routed_onward():
    state = {"retrieved": [], "halted_reason": "budget", "groundedness": {"passed": True}}
    assert supervisor(state)["next_agent"] is None


def test_a_completed_run_stops():
    state = {"retrieved": [], "groundedness": {"passed": True}, "roadmap": "done"}
    assert supervisor(state)["next_agent"] is None
