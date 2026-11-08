/**
 * Sign-in. The API sets an HttpOnly session cookie; this page never sees a token.
 */
import { ShieldCheck } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";
import { toApiError } from "../services/api";

interface LocationState {
  from?: string;
}

export function LoginPage() {
  const { status, signIn, notice } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const destination = (location.state as LocationState | null)?.from ?? "/";

  if (status === "signedIn") return <Navigate to={destination} replace />;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signIn(email, password);
      navigate(destination, { replace: true });
    } catch (caught) {
      const failure = toApiError(caught);
      setError(
        failure.status === 429 && failure.retryAfterSeconds
          ? `Too many attempts. Try again in ${failure.retryAfterSeconds} seconds.`
          : failure.message,
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-page">
      <form className="card login-card" onSubmit={(event) => void handleSubmit(event)} noValidate>
        <div className="brand">
          <ShieldCheck aria-hidden="true" />
          <span>FinGuard AI</span>
        </div>
        <h1>Sign in</h1>
        <p className="muted">
          Research and demonstration only. Scores rank simulated PaySim transactions for review and
          are not findings of fraud.
        </p>
        {notice ? (
          <p className="notice" role="status">
            {notice}
          </p>
        ) : null}
        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          autoComplete="username"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />
        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />
        {error ? (
          <p className="error-text" role="alert">
            {error}
          </p>
        ) : null}
        <button type="submit" className="button primary" disabled={busy || !email || !password}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </main>
  );
}
