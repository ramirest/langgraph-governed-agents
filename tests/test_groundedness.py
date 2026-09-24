"""Scoring the claim against what was actually retrieved."""
from governed_agents.config import GROUNDEDNESS_FLOOR
from governed_agents.governance.groundedness import score_groundedness

CHUNKS = [
    {"id": "a#1", "text": "...", "source": "a.md"},
    {"id": "a#2", "text": "...", "source": "a.md"},
]


def finding(claim, ids, severity="high"):
    return {"claim": claim, "evidence_ids": ids, "severity": severity}


def test_all_claims_cited_from_retrieval_scores_one():
    result = score_groundedness([finding("x", ["a#1"]), finding("y", ["a#2"])], CHUNKS)
    assert result["score"] == 1.0
    assert result["passed"]
    assert result["ungrounded_claims"] == []


def test_no_findings_scores_one_not_zero():
    # Finding nothing is a valid diagnostic result. Scoring it as a failure would
    # push the graph toward inventing a gap to clear its own floor.
    result = score_groundedness([], CHUNKS)
    assert result["score"] == 1.0
    assert result["passed"]


def test_an_uncited_claim_is_ungrounded():
    result = score_groundedness([finding("x", [])], CHUNKS)
    assert result["score"] == 0.0
    assert result["ungrounded_claims"] == ["x"]


def test_citing_a_chunk_that_was_never_retrieved_is_ungrounded():
    result = score_groundedness([finding("x", ["b#9"])], CHUNKS)
    assert not result["passed"]
    assert result["ungrounded_claims"] == ["x"]


def test_a_claim_is_only_grounded_if_every_id_holds():
    # Half-real citations are the interesting failure: the first id passing a
    # spot check is what makes the second one survive.
    result = score_groundedness([finding("x", ["a#1", "b#9"])], CHUNKS)
    assert result["score"] == 0.0


def test_the_floor_is_the_one_in_config():
    four_good_one_bad = [finding("g%d" % i, ["a#1"]) for i in range(4)] + [
        finding("bad", ["b#9"])
    ]
    result = score_groundedness(four_good_one_bad, CHUNKS)
    assert result["score"] == 0.8
    assert result["floor"] == GROUNDEDNESS_FLOOR
    assert result["passed"] is (0.8 >= GROUNDEDNESS_FLOOR)


def test_the_failing_claims_are_returned_not_just_the_number():
    result = score_groundedness([finding("keep", ["a#1"]), finding("drop", [])], CHUNKS)
    assert result["ungrounded_claims"] == ["drop"]
    assert result["n_findings"] == 2
