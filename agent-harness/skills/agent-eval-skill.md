---
name: agent-eval
description: Use whenever an AI agent's prompt, tools, schema, or model version is changed. Produces or updates the agent's eval pack and runs the eval as a gate.
---

# Agent Eval Skill

Use this skill on every change to an agent that affects its behavior.

## Required Context

- `agent-harness/core/agent-eval-standard.md`.
- `agent-harness/templates/AGENT_EVAL_PACK.yaml`.
- The agent's existing eval pack (if any) at `<eval-path>/<agent_name>.yaml`.
- The most recent agent correction entries (from `agent_corrections` table or equivalent).

## Workflow

1. **Identify the change** — prompt? tool schema? model? output type? Each requires the eval to be re-run.
2. **Bump `version` and `prompt_version`** in the eval pack.
3. **Add cases** — at least one new golden case per behavior change; at least one regression case per correction since the last version.
4. **Add red-team cases** — for any new tool or input source, add a prompt-injection / PII-smuggling / OOD case.
5. **Add HITL routing cases** — for any change to the confidence threshold or HITL routing logic.
6. **Run the eval** — locally and in CI.
7. **Compare to baseline** — average score, pass rate, red-team pass rate, per-case regression. Fail PR if any threshold breaks.
8. **Update the drift baseline** — only after the eval passes and the orchestrator has approved.
9. **Calibration check** — if the agent has high-confidence outputs that the eval scores low, tighten the HITL gating and re-run.

## Must Do

- Every agent in scope has an eval pack file at `<eval-path>/<agent_name>.yaml` — no exceptions.
- Red-team cases pass at 100% — no carve-outs.
- LLM-as-judge evaluators are paired with deterministic evaluators where possible — judges drift too.
- Corrections from production are promoted to eval cases within 7 days.
- Prompts are versioned in the repo, referenced by name from the agent code.

## Avoid

- Hand-running evals in notebooks and pasting screenshots into PRs — the eval must run in CI.
- Lowering the threshold to make a PR pass.
- Removing failing cases instead of fixing them.
- Sending raw PII to the model — mask at the call site, verify in the trace.

## Verification

```bash
# Run eval pack
<project test command> tests/evals/test_<agent_name>.py -v

# Compare to baseline (project-specific tooling)
<project eval-compare> <agent_name> --against=<baseline_run_id>

# Drift report
<project drift-report> --since=7d --agent=<agent_name>
```
