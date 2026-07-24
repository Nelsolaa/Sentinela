import math
import time

from fastapi import HTTPException, Request, Response, status
from limits import parse
from limits.storage import storage_from_string
from limits.strategies import MovingWindowRateLimiter

from Security.config import (
    HEALTH_RATE_LIMIT,
    INGEST_RATE_LIMIT,
    RATE_LIMIT_STORAGE_URI,
    READ_RATE_LIMIT,
)

_storage = storage_from_string(RATE_LIMIT_STORAGE_URI)
_limiter = MovingWindowRateLimiter(_storage)


class RateLimitDependency:
    def __init__(self, scope: str, limit: str) -> None:
        self.scope = scope
        self.limit = parse(limit)

    def __call__(self, request: Request, response: Response) -> None:
        client = request.client.host if request.client else "unknown"
        allowed = _limiter.hit(self.limit, "sentinela", self.scope, client)
        window = _limiter.get_window_stats(
            self.limit,
            "sentinela",
            self.scope,
            client,
        )
        retry_after = max(1, math.ceil(window.reset_time - time.time()))

        headers = {
            "X-RateLimit-Limit": str(self.limit.amount),
            "X-RateLimit-Remaining": str(max(0, window.remaining)),
            "X-RateLimit-Reset": str(math.ceil(window.reset_time)),
        }

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded.",
                headers={**headers, "Retry-After": str(retry_after)},
            )

        for name, value in headers.items():
            response.headers[name] = value


ingest_rate_limit = RateLimitDependency("ingest", INGEST_RATE_LIMIT)
read_rate_limit = RateLimitDependency("read", READ_RATE_LIMIT)
health_rate_limit = RateLimitDependency("health", HEALTH_RATE_LIMIT)


def reset_rate_limits() -> None:
    _storage.reset()
