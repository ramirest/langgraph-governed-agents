"""Routes work. Holds no tools, by design.

Giving the router tool access is how a hierarchy quietly becomes a single agent
with extra steps: it stops delegating and starts doing, and the per-agent
ceilings stop meaning anything.

The routing decision is a pure function of state, not a model call. A router
that reasons is a router that can be argued with, and there is nothing here for
an instruction hidden in a retrieved document to talk to.
"""
from typing import Optional

from governed_agents.state import DiagnosticState


def supervisor(state: DiagnosticState) -> DiagnosticState:
    """Pick the next specialist from what the state already contains.

    Each branch asks whether a stage has *run*, never whether it produced
    something. `not state.get("findings")` would conflate "the analyst found no
    gaps" with "the analyst has not been called yet", and a router that cannot
    tell those apart re-dispatches the analyst forever on a clean corpus. An
    empty result is a result.

    The marker for "the analyst has run" is `groundedness`, because the scorer
    sits on a fixed edge out of the analyst and cannot be skipped.
    """
    next_agent: Optional[str]
    grounding = state.get("groundedness")

    if state.get("halted_reason"):
        next_agent = None
    elif "retrieved" not in state:
        next_agent = "retriever"
    elif grounding is None:
        next_agent = "analyst"
    elif not grounding.get("passed"):
        # Do not pay the writer to dress up findings that failed the floor. The
        # run still ends at the human gate, which reports why.
        next_agent = None
    elif "roadmap" not in state:
        next_agent = "writer"
    else:
        next_agent = None

    return {"next_agent": next_agent}
