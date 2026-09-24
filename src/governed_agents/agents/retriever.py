"""Pulls evidence. Grant: search_documents.

The model's only job here is to turn the request into a search query. It never
sees a tool signature it was not granted, and the chunks it gets back are
returned to the graph untouched — the retriever does not summarise, because a
summary is where evidence quietly becomes assertion.
"""
from governed_agents.governance.budget import BudgetExceeded
from governed_agents.state import DiagnosticState


def retriever(state: DiagnosticState, agent) -> DiagnosticState:
    try:
        query, spend = agent.invoke(
            state.get("spend", {}),
            "Rewrite this diagnostic request as a document search query:\n"
            + state["question"],
        )
    except BudgetExceeded as exc:
        return {"halted_reason": str(exc)}

    chunks = agent.call_tool("search_documents", query, k=6)
    return {"retrieved": chunks, "query": query, "spend": spend}
