/**
 * Catches an error while showing a page, so one failure never blanks the whole interface
 * (Phase 5 finding F7).
 *
 * The usual cause is a page's code failing to download: after a redeploy the old file names no
 * longer exist, or the connection dropped. The browser remembers a failed download for the
 * rest of the visit, so only a full reload fetches it again; the prompt offers exactly that.
 * Other errors get a general message. The error's own text is never shown, since it can contain
 * anything; React has already written it to the browser console.
 */
import { AlertTriangle } from "lucide-react";
import { Component, type ReactNode } from "react";

/** Messages browsers give when a dynamically imported module cannot be fetched. */
const DOWNLOAD_FAILURE = /dynamically imported module|Importing a module script failed|ChunkLoadError|Loading chunk/i;

export function isDownloadFailure(error: unknown): boolean {
  const text = error instanceof Error ? `${error.name} ${error.message}` : String(error);
  return DOWNLOAD_FAILURE.test(text);
}

interface Props {
  children: ReactNode;
  /** Reload the document. Replaced in tests. */
  reload?: () => void;
}

interface State {
  error: unknown;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: unknown): State {
    return { error };
  }

  render() {
    const { error } = this.state;
    if (error === null) return this.props.children;
    const reload = this.props.reload ?? (() => window.location.reload());
    const download = isDownloadFailure(error);
    return (
      <section className="card narrow state-error" role="alert" aria-labelledby="page-error-title">
        <AlertTriangle className="state-icon" aria-hidden="true" />
        <h1 id="page-error-title">{download ? "This page could not be loaded" : "Something went wrong on this page"}</h1>
        <p className="muted">
          {download
            ? "Its code could not be downloaded. The application may have been updated, or the connection dropped. Reload to get the current version."
            : "Reload to try again. If it happens again, tell an administrator what you were doing."}
        </p>
        <button type="button" className="button primary" onClick={reload}>
          Reload
        </button>
      </section>
    );
  }
}
