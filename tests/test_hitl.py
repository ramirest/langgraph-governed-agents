"""Nothing is delivered without a person saying so."""
from governed_agents.hitl import human_gate

PASSING = {"score": 1.0, "floor": 0.8, "passed": True, "ungrounded_claims": []}
FAILING = {"score": 0.5, "floor": 0.8, "passed": False, "ungrounded_claims": ["x"]}


def test_with_no_reviewer_attached_the_gate_refuses():
    # The default has to be the safe one, because the default is what runs when
    # nobody configured anything.
    result = human_gate({"groundedness": PASSING, "roadmap": "draft"})
    assert result["approved"] is False


def test_a_passing_score_cannot_approve_itself():
    result = human_gate(
        {"groundedness": PASSING, "roadmap": "draft"},
        review=lambda _s: (False, "out of scope"),
    )
    assert result["approved"] is False
    assert result["reviewer_note"] == "out of scope"


def test_an_attached_reviewer_can_approve():
    result = human_gate(
        {"groundedness": PASSING, "roadmap": "draft"}, review=lambda _s: (True, "ok")
    )
    assert result["approved"] is True


def test_a_failing_score_is_blocked_before_the_reviewer_is_asked():
    asked = []

    def review(_state):
        asked.append(1)
        return True, "rubber stamp"

    result = human_gate({"groundedness": FAILING, "roadmap": "draft"}, review=review)
    assert result["approved"] is False
    assert asked == []  # a reviewer cannot wave through a run that failed the floor
    assert "below floor" in result["reviewer_note"]


def test_a_missing_score_is_treated_as_a_failure():
    assert human_gate({"roadmap": "draft"}, review=lambda _s: (True, "ok"))["approved"] is False
