# Governed agents

A small LangGraph system that answers one question: **how do you stop a
multi-agent pipeline from confidently making something up, and how do you prove
it stopped?**

It runs a technical-maturity diagnostic over a document corpus — retrieve,
analyse, draft a roadmap — with four things enforced in code rather than
requested in a prompt:

| | Enforced by | What it stops |
|---|---|---|
| **Per-agent tool permissions** | `governance/permissions.py` | The writer cannot retrieve. The router holds no tools at all. |
| **Per-agent cost ceilings** | `governance/budget.py` | A run that would overspend halts and says so, instead of finishing quietly. |
| **Groundedness scoring against a written rubric** | `governance/groundedness.py` + `evals/rubric.md` | A claim citing evidence that was never retrieved never reaches a draft. |
| **A human gate before delivery** | `hitl.py` | Nothing is delivered without a person approving it. With no reviewer attached, the gate refuses. |

This is a **clean-room reference implementation** of a pattern I work with in
production: hierarchically orchestrated agents with a defined role, permissions
and tools each; RAG grounded in an organisation's own documents; groundedness
scored against a written rubric with human review before anything is delivered.
No employer's code, prompts, rubric or data are in here. The corpus, the
fictional Meridian Transit Authority, and everything else in this repository
were written for it.

---

## The run that matters

The whole point of the repo is the blocked path, so that is the default demo:

```console
$ python run_diagnostic.py --invent

findings:
  [high  ] The fare-collection dataset has no named owner while three teams write to it.
            evidence: ['data-governance#1']
  [high  ] Warehouse access is per person with no revocation path; 12 accounts belong to people who have left.
            evidence: ['data-governance#3']
  [medium] There are no automated quality checks; errors surface through downstream consumers.
            evidence: ['data-governance#4']
  [high  ] An external audit in 2019 found the Authority non-compliant with national standards.
            evidence: ['audit-2019#0']

groundedness: 0.75 (floor 0.80) -> BLOCK
  ungrounded: An external audit in 2019 found the Authority non-compliant with national standards.

human gate  : NOT APPROVED
reviewer    : blocked before review: groundedness 0.75 below floor 0.80 (1 ungrounded)

spend against ceilings:
  retriever  $0.0040 / $0.05
  analyst    $0.1200 / $0.40
  writer     $0.0000 / $0.25

roadmap: not written (the writer was skipped)
```

Three things happened there, none of which depended on a model behaving well.
The fabricated claim was named, not just counted. The writer never ran, so there
is no polished draft sitting around to be mistaken for a reviewed one — and
`$0.0000` against its ceiling is the receipt. And the reviewer was never asked,
because a human should not be handed a document that already failed its floor.

Drop `--invent` for the clean run. Add `--reject` to watch a passing run get
declined anyway.

---

## Quickstart

```bash
pip install -e ".[dev]"

python run_diagnostic.py            # one diagnostic, full trace
pytest -q                           # 35 tests
python evals/run_evals.py           # 6 golden cases
```

**No API key needed.** The default path scripts the model's outputs and runs the
real retriever, the real permission checks, the real ceilings, the real scorer
and the real gate. That is deliberate: a governance guarantee you can only verify
by spending money is a guarantee nobody re-verifies.

For a real model: `pip install -e ".[anthropic]"`, set `ANTHROPIC_API_KEY` (see
`.env.example`), then `python run_diagnostic.py --live "your question"`. The
governance layer cannot tell the difference between the two, which is the reason
the offline tests are worth anything.

---

## Shape of the graph

```
START -> supervisor -> retriever ----------------> supervisor
                    -> analyst -> score_findings -> supervisor
                    -> writer ------------------->  supervisor
                    -> human_gate -> END
                    -> END  (when halted)
```

**Every specialist returns to the supervisor.** That is what makes the hierarchy
real rather than decorative: no specialist decides what happens next, so none of
them can extend a run, and each one's spend is charged against its own ceiling.

**`score_findings` sits on a fixed edge out of the analyst**, not on a route the
supervisor chooses. A quality gate the router can skip is not a gate.

**The supervisor holds no tools and makes no model call.** Its routing is a pure
function of state. A router that reasons is a router that can be argued with, and
there is nothing in it for an instruction hidden inside a retrieved document to
talk to.

---

## Decisions worth arguing about

**Permissions are checked at the call site.** `guard_tool(agent, tool)` raises
before dispatch. "You may only use these tools" in a system prompt is a request;
this is a gate. The test that matters gives the writer a working
`search_documents` implementation and asserts it still cannot reach it.

**Budget ceilings raise instead of clamping.** A run that silently stopped short
of its ceiling looks identical to a run that finished. Cost is a failure mode, so
it is treated like one — loudly, with the agent and both numbers in the message.

**Groundedness is scored structurally, and the semantic half is scored
separately.** The automated check asks one narrow question — does every claim
cite a chunk that was actually retrieved in this run? — because it is cheap,
deterministic, and catches the failure that costs the most in a diagnostic
delivered to an institution. Whether the cited chunk really supports the claim
needs judgement, so it lives in `evals/rubric.md` as a four-level scale applied
per case. Conflating the two produces a number that means neither.

