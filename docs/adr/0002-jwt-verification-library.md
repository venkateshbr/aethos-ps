# ADR 0002 — JWT verification on PyJWT (drop python-jose)

- **Status:** Accepted
- **Date:** 2026-07-23
- **Deciders:** Founder + Prahari (security) + Vastu (architecture)
- **Issue:** #384
- **Supersedes:** the python-jose verification path in `app/core/auth.py`

## Context

`app/core/auth.py` verifies every inbound Supabase JWT — the tenant auth
boundary. It accepted two families:

- **HS256** against `SUPABASE_JWT_SECRET` (legacy projects + test fixtures).
- **ES256 / RS256** resolved through the project JWKS by the token's `kid`
  (Supabase's default for new projects), with an LRU-cached JWKS that clears and
  refetches once on a `kid` miss so key rotation self-heals.

Verification ran on **python-jose**, which pulls **python-ecdsa**. `ecdsa` 0.19.2
carries **PYSEC-2026-1325** (a Minerva-style timing side-channel in P-256 signing,
key generation, and ECDH) with **no upstream fix planned** (audit #368, LR-14/
#384). Aethos only *verifies* tokens — it never signs or generates keys in the
service — so direct exploitability is low, but a permanently-unfixable advisory
sitting in the auth dependency is not acceptable for launch, and it was the sole
remaining production advisory after #385.

The blocker to swapping libraries: the **ES256/RS256 JWKS path had zero test
coverage**. Every auth test minted HS256. Replacing the verifier blind could have
silently broken production login on any Supabase-asymmetric project.

## Decision

Migrate JWT verification from python-jose to **PyJWT** (already a dependency via
`pyjwt[crypto]`), and remove python-jose — which drops `ecdsa`, `python-jose`,
and `rsa` from the lock.

Land the test safety net **first**: a new implementation-independent contract
(`tests/unit/test_jwt_verification.py`) that drives `get_current_user` through
HS256 + ES256 + RS256 (JWKS by `kid`), rotation self-heal, and the negative paths
(alg `none`, unknown `kid`, HS256-with-JWKS-`kid` confusion, expired, missing
`sub`, missing credentials). It was proven green on the **old python-jose** impl
before `auth.py` was touched, so it pins token compatibility across the swap.

Verification specifics preserved/added:
- Per-path algorithm pinning: HS256 only on the shared-secret path, ES256/RS256
  only on the JWKS path; any other `alg` (including `none`) is rejected *before*
  verification via a dedicated `_UnsupportedAlgorithmError`.
- JWK → key via `PyJWK.from_dict(jwk).key`; the LRU JWKS cache + single-refetch
  rotation behaviour is unchanged.

## Options considered

- **PyJWT (chosen):** maintained, already vendored, no ecdsa, drop-in
  `get_unverified_header` / `decode` API, first-class JWKS via `PyJWK`.
- **authlib / joserfc:** capable, but adds a new dependency surface for no gain
  over PyJWT, which we already ship.
- **Keep python-jose, document a time-bounded exception:** allowed by #384's AC
  (verification-only, no signing) but leaves an unfixable advisory in the auth
  boundary indefinitely — rejected once the PyJWT swap proved low-risk.

## Consequences

- **Positive:** locked pip-audit reports **no known vulnerabilities** after sync
  (ecdsa gone); the previously-untested asymmetric path now has a durable
  contract; algorithm handling is explicitly pinned.
- **Negative / trade-offs:** PyJWT and python-jose surface slightly different
  exception types — the auth dependency now catches `PyJWTError` plus our
  sentinels; any future code that imported `jose` must use PyJWT.
- **Migration / rollout:** dependency + lock change; `uv sync` required so the
  venv drops ecdsa (pip-audit reads the installed env, not just the lock). No
  runtime data migration.
- **Verification:** 11/11 JWT contract tests green on **both** libraries; full
  backend suite 1281 passed; locked pip-audit clean after sync.
