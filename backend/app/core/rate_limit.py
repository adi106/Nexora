import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class RateLimiter:
    """
    Simple in-memory sliding-window rate limiter, keyed by client IP.

    This is process-local: it protects a single backend instance from
    brute-force/spam bursts, but does not coordinate across multiple
    instances behind a load balancer. A multi-instance deployment needs
    a shared store (e.g. Redis) for this to hold across instances.
    """

    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, deque] = defaultdict(deque)

    def reset(self) -> None:
        self._buckets.clear()

    def __call__(self, request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        bucket = self._buckets[client_ip]
        now = time.monotonic()

        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()

        if len(bucket) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )

        bucket.append(now)


login_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)
registration_rate_limiter = RateLimiter(max_requests=5, window_seconds=60)
