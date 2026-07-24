"""Executable authz coverage gate over ALL mutating routes (#378, ADR 0005 D1).

The audit found "many routes require only authentication". This test enumerates
every state-changing route (POST/PUT/PATCH/DELETE) under the v1 API, classifies
its gate from the full dependency tree, and asserts that anything NOT gated by a
role or privilege is on a small, reviewed allowlist. A new mutation that ships
with only-authentication (or fully public) therefore fails CI until it is either
gated or consciously added here with a justification.

Complements test_authz_matrix.py (which pins the exact gate of crown-jewel
handlers). No live stack needed — pure signature/dependency introspection.
"""

from __future__ import annotations

import importlib
import pkgutil

import pytest

import app.api.v1.endpoints as endpoints_pkg

pytestmark = pytest.mark.unit

_AUTH_DEPS = {"get_current_user", "get_current_employee", "get_current_employee_user"}
_MUTATING = {"POST", "PUT", "PATCH", "DELETE"}


def _walk(dep):
    yield dep
    for sub in getattr(dep, "dependencies", []) or []:
        yield from _walk(sub)


def _classify(route) -> str:
    """Return 'role:x' | 'privilege:y' | 'authenticated' | 'public'."""
    role = priv = None
    authed = False
    for node in _walk(route.dependant):
        call = getattr(node, "call", None)
        if call is None:
            continue
        r = getattr(call, "aethos_min_role", None)
        if r is not None:
            role = r.value
        p = getattr(call, "aethos_privilege", None)
        if p is not None:
            priv = p
        if getattr(call, "__name__", "") in _AUTH_DEPS:
            authed = True
    if role:
        return f"role:{role}"
    if priv:
        return f"privilege:{priv}"
    return "authenticated" if authed else "public"


def _mutating_routes() -> dict[str, str]:
    """Map 'module:METHOD path' -> classification for every mutating v1 route."""
    out: dict[str, str] = {}
    for info in pkgutil.iter_modules(endpoints_pkg.__path__):
        module = importlib.import_module(f"app.api.v1.endpoints.{info.name}")
        router = getattr(module, "router", None)
        if router is None:
            continue
        for route in getattr(router, "routes", []):
            methods = (getattr(route, "methods", set()) or set()) & _MUTATING
            for method in sorted(methods):
                out[f"{info.name}:{method} {route.path}"] = _classify(route)
    return out


# Mutations that are intentionally NOT role/privilege gated, each with a reason.
# A mutation missing from here that is not role/privilege gated FAILS the test —
# add it only with a deliberate justification (Prahari review for anything money-
# or data-touching). Keep values short; the reason is the point.
ALLOWED_UNGATED: dict[str, str] = {
    # Public by design:
    "auth:POST /signup": "public — tenant self-signup",
    "webhooks:POST /stripe": "public — Stripe signature verified in-handler",
    "atlas_tools:POST /execute": "token-guarded — validates a server-issued tool context token in-handler (Nous)",
    # Authenticated self-service (user- or tenant-scoped, no elevated authority):
    "auth:POST /complete-password-change": "the authenticated user rotating their own password",
    "billing:POST /portal": "tenant self-service — opens own Stripe billing portal",
    "billing:POST /start-trial": "tenant self-service — starts own trial",
    "chat:POST /threads": "user's own chat thread",
    "chat:POST /threads/{thread_id}/messages": "user's own chat message",
    "documents:POST /upload": "authenticated tenant document upload (tenant-scoped)",
    "documents:POST /{document_id}/extract": "authenticated extraction of a tenant document",
    "documents:DELETE /{document_id}": "authenticated delete of a tenant document",
    "engagements:POST /{id}/draft-invoice": "L2 draft→Inbox; posting still requires invoices.post",
    "inbox:POST /tasks/{task_id}/escalate": "escalating a task the member can already see",
    "timesheet:POST /entries": "timesheet portal self-service (get_current_employee)",
    "timesheet:PATCH /entries/{id}": "timesheet portal self-service (get_current_employee)",
    "timesheet:DELETE /entries/{id}": "timesheet portal self-service (get_current_employee)",
    "timesheet:POST /submit": "timesheet portal self-service (get_current_employee)",
}


def test_every_mutation_is_gated_or_explicitly_allowlisted() -> None:
    routes = _mutating_routes()
    assert routes, "no mutating routes discovered — introspection regressed"

    ungated = {
        key: cls
        for key, cls in routes.items()
        if cls in ("authenticated", "public") and key not in ALLOWED_UNGATED
    }
    assert not ungated, (
        "New mutating route(s) ship without a role/privilege gate. Add a "
        "require_role/require_privilege gate, or (only after review) add the route "
        "to ALLOWED_UNGATED with a justification:\n"
        + "\n".join(f"  {k} -> {v}" for k, v in sorted(ungated.items()))
    )


def test_allowlist_has_no_stale_entries() -> None:
    """An allowlisted route that got gated (or removed) must be pruned, so the
    allowlist keeps shrinking toward zero and never hides a real regression."""
    routes = _mutating_routes()
    stale = [
        key
        for key in ALLOWED_UNGATED
        if key not in routes or routes[key] not in ("authenticated", "public")
    ]
    assert not stale, f"ALLOWED_UNGATED has stale entries (now gated/removed): {stale}"


def test_majority_of_mutations_are_role_or_privilege_gated() -> None:
    # Sanity floor: the ungated allowlist must stay small relative to the surface.
    routes = _mutating_routes()
    gated = sum(1 for c in routes.values() if c.startswith(("role:", "privilege:")))
    assert gated >= len(routes) - len(ALLOWED_UNGATED)
    assert gated / len(routes) > 0.8, "authz coverage fell below 80% of mutations"
