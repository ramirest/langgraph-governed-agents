"""The ceiling has to be a wall, not a suggestion."""
import pytest

from governed_agents.config import BUDGET_CEILING_USD
from governed_agents.governance.budget import BudgetExceeded, charge, within_budget


def test_charge_accumulates():
    spend = charge({}, "analyst", 0.10)
    spend = charge(spend, "analyst", 0.10)
    assert spend["analyst"] == pytest.approx(0.20)


def test_charge_does_not_mutate_the_input():
    original = {"analyst": 0.10}
    charge(original, "analyst", 0.10)
    assert original == {"analyst": 0.10}


def test_exceeding_the_ceiling_raises_rather_than_clamping():
    ceiling = BUDGET_CEILING_USD["retriever"]
    with pytest.raises(BudgetExceeded) as exc:
        charge({}, "retriever", ceiling + 0.01)
    # The error has to name the agent and both numbers, or the operator ends up
    # reading logs to find out which ceiling stopped the run.
    assert exc.value.agent == "retriever"
    assert exc.value.ceiling == ceiling


def test_spending_exactly_the_ceiling_is_allowed():
    ceiling = BUDGET_CEILING_USD["writer"]
    assert within_budget({}, "writer", ceiling)
    assert charge({}, "writer", ceiling)["writer"] == pytest.approx(ceiling)


def test_an_agent_with_no_ceiling_is_a_configuration_error():
    # Defaulting to "unlimited" here is how a governance layer becomes decorative.
    with pytest.raises(KeyError):
        within_budget({}, "unregistered_agent", 0.01)
