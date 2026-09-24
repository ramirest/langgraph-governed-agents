"""Tool permissions, enforced at the call site.

The point of this module: an agent cannot call a tool it was not granted, no
matter what the model decides to emit. Putting "you may only use X" in a system
prompt is a request. This is a gate.
"""
from typing import Callable, TypeVar

from governed_agents.config import TOOL_GRANTS

F = TypeVar("F", bound=Callable)


class PermissionDenied(PermissionError):
    def __init__(self, agent: str, tool: str):
        self.agent = agent
        self.tool = tool
        super().__init__("agent %r is not granted tool %r" % (agent, tool))


def guard_tool(agent: str, tool_name: str) -> None:
    """Raise unless `agent` holds a grant for `tool_name`."""
    granted = TOOL_GRANTS.get(agent)
    if granted is None:
        raise PermissionDenied(agent, tool_name)  # unknown agent grants nothing
    if tool_name not in granted:
        raise PermissionDenied(agent, tool_name)
