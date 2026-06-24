"""Rate limiting for high-risk public endpoints."""

from __future__ import annotations

import hashlib
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock
from typing import Any, Protocol

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings


@dataclass(frozen=True)
class RateLimitRule:
    name: str
    method: str
    path_prefix: str
    max_requests: int
    window_seconds: int


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int = 0
    backend: str = "memory"
    fallback_used: bool = False


class RateLimiter(Protocol):
    def check(self, *, rule: RateLimitRule, subject: str) -> RateLimitDecision: ...


class InMemoryRateLimiter:
    """Sliding-window limiter suitable for a first app-level protection slice."""

    def __init__(self, *, now: Callable[[], float] | None = None) -> None:
        self._now = now or time.monotonic
        self._events: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, *, rule: RateLimitRule, subject: str) -> RateLimitDecision:
        now = self._now()
        window_start = now - rule.window_seconds
        key = (rule.name, subject)
        with self._lock:
            events = self._events[key]
            while events and events[0] <= window_start:
                events.popleft()
            if len(events) >= rule.max_requests:
                retry_after = max(1, int(rule.window_seconds - (now - events[0])))
                return RateLimitDecision(
                    allowed=False,
                    limit=rule.max_requests,
                    remaining=0,
                    retry_after_seconds=retry_after,
                )
            events.append(now)
            remaining = max(0, rule.max_requests - len(events))
            return RateLimitDecision(
                allowed=True,
                limit=rule.max_requests,
                remaining=remaining,
            )

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


class SupabaseRateLimiter:
    """Postgres-backed limiter for multi-instance deployments.

    The subject is hashed before leaving the process so operational tables never
    store raw IPs, public invoice tokens, JWTs, or request payloads.
    """

    def __init__(
        self,
        *,
        db_factory: Callable[[], Any] | None = None,
        fallback_limiter: InMemoryRateLimiter | None = None,
        fallback_enabled: bool = True,
        subject_salt: str = "",
    ) -> None:
        self._db_factory = db_factory or _supabase_service_role_client
        self._fallback_limiter = fallback_limiter or InMemoryRateLimiter()
        self._fallback_enabled = fallback_enabled
        self._subject_salt = subject_salt
        self._backend_failure_count = 0
        self._lock = Lock()

    @property
    def backend_failure_count(self) -> int:
        with self._lock:
            return self._backend_failure_count

    def check(self, *, rule: RateLimitRule, subject: str) -> RateLimitDecision:
        try:
            result = self._db_factory().rpc(
                "check_rate_limit",
                {
                    "p_rule_name": rule.name,
                    "p_subject_hash": hash_subject(subject, salt=self._subject_salt),
                    "p_max_requests": rule.max_requests,
                    "p_window_seconds": rule.window_seconds,
                },
            ).execute()
            row = _first_result_row(result.data)
            request_count = int(row.get("request_count") or 0)
            allowed = bool(row.get("allowed"))
            retry_after = int(row.get("retry_after_seconds") or 0)
            return RateLimitDecision(
                allowed=allowed,
                limit=rule.max_requests,
                remaining=max(0, rule.max_requests - request_count),
                retry_after_seconds=retry_after,
                backend="supabase",
            )
        except Exception:
            with self._lock:
                self._backend_failure_count += 1
            try:
                from app.services.operational_telemetry import telemetry

                telemetry.record_background_failure("rate_limit_distributed_backend")
            except Exception:
                pass
            if not self._fallback_enabled:
                return RateLimitDecision(
                    allowed=False,
                    limit=rule.max_requests,
                    remaining=0,
                    retry_after_seconds=1,
                    backend="supabase",
                )
            fallback = self._fallback_limiter.check(rule=rule, subject=subject)
            return RateLimitDecision(
                allowed=fallback.allowed,
                limit=fallback.limit,
                remaining=fallback.remaining,
                retry_after_seconds=fallback.retry_after_seconds,
                backend="memory",
                fallback_used=True,
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply configured rate limits to public/auth endpoints."""

    def __init__(
        self,
        app,
        *,
        rules: list[RateLimitRule],
        limiter: RateLimiter | None = None,
        enabled: bool = True,
    ) -> None:
        super().__init__(app)
        self.rules = rules
        self.limiter = limiter or build_rate_limiter()
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        rule = self._matching_rule(request)
        if not self.enabled or rule is None:
            return await call_next(request)

        decision = self.limiter.check(rule=rule, subject=_client_subject(request))
        if not decision.allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": {
                        "code": "rate_limit_exceeded",
                        "message": "Too many requests. Please wait and try again.",
                    }
                },
                headers={
                    "Retry-After": str(decision.retry_after_seconds),
                    "X-RateLimit-Limit": str(decision.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Backend": decision.backend,
                    "X-RateLimit-Fallback": "1" if decision.fallback_used else "0",
                },
            )

        response: Response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(decision.limit)
        response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
        response.headers["X-RateLimit-Backend"] = decision.backend
        response.headers["X-RateLimit-Fallback"] = "1" if decision.fallback_used else "0"
        return response

    def _matching_rule(self, request: Request) -> RateLimitRule | None:
        method = request.method.upper()
        path = request.url.path
        for rule in self.rules:
            if method == rule.method.upper() and path.startswith(rule.path_prefix):
                return rule
        return None


def _client_subject(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def build_rate_limiter() -> RateLimiter:
    backend = settings.rate_limit_backend.strip().lower()
    if backend in {"supabase", "postgres", "distributed"}:
        return SupabaseRateLimiter(
            fallback_enabled=settings.rate_limit_distributed_fallback_to_memory,
            subject_salt=settings.supabase_service_role_key[:32],
        )
    return InMemoryRateLimiter()


def hash_subject(subject: str, *, salt: str = "") -> str:
    payload = f"{salt}:{subject}".encode("utf-8", errors="ignore")
    return hashlib.sha256(payload).hexdigest()


def _first_result_row(data: Any) -> dict[str, Any]:
    if isinstance(data, list) and data:
        row = data[0]
        return row if isinstance(row, dict) else {}
    if isinstance(data, dict):
        return data
    return {}


def _supabase_service_role_client() -> Any:
    from supabase import create_client

    return create_client(settings.supabase_url, settings.supabase_service_role_key)
