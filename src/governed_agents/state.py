"""Graph state.

Everything the governance layer needs to make a decision lives here, not in the
model's context. A model cannot talk its way past a budget it cannot see.
"""
from typing import Dict, List, Optional, TypedDict


class Finding(TypedDict):
    """One gap the analyst found, with the evidence it rests on."""

    claim: str
    evidence_ids: List[str]  # ids of retrieved chunks, for groundedness scoring
    severity: str  # "low" | "medium" | "high"


class DiagnosticState(TypedDict, total=False):
    """State passed between nodes.

    `spend` and `findings` are append-only from the agents' point of view: the
    agents propose, the governance nodes decide.
    """

    question: str
    next_agent: Optional[str]

    query: Optional[str]  # the retriever's rewrite, kept so a run is auditable
    retrieved: List[Dict[str, str]]  # [{"id": ..., "text": ..., "source": ...}]
    findings: List[Finding]
    maturity: Optional[Dict[str, object]]
    roadmap: Optional[str]

    # governance
    spend: Dict[str, float]  # agent name -> USD spent so far
    halted_reason: Optional[str]
    groundedness: Optional[Dict[str, object]]
    approved: Optional[bool]
    reviewer_note: Optional[str]
