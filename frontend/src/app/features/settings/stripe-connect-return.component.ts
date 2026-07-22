import { Component, OnInit, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';

/**
 * Stripe Connect OAuth return handler (#403).
 *
 * Stripe redirects the browser here (redirect_uri
 * `${frontend}/settings/billing/connect/return?code=..&state=..`). Previously no
 * Angular route matched, so the callback fell through to the `**` wildcard and
 * the linkage was lost. This transient page reads the code/state, completes the
 * exchange via the backend (`GET /api/v1/stripe/connect/return`), then returns
 * the owner to Settings.
 */
@Component({
  selector: 'app-stripe-connect-return',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="min-h-screen flex items-center justify-center bg-surface-base text-text-primary">
      <div class="max-w-md w-full p-8 text-center">
        @if (phase() === 'loading') {
          <h1 class="text-lg font-semibold">Completing Stripe Connect setup…</h1>
          <p class="mt-2 text-sm text-text-muted">This only takes a moment.</p>
        } @else if (phase() === 'success') {
          <h1 class="text-lg font-semibold text-emerald-400">Stripe connected</h1>
          <p class="mt-2 text-sm text-text-muted">Redirecting to Settings…</p>
        } @else {
          <h1 class="text-lg font-semibold text-confidence-low">Couldn't complete Stripe setup</h1>
          <p class="mt-2 text-sm text-text-muted" role="alert">{{ error() }}</p>
          <a routerLink="/app/settings" class="mt-4 inline-block text-accent-light underline">
            Back to Settings
          </a>
        }
      </div>
    </div>
  `,
})
export class StripeConnectReturnComponent implements OnInit {
  private http = inject(HttpClient);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  phase = signal<'loading' | 'success' | 'error'>('loading');
  error = signal<string | null>(null);

  async ngOnInit(): Promise<void> {
    const code = this.route.snapshot.queryParamMap.get('code');
    const state = this.route.snapshot.queryParamMap.get('state');
    if (!code || !state) {
      this.phase.set('error');
      this.error.set('Missing authorization details from Stripe. Please retry connecting from Settings.');
      return;
    }
    try {
      await firstValueFrom(
        this.http.get('/api/v1/stripe/connect/return', { params: { code, state } }),
      );
      this.phase.set('success');
      setTimeout(() => this.router.navigate(['/app/settings']), 1200);
    } catch (err) {
      this.phase.set('error');
      const detail = (err as { error?: { detail?: string } }).error?.detail;
      this.error.set(detail || 'Stripe Connect could not be completed. Please try again from Settings.');
    }
  }
}
