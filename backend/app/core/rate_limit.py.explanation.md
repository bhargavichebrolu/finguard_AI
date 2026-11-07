# rate_limit.py

Source: [backend/app/core/rate_limit.py](rate_limit.py)

## A. File Purpose
Limits how often something can happen, such as failed logins per client and account, or uploads per user.

## B. Why This File Exists
PRD section 10 asks for rate limiting where supported. Unlimited login attempts would allow password guessing, and unlimited uploads could exhaust a small server.

## C. Dependencies
- **Libraries:** `threading`, `time`, `collections`.
- **Internal modules:** `app.core.errors`.
- **External services / database:** none.
- **Depended on by:** `auth_service.py`, `security/dependencies.py`.

## D. Every Function Explained

### `__init__`
Creates the empty event store and its lock.

### `_recent`
- **Purpose:** return a key's events still inside the window.
- **Parameters / types:** `key: str`, `window_seconds: int`, `now: float`. **Returns / type:** `deque[float]`.
- **Internal processing:** removes expired events from the front. The caller holds the lock.
- **Error handling:** none needed. **Calls:** none. **Used by:** `require_below_limit`.

### `require_below_limit`
- **Purpose:** check without counting.
- **Parameters / types:** `key: str`, `limit: int`, `window_seconds: int`. **Returns / type:** `None`.
- **Internal processing:** works out when the oldest event expires, for the `Retry-After` header.
- **Error handling:** raises `RateLimitedError`.
- **Calls:** `_recent`. **Used by:** `hit`, `auth_service`.

### `record`
Counts one event. Login uses it separately, so only failures count.

### `hit`
Checks, then counts. Used for prediction and upload limits, where every call counts.

### `clear`
Forgets one key's events, used after a successful login.

### `reset`
Forgets everything, so tests start clean.

## E. Classes Explained

### `RateLimiter`
- **Purpose:** the counter. **Attributes:** `_events`, `_lock`. **Methods:** those above. **Inheritance:** none.

`limiter` is the shared instance.

## F. Execution Flow
A route's dependency or a service calls `hit` or `require_below_limit`. If the limit is reached, the error handler returns 429.

## G. Input and Output
Input: a key and limits. Output: nothing, or `RateLimitedError`.

## H. Important Technical Concepts
- **`time.monotonic`:** unaffected by changes to the computer's clock.
- **Sliding window:** counts events in the last N seconds, which avoids the burst possible at the boundary of fixed windows.

## I. Example
```python
limiter.hit(f"upload:{user.id}", limit=10, window_seconds=60)
```

## J. Maintenance Notes
**Known limitation:** counts are per process and reset on restart, so several workers would each have their own count. Moving to several workers needs a shared store such as Redis. Keys are never removed except by `clear`, which is acceptable at this scale but is a slow growth to watch if run for a long time with many distinct clients.

## K. Related Files
- [auth_service.py](../services/auth_service.py.explanation.md): login limits.
- [dependencies.py](../security/dependencies.py.explanation.md): request limits.
- [ADR 0003](../../../docs/decisions/0003-phase-3-decisions.md): decision 11.
