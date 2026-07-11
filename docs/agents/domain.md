# Domain documentation

This repository uses a single professional-services ERP context.

## Read before exploring or changing a domain area

1. `docs/team/PROJECT_CONTEXT.md` for stack, conventions, trust boundaries, and terminology.
2. `docs/PLAN.md` for intended product scope and historical decisions. Treat claims marked draft or pre-execution as historical until verified against code and production.
3. `domain_packs/professional-services/pack.yaml` for entities, workflows, agents, and quality rules.
4. Relevant scenario documents under `docs/test/e2e_*.md` for executable behavior.
5. Relevant ADRs under `docs/adr/`; surface conflicts explicitly rather than silently overriding a decision.

Use domain terms from those sources in issue titles, hypotheses, tests, code, and documentation. When sources disagree with implemented or verified production behavior, record the discrepancy and update the authoritative user/operations documentation as part of the same issue.
