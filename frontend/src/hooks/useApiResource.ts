/**
 * Load data from the API with loading and error states, which every page shows the same way.
 */
import { useCallback, useEffect, useRef, useState, type DependencyList } from "react";

import { ApiError, toApiError } from "../services/api";

export interface Resource<T> {
  data: T | null;
  error: ApiError | null;
  loading: boolean;
  reload: () => void;
}

/** Run `load` now and whenever `deps` change. A slow earlier response never replaces a newer one. */
export function useApiResource<T>(load: () => Promise<T>, deps: DependencyList): Resource<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);
  const latest = useRef(0);

  useEffect(() => {
    const request = ++latest.current;
    setLoading(true);
    setError(null);
    load()
      .then((value) => {
        if (request === latest.current) setData(value);
      })
      .catch((caught: unknown) => {
        if (request === latest.current) setError(toApiError(caught));
      })
      .finally(() => {
        if (request === latest.current) setLoading(false);
      });
    // `load` is rebuilt on every render, so `deps` decide when to reload.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, attempt]);

  const reload = useCallback(() => setAttempt((count) => count + 1), []);
  return { data, error, loading, reload };
}

/** Call `callback` every `intervalMs` while `active` is true, waiting longer after `slowAfterMs`. */
export function usePolling(
  callback: () => void,
  intervalMs: number,
  active: boolean,
  slowAfterMs = 30_000,
): void {
  const saved = useRef(callback);
  saved.current = callback;

  useEffect(() => {
    if (!active) return undefined;
    const started = Date.now();
    let timer: number;
    const tick = () => {
      saved.current();
      const delay = Date.now() - started > slowAfterMs ? intervalMs * 3 : intervalMs;
      timer = window.setTimeout(tick, delay);
    };
    timer = window.setTimeout(tick, intervalMs);
    return () => window.clearTimeout(timer);
  }, [intervalMs, active, slowAfterMs]);
}
