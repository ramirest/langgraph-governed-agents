"""The human gate.

Nothing reaches the client without a person approving it. The gate sits after
groundedness scoring so the reviewer sees the score and the ungrounded claims
next to the draft, rather than being asked to eyeball prose cold.

In production this is a LangGraph `interrupt`, which suspends the run and
persists state until a human resumes it. Here the decision function is injected
so the tests can drive both branches deterministically.
"""
from typing import Callable, Optional, Tuple

from governed_agents.state import DiagnosticState

ReviewFn = Callable[[DiagnosticState], Tuple[bool, Optional[str]]]


def auto_reject(_state: DiagnosticState) -> Tuple[bool, Optional[str]]:
    """Default review function: refuses. Failing closed is the whole point."""
    return False, "no reviewer attached"


def human_gate(
    state: DiagnosticState, review: Optional[ReviewFn] = None
) -> DiagnosticState:
    grounding = state.get("groundedness") or {}

    if not grounding.get("passed", False):
        return {
            "approved": False,
            "reviewer_note": "blocked before review: groundedness %.2f below floor %.2f (%d ungrounded)"
            % (
                grounding.get("score", 0.0),
                grounding.get("floor", 0.0),
                len(grounding.get("ungrounded_claims", [])),
            ),
        }

    decide = review or auto_reject
    approved, note = decide(state)
    return {"approved": approved, "reviewer_note": note}
