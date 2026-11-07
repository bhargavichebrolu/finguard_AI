"""A small in-memory rate limiter. Counts live in this process and are lost on restart."""

import threading
import time
from collections import defaultdict, deque

from app.core.errors import RateLimitedError


class RateLimiter:
    """Count events per key within a sliding time window."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _recent(self, key: str, window_seconds: int, now: float) -> deque[float]:
        events = self._events[key]
        while events and events[0] <= now - window_seconds:
            events.popleft()
        return events

    def require_below_limit(self, key: str, limit: int, window_seconds: int) -> None:
        """Raise if the key has reached its limit, without counting this call."""
        now = time.monotonic()
        with self._lock:
            events = self._recent(key, window_seconds, now)
            if len(events) >= limit:
                retry_after = int(events[0] + window_seconds - now) + 1
                raise RateLimitedError(retry_after)

    def record(self, key: str) -> None:
        """Count one event."""
        with self._lock:
            self._events[key].append(time.monotonic())

    def hit(self, key: str, limit: int, window_seconds: int) -> None:
        """Raise if the key is at its limit, otherwise count this call."""
        self.require_below_limit(key, limit, window_seconds)
        self.record(key)

    def clear(self, key: str) -> None:
        """Forget a key's events, such as after a successful login."""
        with self._lock:
            self._events.pop(key, None)

    def reset(self) -> None:
        """Forget everything. Tests use this."""
        with self._lock:
            self._events.clear()


limiter = RateLimiter()
