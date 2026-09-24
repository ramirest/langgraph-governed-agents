"""Operating limits.

These are deliberately data, not prose in a system prompt. A ceiling that lives
in a config file can be tested; a ceiling that lives in a prompt is a request.
"""
from typing import Dict

# USD. Per agent, per run. Exceeding one halts the graph rather than degrading
# quietly, because a silent overspend is the failure mode you notice last.
BUDGET_CEILING_USD: Dict[str, float] = {
    "retriever": 0.05,
    "analyst": 0.40,
    "writer": 0.25,
}

# Tools each agent may call. Enforced at the edge (see governance/permissions.py),
# never by asking the model to behave.
TOOL_GRANTS: Dict[str, frozenset] = {
    "supervisor": frozenset(),  # routes only; touches no tool
    "retriever": frozenset({"search_documents"}),
    "analyst": frozenset({"search_documents", "score_maturity"}),
    "writer": frozenset({"score_maturity"}),
}

# Minimum share of findings that must be traceable to retrieved evidence for a
# diagnostic to reach a human at all. Below this the run halts.
GROUNDEDNESS_FLOOR = 0.80

MODEL = "claude-sonnet-5"
