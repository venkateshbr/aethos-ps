# Agent-eval gate + drift report (#407)

The agent eval has two layers. This doc covers how they gate CI.

## 1. Offline gate (runs in CI, deterministic)

`backend/app/evals/` holds the golden prompt set (`golden_prompts.py`), the
deterministic `rubric.py` (leak / off-topic / write-not-routed / number-fidelity
checks), and a **labeled response corpus** (`eval_fixtures.py`). The gate
(`gate.py`) scores every fixture with the rubric and fails if the harness
misclassifies any fixture or leaves a golden case uncovered.

Because it needs no LLM or network, it runs in the normal unit lane
(`tests/unit/test_eval_gate.py`) **and** as an explicit CI step that publishes a
drift dashboard to the GitHub step summary:

```yaml
# .github/workflows/ci.yml → backend-test
- name: Agent-eval offline gate (#407)
  working-directory: backend
  run: uv run python -m scripts.agent_eval_gate --out "$GITHUB_STEP_SUMMARY"
```

Run it locally:

```bash
cd backend && uv run python -m scripts.agent_eval_gate          # prints report, exit 1 on drift
cd backend && uv run python -m scripts.agent_eval_gate --out eval-drift.md
```

**What it protects:** the *scoring logic* the eval depends on. If someone weakens
the leak detector or the Inbox-routing check so a bad answer starts passing, a
labeled fixture flips and CI goes red. Grow `eval_fixtures.py` alongside
`GOLDEN_CASES` — every case should have at least one passing fixture and, where a
failure mode applies, one failing fixture.

## 2. Live eval (opt-in, real agent)

`backend/tests/eval/test_agent_eval_live.py` runs the same golden prompts against
a running stack + seeded tenant and scores the real agent's answers — this is what
measures actual model/prompt/runtime drift. It is skipped by default (needs a
backend, a seeded tenant, and LLM budget):

```bash
AETHOS_EVAL_LIVE=1 \
AETHOS_EVAL_API_URL=http://localhost:8011 \
AETHOS_EVAL_TOKEN=<jwt> \
AETHOS_EVAL_TENANT_ID=<uuid> \
uv run pytest tests/eval/test_agent_eval_live.py -q -s
```

The offline gate guards the rubric; the live eval exercises the agent through it.
