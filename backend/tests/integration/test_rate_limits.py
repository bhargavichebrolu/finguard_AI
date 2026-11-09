"""The PostgreSQL rate limiter (Phase 5 M3): exact limits, waits, expiry and simultaneous requests.

Separate connections stand in for separate processes: each `hit` takes its own connection and
transaction, exactly as it does in each API process.
"""

import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import text
from tests.conftest import empty_all_tables

from app.core.errors import RateLimitedError
from app.core.rate_limit import DatabaseRateLimiter, MemoryRateLimiter

pytestmark = pytest.mark.database


@pytest.fixture
def database_limiter(db_engine):
    empty_all_tables(db_engine)
    yield DatabaseRateLimiter()
    empty_all_tables(db_engine)


@pytest.fixture(params=["memory", "database"])
def any_limiter(request, db_engine):
    if request.param == "memory":
        return MemoryRateLimiter()
    empty_all_tables(db_engine)
    return DatabaseRateLimiter()


def test_allows_exactly_the_limit_then_refuses_with_a_wait(any_limiter):
    for _ in range(3):
        any_limiter.hit("predict:user-1", 3, 60)
    with pytest.raises(RateLimitedError) as refused:
        any_limiter.hit("predict:user-1", 3, 60)
    assert 1 <= int(refused.value.headers["Retry-After"]) <= 61
    any_limiter.hit("predict:user-2", 3, 60)  # other keys are unaffected


def test_refused_attempts_are_not_counted(any_limiter):
    for _ in range(2):
        any_limiter.hit("k", 2, 60)
    for _ in range(5):
        with pytest.raises(RateLimitedError):
            any_limiter.hit("k", 2, 60)


def test_events_expire_after_the_window(any_limiter):
    any_limiter.hit("short", 1, 1)
    with pytest.raises(RateLimitedError):
        any_limiter.hit("short", 1, 1)
    time.sleep(1.2)
    any_limiter.hit("short", 1, 1)


def test_sign_in_pattern_check_record_and_clear(any_limiter):
    for _ in range(2):
        any_limiter.require_below_limit("login:a", 2, 60)
        any_limiter.record("login:a")
    with pytest.raises(RateLimitedError):
        any_limiter.require_below_limit("login:a", 2, 60)
    any_limiter.clear("login:a")
    any_limiter.require_below_limit("login:a", 2, 60)


def test_simultaneous_requests_never_exceed_the_limit(database_limiter):
    def attempt(_: int) -> bool:
        try:
            database_limiter.hit("upload:shared", 5, 60)
            return True
        except RateLimitedError:
            return False

    with ThreadPoolExecutor(max_workers=20) as pool:
        allowed = sum(pool.map(attempt, range(20)))
    assert allowed == 5


def test_expired_events_are_deleted_as_the_key_is_used(database_limiter, db_engine):
    database_limiter.hit("tidy", 5, 1)
    database_limiter.hit("tidy", 5, 1)
    time.sleep(1.2)
    database_limiter.hit("tidy", 5, 1)
    with db_engine.connect() as connection:
        rows = connection.execute(
            text("SELECT count(*) FROM rate_limit_events WHERE key = 'tidy'")
        ).scalar()
    assert rows == 1


def test_counts_use_database_time_and_survive_a_new_limiter(database_limiter):
    # A new limiter object stands in for a restarted process: nothing is held in memory.
    for _ in range(2):
        database_limiter.hit("restart", 2, 60)
    with pytest.raises(RateLimitedError):
        DatabaseRateLimiter().hit("restart", 2, 60)


def test_fixed_window_allows_exactly_the_limit(any_limiter):
    for _ in range(4):
        any_limiter.hit_window("predict:window", 4, 60)
    with pytest.raises(RateLimitedError) as refused:
        any_limiter.hit_window("predict:window", 4, 60)
    assert 1 <= int(refused.value.headers["Retry-After"]) <= 61


def test_fixed_window_admits_exactly_the_limit_under_simultaneous_requests(database_limiter):
    def attempt(_: int) -> bool:
        try:
            database_limiter.hit_window("predict:simultaneous", 5, 60)
            return True
        except RateLimitedError:
            return False

    with ThreadPoolExecutor(max_workers=20) as pool:
        allowed = sum(pool.map(attempt, range(20)))
    assert allowed == 5


def test_fixed_window_starts_again_in_the_next_window(database_limiter):
    # Wait for the start of a fresh two-second window so the test is not on a boundary.
    time.sleep(2 - time.time() % 2 + 0.05)
    database_limiter.hit_window("predict:rollover", 1, 2)
    with pytest.raises(RateLimitedError):
        database_limiter.hit_window("predict:rollover", 1, 2)
    time.sleep(2.1)
    database_limiter.hit_window("predict:rollover", 1, 2)
