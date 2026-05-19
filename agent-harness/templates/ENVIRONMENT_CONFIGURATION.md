# Environment Configuration

Copy `.env.example` to `.env` and fill in environment-specific values.

Never commit real secrets.

## Required Variables

| Variable | Required | Purpose | Notes |
| --- | --- | --- | --- |
| `<VAR>` | Yes | `<purpose>` | `<placeholder example>` |

## Optional Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `<VAR>` | `<default>` | `<purpose>` |

## Pre-Run Checklist

- `.env` exists and is gitignored.
- Secrets are environment-specific.
- Webhook secrets match the configured endpoint.
- Public frontend URLs point at reachable API URLs.
- Production debug flags are disabled.

