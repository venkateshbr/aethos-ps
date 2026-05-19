# Contract Testing

Contract tests verify that two systems agree on the shape and semantics of the messages they exchange — without spinning both systems up together. They catch breaking changes earlier and cheaper than e2e tests can.

## When to use contract tests

Use them at every boundary you control:

- **Frontend ↔ Backend HTTP API** — every endpoint the frontend calls.
- **Backend ↔ Internal service** — RPCs, queues, event buses you own on both ends.
- **Agent ↔ Tool** — the tool schemas the LLM is told it can call.
- **Backend ↔ External provider** — the small subset of provider behavior you actually depend on (Stripe webhook shapes, Plaid object structure).
- **Webhook in / out** — the signed envelope and payload shape.

## When *not* to rely on contract tests alone

Contract tests prove the messages match. They do not prove the business workflow works. E2E tests are still required for:

- User-facing workflows (engagement → cash, signup → first invoice, etc.).
- Cross-system effect verification (the Stripe webhook arriving actually marks the invoice paid, posts a journal, and notifies the user).
- Auth/RBAC behavior in the real UI.
- Money totals and reconciliation.

A common failure mode is "contract tests green, product broken" — the JSON shapes are right but the semantics aren't.

## Consumer-driven contracts

For inter-service contracts you control, prefer consumer-driven contract testing (e.g., Pact):

1. **Consumer** writes a test that defines what request it sends and what response it expects.
2. The consumer test produces a **pact file** (JSON) describing the interaction.
3. The pact is published to a broker (or committed to the repo if there is no broker).
4. The **provider** runs a verification step: it replays each recorded request and asserts the response is at least what was promised.

Benefits:

- Provider and consumer can be tested independently and deployed independently.
- "Can I deploy?" becomes a deterministic check, not a coordination meeting.
- Breaking changes are surfaced at consumer-PR time, not at integration.

Limitations:

- Pact tests are *message* tests, not behavior tests. Validate behavior separately.
- Pacts are only as good as the consumer expectations — a consumer that does not exercise a field will not protect it.

## Inter-tool contracts (agent ↔ tool)

When an agent calls a tool, the tool's input schema *is* the contract. Test it explicitly:

- **Schema test** — the tool definition's `input_schema` validates with the same JSON Schema validator your tool dispatcher uses.
- **Round-trip test** — given a valid input, the tool runs and returns a structurally valid output per its declared output type.
- **Strict-mode test** — if the API supports strict tool use (Anthropic `strict: true`), the tool roundtrips with strict mode enabled.
- **Hallucinated-field test** — given an LLM that passes an undeclared field, the tool rejects cleanly with a structured error, not a stack trace.

These tests are part of the agent eval pack, not the integration suite.

## External provider contracts

For Stripe, Plaid, Resend, and similar:

- Pin the **API version** in the provider client.
- Capture the **subset of the schema** you actually depend on in a contract test (you do not need to validate the entire Stripe object — just the fields your code reads).
- Use the provider's **fixture / sandbox webhooks** in tests. Do not hand-craft webhooks unless replaying real captured fixtures.
- When the provider releases a new API version, run the contract tests against the new version before bumping.

## OpenAPI / schema diffing

If the project publishes an OpenAPI spec:

- The OpenAPI spec is committed.
- A schema-diff check runs on every PR: a "breaking change" diff fails CI unless explicitly approved.
- Versioning policy: additive changes ship freely; breaking changes require a `v` bump and a deprecation path.

For projects without OpenAPI, prefer typed schemas at the boundary (Pydantic / Zod / TypeBox) and assert serialization round-trips in tests.

## Idempotency contract

For any endpoint that accepts idempotency keys (webhooks, payment intents, bill payment files):

- Contract test: same key + same payload → identical effect after replay.
- Contract test: same key + different payload → declared error code (e.g., 409 Conflict).

## Backward / forward compatibility

The harness defaults to:

- **Backward compatible**: a producer adding a new field must not break older consumers.
- **Tolerant readers**: consumers ignore unknown fields. Tests assert this is true.
- **Versioned breaking changes**: any field removal or semantic change requires a new endpoint version or a new event type.

## Where contracts live

Recommended repo layout:

```
shared/
  schemas/
    openapi.yaml                    # If applicable
    events/
      invoice.sent.json             # JSON Schema for each domain event
      payment.received.json
    tools/
      propose_invoice.json          # JSON Schema for each agent tool input/output
contracts/
  pacts/
    web-app__backend.json           # Consumer-driven pacts
  fixtures/
    stripe/                         # Captured provider fixtures
    plaid/
```

## CI integration

- Schema diff: blocks PR on breaking change without approval label.
- Pact verification: provider repo runs `pact-verifier` against the latest broker pacts; failure blocks deploy.
- Agent tool schema tests: run as part of the agent eval suite.
- Provider fixture tests: run on every PR; pinned API version.

## References

- Pact docs — consumer-driven contract testing, broker, can-i-deploy.
- Anthropic tool-use — strict tool use (`strict: true`) for guaranteed schema conformance.
- See also: [testing-standard.md](testing-standard.md), [agent-eval-standard.md](agent-eval-standard.md).
