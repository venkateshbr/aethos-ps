import { HttpErrorResponse } from '@angular/common/http';

/**
 * Map an HTTP error into user-facing copy.
 *
 * Issue #113 — the inbox (and most feature views) used a single generic
 * "Something went wrong. Please try again." regardless of cause. That
 * masks two very different failure modes: an expired session (user needs
 * to sign in again) vs. a backend outage (user should retry later). The
 * messages below are intentionally short and consistent across surfaces.
 *
 * Pass `surface` to inject a feature name into the 5xx copy
 * (e.g. surface='Inbox' → "Inbox is not available right now — try again.").
 * Defaults to a generic phrase if omitted.
 */
export function userMessageForError(err: unknown, surface?: string): string {
  if (err instanceof HttpErrorResponse) {
    if (err.status === 401) {
      return 'Your session expired — please sign in again.';
    }
    if (err.status === 403) {
      return 'You do not have access to this view.';
    }
    if (err.status === 404) {
      return surface
        ? `${surface} could not be found.`
        : 'This resource could not be found.';
    }
    if (err.status === 0) {
      // Network unreachable — usually offline or CORS preflight failure.
      return 'Cannot reach the server. Check your connection and try again.';
    }
    if (err.status >= 500) {
      return surface
        ? `${surface} is not available right now — try again.`
        : 'The service is not available right now — try again.';
    }
  }
  // Fall-through for non-HTTP errors or unmapped statuses.
  return 'Something went wrong. Please try again.';
}
