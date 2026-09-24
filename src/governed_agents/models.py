"""The real-model adapter. Optional: nothing in the tests or evals needs it.

The governance layer only asks three things of a model: `estimate_cost(prompt)`,
`invoke(prompt)` and a `last_cost` attribute after the call. That is the whole
interface, which is why StubModel can stand in for this class everywhere and the
guarantees still hold.

Install with:  pip install -e ".[anthropic]"
"""
import json
import os
from typing import Any, Optional

from governed_agents.config import MODEL

# Prices are an input, not a fact. Set them from your own billing page; they are
# per million tokens and they change. A wrong price here produces a wrong
# ceiling, silently, which is exactly the failure this repo is about — so they
# are a constructor argument, not a constant buried in the call site.
DEFAULT_USD_PER_MTOK_IN = 3.0
DEFAULT_USD_PER_MTOK_OUT = 15.0

# Rough characters-per-token, used only to pre-authorize a call. Deliberately
# pessimistic: an estimate that runs low turns the ceiling into a suggestion.
CHARS_PER_TOKEN = 3.5
ASSUMED_OUTPUT_TOKENS = 1200


class AnthropicModel:
    """Wraps ChatAnthropic and reports what the call actually cost."""

    def __init__(
        self,
        model: str = MODEL,
        usd_per_mtok_in: float = DEFAULT_USD_PER_MTOK_IN,
        usd_per_mtok_out: float = DEFAULT_USD_PER_MTOK_OUT,
        expects_json: bool = False,
        api_key: Optional[str] = None,
    ):
        from langchain_anthropic import ChatAnthropic  # optional dependency

        self._client = ChatAnthropic(
            model=model,
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
        )
        self.usd_per_mtok_in = usd_per_mtok_in
        self.usd_per_mtok_out = usd_per_mtok_out
        self.expects_json = expects_json
        self.last_cost = 0.0

    def estimate_cost(self, prompt: str) -> float:
        tokens_in = len(prompt) / CHARS_PER_TOKEN
        return (
            tokens_in * self.usd_per_mtok_in
            + ASSUMED_OUTPUT_TOKENS * self.usd_per_mtok_out
        ) / 1_000_000

    def invoke(self, prompt: str) -> Any:
        message = self._client.invoke(prompt)

        usage = getattr(message, "usage_metadata", None) or {}
        self.last_cost = (
            usage.get("input_tokens", 0) * self.usd_per_mtok_in
            + usage.get("output_tokens", 0) * self.usd_per_mtok_out
        ) / 1_000_000

        text = message.content if isinstance(message.content, str) else str(message.content)
        if not self.expects_json:
            return text

        # The analyst has to return structured findings. A model that returns
        # prose where the schema was asked for is a failure to surface, not to
        # paper over with a regex: an unparseable response yields no findings,
        # the groundedness score is 1.0 over zero claims, and the human gate
        # shows a diagnostic that found nothing. That is visible. A salvaged
        # half-parse is not.
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []

    @property
    def cost_per_call(self) -> float:
        return self.estimate_cost("")
