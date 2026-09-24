"""Writes the roadmap from findings that already passed scoring.

Grant: score_maturity only. The writer cannot retrieve, so it cannot introduce
evidence that was never scored. Every sentence it writes traces to a finding the
groundedness gate already saw — a structural guarantee, not a well-behaved model.
"""
from governed_agents.governance.budget import BudgetExceeded
from governed_agents.state import DiagnosticState


def writer(state: DiagnosticState, agent) -> DiagnosticState:
    findings = state.get("findings", [])
    maturity = agent.call_tool("score_maturity", findings)

    summary = "\n".join(
        "- [%s] %s" % (f.get("severity", "low"), f["claim"]) for f in findings
    )

    try:
        roadmap, spend = agent.invoke(
            state.get("spend", {}),
            "Maturity level %s (%s). Draft a roadmap from these findings, and "
            "introduce nothing that is not one of them:\n%s"
            % (maturity["level"], maturity["label"], summary),
        )
    except BudgetExceeded as exc:
        return {"halted_reason": str(exc), "maturity": maturity}

    return {"roadmap": roadmap, "maturity": maturity, "spend": spend}