**An empty finding set scores 1.0, not 0.0.** Finding no gaps is a valid
diagnostic result. Scoring it as failure pushes the graph toward inventing a gap
to clear its own floor.

**The router asks whether a stage has run, never whether it produced something.**
`not state.get("findings")` conflates "the analyst found nothing" with "the
analyst has not been called", and a router that cannot tell those apart
re-dispatches the analyst forever on a clean corpus. This one cost me a test
before it cost me anything else, which is the argument for having the test.

**The human gate fails closed.** With no reviewer wired up it refuses, because
the default is what runs at 2am when nobody configured anything.

**The floor is a constant in one file.** `GROUNDEDNESS_FLOOR = 0.80` in
`config.py`, not a literal at the comparison. Moving it should be a visible,
reviewable change — the kind of number that drifts in a code review is the kind
that ends up justifying whatever the pipeline already did.

---

## The rubric is a file

`evals/rubric.md` is versioned with the code. A rubric that lives in a
reviewer's head produces a score only that reviewer can reproduce, and a score
nobody else can reproduce is an opinion with a number attached. It defines the
groundedness floor, the four-level faithfulness scale, the severity weighting
behind the 1-5 maturity level, and what the automated check deliberately does
*not* catch.

The golden cases in `evals/cases.yaml` are the regression suite: the thing that
re-runs when a prompt, a model or a threshold changes. Each case scripts what the
analyst emits and asserts on the graph's behaviour, so a failure means the
governance layer changed, not that a model had an off day. Retrieval in the cases
is real, which is what keeps the ungrounded cases honest rather than rigged.

```console
$ python evals/run_evals.py
PASS governance-gaps-grounded     groundedness=1.00 approved=True
PASS invented-evidence-blocked    groundedness=0.50 approved=False
PASS uncited-claim-blocked        groundedness=0.50 approved=False
PASS budget-ceiling-halts         groundedness=n/a approved=None  halted: agent 'retriever' would spend $0.0900 against a $0.05 ceiling
PASS reviewer-rejects             groundedness=1.00 approved=False
PASS no-findings-scores-clean     groundedness=1.00 approved=True

6/6 cases passed
```

It runs in CI on every push, because it runs offline. A regression suite that
needs an API key is a regression suite that stops running.

---

## Layout

```
run_diagnostic.py     one diagnostic, full trace, offline by default
src/governed_agents/
  state.py            graph state — everything a governance decision needs,
                      outside the model's context
  config.py           ceilings, grants, floor, model. Data, not prose.
  graph.py            wiring and the conditional edges
  hitl.py             the human gate
  tools.py            search_documents, score_maturity — deterministic, offline
  models.py           optional ChatAnthropic adapter with real cost accounting
  governance/
    permissions.py    guard_tool: raises before dispatch
    budget.py         per-agent ceilings, pre-authorize then reconcile
    groundedness.py   structural scoring against the rubric
  agents/
    base.py           StubModel, Agent.call_tool, Agent.invoke
    supervisor.py     routes; holds nothing
    retriever.py      rewrites the query, retrieves, summarises nothing
    analyst.py        findings, each carrying its evidence ids
    writer.py         roadmap from findings that already passed
  rag/store.py        lexical chunk store, no embedding service
evals/
  rubric.md           the written rubric
  cases.yaml          6 golden cases
  run_evals.py        the regression suite
data/sample_org/      the fictional corpus
tests/                35 tests, all offline
.github/workflows/    pytest + the golden cases, on every push
```

---

## What this does not do

Stating the limits is part of the point; a governance layer whose gaps are
undocumented is a governance layer you will trust further than it deserves.

- **The ceiling is a pre-authorization.** An estimate is charged before the call
  and reconciled against actual token usage after. When a call costs more than
  estimated, the money is already spent and what the ceiling stops is the *next*
  call. Exact upfront pricing is not possible, which is why the ceilings sit well
  below the point where one overrun would matter — but it is a real limit, not a
  detail.
- **Retrieval is lexical**, not semantic. Swap `rag/store.py` for a real vector
  store; keep the `{"id", "text", "source"}` contract the scorer depends on.
  Nothing in the governance layer changes, which is the interesting part.
- **Semantic faithfulness is not automated.** The structural check passes a claim
  that cites a real chunk which does not support it. An LLM-as-judge scorer over
  the golden cases is the obvious next step; the rubric already defines the scale
  it would apply.
- **The human gate is synchronous here.** In production this is a LangGraph
  `interrupt` with a checkpointer, suspending the run until a person resumes it.
  `build_graph` takes a `checkpointer`; the demo passes none so a run completes
  in one process.
- **One corpus, one diagnostic shape.** Multi-tenant isolation, per-tenant
  budgets and an audit log are all absent.

---

## Why this repository exists

I spend my working days on agents that produce output an institution will act
on, where a confident fabrication is the expensive failure and "the model
usually gets it right" is not an answer. Most of what makes that work is not
prompt engineering — it is deciding which guarantees have to be structural, and
then being able to demonstrate that they hold.

This is that argument in runnable form: 35 tests and 6 golden cases that pass
without an API key, and a default demo that shows the system refusing to deliver
something it could not support.

— [Ramires Teixeira](https://linkedin.com/in/ramires-teixeira) · [rtxconsulting.com.br](https://rtxconsulting.com.br)
