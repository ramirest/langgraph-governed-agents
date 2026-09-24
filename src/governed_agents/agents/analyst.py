"""Turns evidence into findings. Grants: search_documents, score_maturity.

Each finding must carry the ids of the chunks it rests on. That requirement is
what makes groundedness measurable downstream: a claim with no evidence_ids is
not "unverified", it is ungrounded, and the scorer treats it that way.
"""
from typing import List

from governed_agents.governance.budget import BudgetExceeded
from governed_agents.state import DiagnosticState, Finding


def analyst(state: DiagnosticState, agent) -> DiagnosticState:
    retrieved = state.get("retrieved", [])
    context = "\n\n".join("[%s] %s" % (c["id"], c["text"]) for c in retrieved)

    try:
        raw, spend = agent.invoke(
            state.get("spend", {}),
            "Identify maturity gaps. Cite the chunk id behind every claim, and "
            "make no claim you cannot cite.\n\n" + context,
        )
    except BudgetExceeded as exc:
        return {"halted_reason": str(exc)}

    findings: List[Finding] = raw if isinstance(raw, list) else []
    return {"findings": findings, "spend": spend}
