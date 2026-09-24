"""Hierarchical agents with governance enforced outside the prompt.

`build_graph` is exported lazily on purpose: importing it pulls in LangGraph, and
the governance modules are useful on their own. Someone who only wants to read or
reuse `governed_agents.governance` should not have to install a graph engine to
do it.
"""
__all__ = ["build_graph"]


def __getattr__(name):
    if name == "build_graph":
        from governed_agents.graph import build_graph

        return build_graph
    raise AttributeError("module %r has no attribute %r" % (__name__, name))
