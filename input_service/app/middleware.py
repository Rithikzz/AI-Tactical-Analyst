from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import Request, Response

from .config import RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SECONDS


class RateLimitMiddleware:
    def __init__(self, app):
        self.app = app
        self._requests: Dict[str, Deque[float]] = defaultdict(deque)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        if request.url.path.startswith("/health") or request.url.path.startswith("/auth"):
            await self.app(scope, receive, send)
            return

        key = request.client.host if request.client else "anonymous"
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW_SECONDS
        q = self._requests[key]
        while q and q[0] < window_start:
            q.popleft()
        if len(q) >= RATE_LIMIT_REQUESTS:
            response = Response(
                content="Rate limit exceeded.",
                status_code=429,
                media_type="text/plain",
            )
            await response(scope, receive, send)
            return

        q.append(now)
        await self.app(scope, receive, send)
