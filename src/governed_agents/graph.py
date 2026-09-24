"""Graph wiring.

Shape:

    START -> supervisor -> retriever ---------------> supervisor
                        -> analyst -> score_findings -> supervisor
                        -> writer ---------------->    supervisor
                        -> human_gate -> END
                        -> END (when halted)

Two things are worth noticing.

Every specialist returns to the supervisor. That is what makes the hierarchy
real: no specialist decides what happens next, so no specialist can extend the
run, and each one's spend is charged against its own ceiling.

`score_findings` sits on a fixed edge out of the analyst, not on a route the
supervisor chooses. A quality gate the router can skip is not a gate.
"""
from typing import Any, Callable, Dict, Optional

from langgraph.graph import END, START, StateGraph

from governed_agents.agents.analyst import analyst
from governed_agents.agents.base import Agent
from governed_agents.agents.retriever import retriever
from governed_agents.agents.supervisor import supervisor
from governed_agents.agents.writer import writer
from governed_agents.governance.groundedness import score_groundedness
from governed_agents.hitl import ReviewFn, human_gate
from governed_agents.rag.store import DocumentStore
from governed_agents.state import DiagnosticState
from governed_agents.tools import make_tools


def score_findings(state: DiagnosticState) -> DiagnosticState:
    return {
        "groundedness": score_groundedness(
            state.get("findings", []), state.get("retrieved", [])
        )
    }


def _route(state: DiagnosticState) -> str:
    """Where the supervisor sends control next."""
    if state.get("halted_reason"):
        return END
    next_agent = state.get("next_agent")
    if next_agent:
        return next_agent
    return "human_gate"


def build_graph(
    store: DocumentStore,
    models: Dict[str, Any],
    review: Optional[ReviewFn] = None,
    checkpointer: Any = None,
) -> Callable:
    """Compile the diagnostic graph.

    `models` maps agent name -> model object exposing `.invoke(prompt)` and
    `.cost_per_call`. Pass StubModel instances to run the whole thing offline,
    or ChatAnthropic wrappers to run it for real; the governance layer cannot
    tell the difference, which is exactly why the tests are worth anything.
    """
    tools = make_tools(store)
    agents = {
        name: Agent(name=name, model=model, tools=tools)
        for name, model in models.items()
    }

    graph = StateGraph(DiagnosticState)

    graph.add_node("supervisor", supervisor)
    graph.add_node("retriever", lambda s: retriever(s, agents["retriever"]))
    graph.add_node("analyst", lambda s: analyst(s, agents["analyst"]))
    graph.add_node("writer", lambda s: writer(s, agents["writer"]))
    graph.add_node("score_findings", score_findings)
    graph.add_node("human_gate", lambda s: human_gate(s, review))

    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        _route,
        {
            "retriever": "retriever",
            "analyst": "analyst",
            "writer": "writer",
            "human_gate": "human_gate",
            END: END,
        },
    )
    graph.add_edge("retriever", "supervisor")
    graph.add_edge("analyst", "score_findings")
    graph.add_edge("score_findings", "supervisor")
    graph.add_edge("writer", "supervisor")
    graph.add_edge("human_gate", END)

    return graph.compile(checkpointer=checkpointer)
