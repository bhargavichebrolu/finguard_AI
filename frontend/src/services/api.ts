/**
 * The one HTTP client for the API.
 *
 * The browser keeps the session in an HttpOnly cookie that this code cannot read. Requests that
 * change data copy the readable CSRF cookie into the X-CSRF-Token header. No token is ever kept
 * in browser storage.
 */
import axios, { AxiosError, type AxiosInstance } from "axios";

export const CSRF_COOKIE = "finguard_csrf";
/** In production the cookie is Secure and carries the browser-enforced __Host- prefix (Phase 5 M5). */
export const CSRF_COOKIE_NAMES = [`__Host-${CSRF_COOKIE}`, CSRF_COOKIE];
export const CSRF_HEADER = "X-CSRF-Token";
const UNSAFE_METHODS = new Set(["post", "put", "patch", "delete"]);
const SIGN_IN_PATH = "/api/v1/auth/session";
const REQUEST_TIMEOUT_MS = 30_000;

export interface FieldError {
  location: string;
  message: string;
}

/** An API failure in one shape, whatever went wrong. */
export class ApiError extends Error {
  readonly status: number;
  readonly requestId: string | null;
  readonly fieldErrors: FieldError[];
  readonly retryAfterSeconds: number | null;

  constructor(
    message: string,
    status: number,
    requestId: string | null = null,
    fieldErrors: FieldError[] = [],
    retryAfterSeconds: number | null = null,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.requestId = requestId;
    this.fieldErrors = fieldErrors;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

/** Read one cookie by name from document.cookie. HttpOnly cookies are invisible here by design. */
/** The CSRF token, from the prefixed cookie when cookies are Secure, otherwise the plain one. */
export function readCsrfToken(): string | null {
  for (const name of CSRF_COOKIE_NAMES) {
    const value = readCookie(name);
    if (value !== null) return value;
  }
  return null;
}

export function readCookie(name: string): string | null {
  for (const part of document.cookie.split(";")) {
    const [key, ...rest] = part.trim().split("=");
    if (key === name) {
      return decodeURIComponent(rest.join("="));
    }
  }
  return null;
}

interface ErrorBody {
  detail?: unknown;
  request_id?: string;
  errors?: { location?: unknown[]; message?: string }[];
}

/** Turn any thrown value from Axios into an ApiError with a message that is safe to show. */
export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) {
    return error;
  }
  if (!(error instanceof AxiosError) || !error.response) {
    return new ApiError("The server could not be reached. Check your connection and try again.", 0);
  }
  const { status, data, headers } = error.response;
  const body = (typeof data === "object" && data !== null ? data : {}) as ErrorBody;
  const fieldErrors = (body.errors ?? []).map((item) => ({
    location: (item.location ?? []).filter((part) => part !== "body").join("."),
    message: item.message ?? "Invalid value",
  }));
  const retryAfter = Number(headers?.["retry-after"]);
  const detail = typeof body.detail === "string" ? body.detail : defaultMessage(status);
  return new ApiError(
    detail,
    status,
    body.request_id ?? null,
    fieldErrors,
    Number.isFinite(retryAfter) ? retryAfter : null,
  );
}

function defaultMessage(status: number): string {
  if (status === 401) return "Please sign in.";
  if (status === 403) return "Your role does not allow this action.";
  if (status === 404) return "Not found.";
  if (status === 429) return "Too many requests. Try again shortly.";
  if (status >= 500) return "The server had a problem. Try again later.";
  return "The request could not be completed.";
}

let unauthorizedHandler: (() => void) | null = null;

/** Register what happens when the session ends during use. Only the auth provider calls this. */
export function onUnauthorized(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

/** Build a client. Base URL is empty by default: the API is reached on this page's own origin. */
export function createApiClient(baseURL: string = import.meta.env.VITE_API_BASE_URL ?? ""): AxiosInstance {
  const client = axios.create({ baseURL, withCredentials: true, timeout: REQUEST_TIMEOUT_MS });
  client.interceptors.request.use((config) => {
    if (UNSAFE_METHODS.has((config.method ?? "get").toLowerCase())) {
      const token = readCsrfToken();
      if (token) {
        config.headers.set(CSRF_HEADER, token);
      }
    }
    return config;
  });
  client.interceptors.response.use(
    (response) => response,
    (error: unknown) => {
      const apiError = toApiError(error);
      const url = error instanceof AxiosError ? (error.config?.url ?? "") : "";
      // A failed sign-in is not a session ending, so it is left to the sign-in form to report.
      if (apiError.status === 401 && !url.startsWith(SIGN_IN_PATH)) {
        unauthorizedHandler?.();
      }
      return Promise.reject(apiError);
    },
  );
  return client;
}

export const api = createApiClient();
