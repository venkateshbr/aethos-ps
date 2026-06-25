# GitHub Actions Billing Runbook

Use this runbook when GitHub Actions jobs fail before any workflow step starts.

Tracked by: #319

## Failure Signature

Recent Aethos PS PR checks failed with this pattern:

- Workflow run completes in 1-4 seconds.
- Every affected job has `steps: []`.
- Job metadata has `runner_id: 0`, empty `runner_name`, and no runner group.
- `gh run view --log-failed` cannot return useful logs because checkout/setup
  never started.

This is not the same as a lint, test, dependency, or workflow syntax failure.
The runner is never assigned.

## Confirm The Cause

Inspect the workflow jobs:

```bash
gh run view <run_id> --json jobs,status,conclusion,url
```

Pick a failed job `databaseId`, then inspect check-run annotations:

```bash
gh api repos/venkateshbr/aethos-ps/check-runs/<job_database_id>/annotations
```

The #319 root cause is confirmed when the annotation says:

```text
The job was not started because recent account payments have failed or your spending limit needs to be increased. Please check the 'Billing & plans' section in your settings
```

Observed example:

- Run: `28143593801`
- Job: `83345865038`
- Workflow: `CI`
- Branch: `codex/scheduled-finance-ops-e2e`
- Symptom: `Backend tests (unit + property)` failed with `steps: []`.

Repository Actions settings were checked and are not the blocker:

```bash
gh api repos/venkateshbr/aethos-ps/actions/permissions
gh api repos/venkateshbr/aethos-ps/actions/permissions/workflow
```

Observed values:

```json
{"enabled":true,"allowed_actions":"all","sha_pinning_required":false}
{"default_workflow_permissions":"read","can_approve_pull_request_reviews":false}
```

Read-only workflow permissions are sufficient for the current checkout, lint,
test, and build jobs.

## Required Owner/Admin Action

This cannot be fixed from repository YAML or application code. A GitHub account,
organization, or enterprise billing owner must:

1. Open GitHub `Billing & plans` for the repository owner
   `venkateshbr/aethos-ps`.
2. Resolve any failed payment method or unpaid balance.
3. Review GitHub Actions metered-product budget or legacy spending-limit
   settings and increase the Actions budget/limit if hosted runners are being
   blocked.
4. Confirm that the repository is still allowed to use GitHub-hosted runners.
5. Rerun the failed workflow after billing is resolved.

GitHub references:

- [GitHub Actions billing](https://docs.github.com/billing/managing-billing-for-github-actions/about-billing-for-github-actions)
- [Setting up budgets to control spending on metered products](https://docs.github.com/en/billing/how-tos/set-up-budgets)
- [Billing and usage for GitHub Actions](https://docs.github.com/en/actions/concepts/billing-and-usage)

## Rerun And Verify

After the billing owner resolves the account state:

```bash
gh run rerun <run_id> --failed
gh pr checks <pr_number> --watch
```

The issue is fixed only when:

- Jobs show normal checkout/setup/build/test steps instead of `steps: []`.
- Failed jobs, if any, produce normal logs.
- At least one PR runs the CI workflow from queued to completed with runner
  assignment and step logs.

If the same annotation still appears, the account remains blocked. Do not spend
time editing `.github/workflows/ci.yml` until the billing annotation changes.

## Temporary Local Verification

Until hosted runners are unblocked, PR authors must run the equivalent local
checks and post the commands/results on the PR. For the current CI workflow this
usually means:

```bash
cd backend && uv run ruff check app/
cd backend && uv run pytest tests/unit/ tests/property/ -v --tb=short
cd frontend && npm ci
cd frontend && npx ng lint
cd frontend && npx ng build --configuration=production
```

Known local caveat: `npx ng lint` currently has no Angular lint target in this
repository, while the CI job is marked `continue-on-error`. Treat build,
TypeScript, Playwright, backend lint, and backend tests as the meaningful gates
until the lint target is either added or removed from CI.
