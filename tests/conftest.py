import os

import pytest

from governed_agents.agents.base import StubModel
from governed_agents.rag.store import DocumentStore

CORPUS = os.path.join(os.path.dirname(__file__), "..", "data", "sample_org")


@pytest.fixture(scope="session")
def store():
    return DocumentStore(CORPUS)


@pytest.fixture
def models():
    """Cheap stubs for the happy path. Tests that care override one of them.

    The retriever's scripted response is the search query it would have written;
    the analyst's is the finding list; the writer's is the draft.
    """

    def build(findings, query, roadmap="a roadmap", retriever_cost=0.01):
        return {
            "retriever": StubModel([query], cost_per_call=retriever_cost),
            "analyst": StubModel([findings], cost_per_call=0.01),
            "writer": StubModel([roadmap], cost_per_call=0.01),
        }

    return build
