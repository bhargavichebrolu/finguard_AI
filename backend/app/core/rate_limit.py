"""Rate limits counted in PostgreSQL, so every API process and every restart see the same counts.

`limiter` uses the store chosen by RATE_LIMIT_STORE: "database" (the default, and the only one
production accepts) or "memory", which counts in this process only and resets on restart. The
memory store is kept for comparison measurements and for code paths without a database.

Each limit is a sliding window: an event counts while it is younger than the window.
"""

import threading
import time
from collections import defaultdict, deque
from typing import Protocol

from sqlalchemy import text

from app.core.errors import RateLimitedError

_LOCK = text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))")
_RECENT = """
    recent AS (
        SELECT count(*) AS events, min(occurred_at) AS oldest
        FROM rate_limit_events
        WHERE key = :key AND occurred_at > clock_timestamp() - make_interval(secs => :window)
    )
"""
_WAIT = "floor(extract(epoch FROM oldest + make_interval(secs => :window) - clock_timestamp()))"
_CHECK = text(f"WITH {_RECENT} SELECT events, {_WAIT} AS wait FROM recent")
# One statement after the lock: forget this key's expired events, count the live ones, and add
# this event only if the limit is not yet reached. Run after the lock in a new statement, so its
# snapshot includes every event committed by another process before the lock was granted.
_HIT = text(
    f"""
    WITH expired AS (
        DELETE FROM rate_limit_events
        WHERE key = :key AND occurred_at <= clock_timestamp() - make_interval(secs => :window)
    ),
    {_RECENT},
    counted AS (
        INSERT INTO rate_limit_events (key) SELECT :key FROM recent WHERE events < :limit
    )
    SELECT events, {_WAIT} AS wait FROM recent
    """
)

# Per-request limits: one atomic upsert in autocommit, so one round trip. It increments this
# window's counter, or returns no row when the counter is already at the limit. A fixed window
# can admit up to twice the limit across a window boundary; the sliding window above is used
# where that matters (failed sign-ins). Chosen in Phase 5 M3 after the sliding-window version
# exceeded the prediction latency budget.
_WINDOW_HIT = text(
    """
    INSERT INTO rate_limit_windows AS w (key, window_start, count)
    VALUES (
        :key,
        to_timestamp(floor(extract(epoch FROM clock_timestamp()) / :window) * :window),
        1
    )
    ON CONFLICT (key, window_start) DO UPDATE SET count = w.count + 1 WHERE w.count < :limit
    RETURNING w.count
    """
)
_WINDOW_WAIT = text(
    "SELECT :window - mod(extract(epoch FROM clock_timestamp())::numeric, :window) AS wait"
)


class RateLimitStore(Protocol):
    """What a rate-limit store must do."""

    def require_below_limit(self, key: str, limit: int, window_seconds: int) -> None: ...
    def record(self, key: str) -> None: ...
    def hit(self, key: str, limit: int, window_seconds: int) -> None: ...
    def hit_window(self, key: str, limit: int, window_seconds: int) -> None: ...
    def clear(self, key: str) -> None: ...
    def reset(self) -> None: ...


def _refuse(wait_seconds: float | None) -> None:
    raise RateLimitedError(max(int(wait_seconds or 0), 0) + 1)


class MemoryRateLimiter:
    """Counts in this process only. Several processes each allow the full limit."""

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
                _refuse(events[0] + window_seconds - now)

    def record(self, key: str) -> None:
        """Count one event."""
        with self._lock:
            self._events[key].append(time.monotonic())

    def hit(self, key: str, limit: int, window_seconds: int) -> None:
        """Raise if the key is at its limit, otherwise count this call."""
        now = time.monotonic()
        with self._lock:
            events = self._recent(key, window_seconds, now)
            if len(events) >= limit:
                _refuse(events[0] + window_seconds - now)
            events.append(now)

    def hit_window(self, key: str, limit: int, window_seconds: int) -> None:
        """Per-request limit. In memory the sliding window costs nothing extra, so it is used."""
        self.hit(key, limit, window_seconds)

    def clear(self, key: str) -> None:
        """Forget a key's events, such as after a successful login."""
        with self._lock:
            self._events.pop(key, None)

    def reset(self) -> None:
        """Forget everything. Tests use this."""
        with self._lock:
            self._events.clear()


class DatabaseRateLimiter:
    """Counts in the database, shared by every process, using database time."""

    @staticmethod
    def _engine():
        from app.database.session import get_engine  # imported late: core must load first

        return get_engine()

    def hit_window(self, key: str, limit: int, window_seconds: int) -> None:
        """Per-request limit: one autocommit upsert into rate_limit_windows."""
        engine = self._engine().execution_options(isolation_level="AUTOCOMMIT")
        with engine.connect() as connection:
            parameters = {"key": key, "limit": limit, "window": window_seconds}
            counted = connection.execute(_WINDOW_HIT, parameters).first()
            if counted is None:
                _refuse(connection.execute(_WINDOW_WAIT, {"window": window_seconds}).scalar())

    def require_below_limit(self, key: str, limit: int, window_seconds: int) -> None:
        """Raise if the key has reached its limit, without counting this call."""
        with self._engine().connect() as connection:
            events, wait = connection.execute(_CHECK, {"key": key, "window": window_seconds}).one()
        if events >= limit:
            _refuse(wait)

    def record(self, key: str) -> None:
        """Count one event, committed at once so a failing request still counts."""
        with self._engine().begin() as connection:
            connection.execute(
                text("INSERT INTO rate_limit_events (key) VALUES (:key)"), {"key": key}
            )

    def hit(self, key: str, limit: int, window_seconds: int) -> None:
        """Raise if the key is at its limit, otherwise count this call, atomically per key."""
        with self._engine().begin() as connection:
            connection.execute(_LOCK, {"key": key})
            events, wait = connection.execute(
                _HIT, {"key": key, "limit": limit, "window": window_seconds}
            ).one()
        if events >= limit:
            _refuse(wait)

    def clear(self, key: str) -> None:
        """Forget a key's events, such as after a successful login."""
        with self._engine().begin() as connection:
            connection.execute(text("DELETE FROM rate_limit_events WHERE key = :key"), {"key": key})

    def reset(self) -> None:
        """Forget everything. Tests use this."""
        with self._engine().begin() as connection:
            connection.execute(text("DELETE FROM rate_limit_events"))
            connection.execute(text("DELETE FROM rate_limit_windows"))


class ConfiguredRateLimiter:
    """The limiter the application uses: the store named by RATE_LIMIT_STORE."""

    def __init__(self) -> None:
        self.memory = MemoryRateLimiter()
        self.database = DatabaseRateLimiter()

    def store(self) -> RateLimitStore:
        from app.core.config import get_settings

        return self.database if get_settings().rate_limit_store == "database" else self.memory

    def require_below_limit(self, key: str, limit: int, window_seconds: int) -> None:
        self.store().require_below_limit(key, limit, window_seconds)

    def record(self, key: str) -> None:
        self.store().record(key)

    def hit(self, key: str, limit: int, window_seconds: int) -> None:
        self.store().hit(key, limit, window_seconds)

    def hit_window(self, key: str, limit: int, window_seconds: int) -> None:
        self.store().hit_window(key, limit, window_seconds)

    def clear(self, key: str) -> None:
        self.store().clear(key)

    def reset(self) -> None:
        self.memory.reset()
        self.store().reset()


limiter = ConfiguredRateLimiter()
