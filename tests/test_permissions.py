"""A grant the model can talk its way past is not a grant."""
import pytest

from governed_agents.agents.base import Agent, StubModel
from governed_agents.governance.permissions import PermissionDenied, guard_tool


def test_granted_tool_passes():
    guard_tool("retriever", "search_documents")


def test_ungranted_tool_is_denied():
    # The writer must not be able to retrieve: that is what keeps every sentence
    # it writes traceable to evidence the groundedness gate already scored.
    with pytest.raises(PermissionDenied):
        guard_tool("writer", "search_documents")


def test_supervisor_holds_nothing():
    for tool in ("search_documents", "score_maturity"):
        with pytest.raises(PermissionDenied):
            guard_tool("supervisor", tool)


def test_unknown_agent_is_denied_not_defaulted():
    with pytest.raises(PermissionDenied):
        guard_tool("ghost", "search_documents")


def test_agent_call_tool_checks_the_grant_before_dispatching():
    called = []
    agent = Agent(
        name="writer",
        model=StubModel([]),
        tools={"search_documents": lambda *a, **k: called.append(1)},
    )
    with pytest.raises(PermissionDenied):
        agent.call_tool("search_documents", "anything")
    # The implementation exists and is reachable; only the grant stopped it.
    assert called == []


def test_a_grant_without_an_implementation_fails_loudly():
    agent = Agent(name="retriever", model=StubModel([]), tools={})
    with pytest.raises(KeyError):
        agent.call_tool("search_documents", "anything")
