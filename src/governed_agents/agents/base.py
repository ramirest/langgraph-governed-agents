"""Shared agent plumbing.

`StubModel` exists so the graph, the governance layer and the eval suite can be
exercised end to end without an API key. Every test in this repo runs against
it. That is deliberate: a governance guarantee you can only verify by spending
money is a guarantee nobody re-verifies.
"""
from typing import Any, Callable, Dict, Optional, Tuple

from governed_agents.governance.budget import charge
from governed_agents.governance.permissions import guard_tool


class StubModel:
    """Replays scripted responses in order. No network, no cost drift."""

    def __init__(self, responses, cost_per_call: float = 0.01):
        self._responses = list(responses)
        self._index = 0
        self.cost_per_call = cost_per_call
        self.last_cost = 0.0
        self.calls = 0

    def estimate_cost(self, _prompt: str) -> float:
        return self.cost_per_call

    def invoke(self, _prompt: str) -> Any:
        self.calls += 1
        if self._index >= len(self._responses):
            raise AssertionError("StubModel ran out of scripted responses")
        response = self._responses[self._index]
        self._index += 1
        self.last_cost = self.cost_per_call
        return response


class Agent:
    """An agent is a name, a model, and the tools it was granted.

    Tools go through `call_tool`, which checks the grant before dispatching.
    Bypassing it is possible, the same way ignoring a type checker is possible;
    what matters is that the default path is the checked one and the tests
    assert on it.
    """

    def __init__(self, name: str, model: Any, tools: Optional[Dict[str, Callable]] = None):
        self.name = name
        self.model = model
        self.tools = tools or {}

    def call_tool(self, tool_name: str, *args, **kwargs):
        guard_tool(self.name, tool_name)
        if tool_name not in self.tools:
            raise KeyError(
                "agent %r has a grant for %r but no implementation" % (self.name, tool_name)
            )
        return self.tools[tool_name](*args, **kwargs)

    def invoke(self, spend: Dict[str, float], prompt: str) -> Tuple[Any, Dict[str, float]]:
        """Pre-authorize against the ceiling, call, then reconcile.

        Raises BudgetExceeded in two places, and the difference matters.

        Before the call: the estimate does not fit under the ceiling, so nothing
        is spent. That is the case worth having.

        After the call: the call cost more than estimated. The money is already
        gone; what the ceiling stops is the *next* call. That is the honest limit
        of charging a model you cannot price before you invoke it, and it is why
        the ceilings sit well below the point where an overrun would matter.
        """
        estimate = self.model.estimate_cost(prompt)
        spend = charge(spend, self.name, estimate)

        result = self.model.invoke(prompt)

        actual = getattr(self.model, "last_cost", None)
        if actual is not None and actual != estimate:
            spend = charge(spend, self.name, actual - estimate)

        return result, spend

    @property
    def cost_per_call(self) -> float:
        return getattr(self.model, "cost_per_call", 0.0)
