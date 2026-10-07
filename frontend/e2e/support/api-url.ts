/**
 * Normalize the configured API base to the origin/root that specs append
 * `/api/v1/...` to. Production may provide either:
 *   - https://host
 *   - https://host/api
 *   - https://host/api/v1
 */
export function apiOrigin(rawBase: string): string {
  return rawBase.trim().replace(/\/+$/, '').replace(/\/api(?:\/v\d+)?$/i, '');
}
