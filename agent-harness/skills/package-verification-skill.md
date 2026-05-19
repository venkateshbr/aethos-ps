---
name: package-verification
description: Use before integrating or changing third-party package, SDK, CLI, API, webhook, or model-provider code.
---

# Package Verification Skill

## Workflow

1. Identify installed version or target version.
2. Inspect local package types/source when installed.
3. Use official docs for unstable/current APIs.
4. Confirm import path, client construction, method signatures, auth, errors, and
   pagination/webhook semantics.
5. Implement behind a small gateway/service boundary.
6. Add tests for success and failure paths.

## Integration Safety

- Never hardcode secrets.
- Verify webhook signatures.
- Log provider IDs, not secret payloads.
- Make failures graceful and observable.

