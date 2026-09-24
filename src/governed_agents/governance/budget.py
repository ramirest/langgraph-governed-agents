"""Per-agent cost ceilings.

The ceiling is a hard stop. When an agent would cross it the graph halts and
says so, instead of finishing with a quietly truncated context or a cheaper
model nobody chose. Cost is a failure mode, so it gets treated like one.
"""
from typing import Dict

from governed_agents.config import BUDGET_CEILING_USD


class BudgetExceeded(RuntimeError):
    def __init__(self, agent: str, spent: float, ceiling: float):
        self.agent = agent
        self.spent = spent
        self.ceiling = ceiling
        super().__init__(
            "agent %r would spend $%.4f against a $%.2f ceiling" % (agent, spent, ceiling)
        )


def within_budget(spend: Dict[str, float], agent: str, cost: float) -> bool:
    ceiling = BUDGET_CEILING_USD.get(agent)
    if ceiling is None:  # an agent with no ceiling is a configuration bug
        raise KeyError("no budget ceiling configured for agent %r" % agent)
    return spend.get(agent, 0.0) + cost <= ceiling


def charge(spend: Dict[str, float], agent: str, cost: float) -> Dict[str, float]:
    """Return a new spend map with `cost` charged to `agent`.

    Raises BudgetExceeded rather than clamping: a run that silently stopped
    short of its ceiling looks identical to a run that finished.
    """
    if not within_budget(spend, agent, cost):
        raise BudgetExceeded(agent, spend.get(agent, 0.0) + cost, BUDGET_CEILING_USD[agent])
    updated = dict(spend)
    updated[agent] = updated.get(agent, 0.0) + cost
    return updated
