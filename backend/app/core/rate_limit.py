"""Small in-process rate limiter for high-risk public endpoints."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


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


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply configured rate limits to public/auth endpoints."""

    def __init__(
        self,
        app,
        *,
        rules: list[RateLimitRule],
        limiter: InMemoryRateLimiter | None = None,
        enabled: bool = True,
    ) -> None:
        super().__init__(app)
        self.rules = rules
        self.limiter = limiter or InMemoryRateLimiter()
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
                },
            )

        response: Response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(decision.limit)
        response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
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
