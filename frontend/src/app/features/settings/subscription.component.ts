import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';

export interface SubscriptionStatus {
  status: string;
  trial_ends_at: string | null;
  plan_tier: string;
}

@Component({
  selector: 'app-subscription',
  standalone: true,
  imports: [MatIconModule],
  template: `
    <div class="bg-surface-raised border border-border-default rounded-lg overflow-hidden">
      <div class="flex items-center justify-between px-6 py-4 border-b border-border-default">
        <div class="flex items-center gap-2">
          <mat-icon class="text-indigo-400">card_membership</mat-icon>
          <h3 class="text-base font-semibold text-text-primary">Plan &amp; Billing</h3>
        </div>
      </div>

      @if (loading()) {
        <div class="px-6 py-5 animate-pulse" aria-busy="true" aria-label="Loading subscription">
          <div class="h-4 bg-surface rounded w-40 mb-3"></div>
          <div class="h-3 bg-surface rounded w-56"></div>
        </div>
      } @else if (loadError()) {
        <div class="px-6 py-4 text-sm text-confidence-low" role="alert">
          <mat-icon class="text-base align-middle mr-1">error_outline</mat-icon>
          Could not load your subscription.
          <button type="button" class="underline hover:no-underline ml-1" (click)="load()">Retry</button>
        </div>
      } @else {
        <div class="px-6 py-5">
          <div class="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <div class="flex items-center gap-2">
                <span class="text-sm font-medium text-text-primary capitalize">{{ planLabel() }}</span>
                <span
                  class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium"
                  [class]="statusClass()"
                >
                  {{ statusLabel() }}
                </span>
              </div>
              @if (trialDaysLeft() !== null) {
                <p class="text-xs text-text-muted mt-1">
                  @if (trialDaysLeft()! > 0) {
                    Trial ends in {{ trialDaysLeft() }} day{{ trialDaysLeft() === 1 ? '' : 's' }}.
                  } @else {
                    Trial has ended.
                  }
                </p>
              }
            </div>

            <button
              type="button"
              (click)="openPortal()"
              [disabled]="opening()"
              class="inline-flex items-center gap-1.5 bg-accent hover:bg-accent-hover text-accent-on font-medium px-3 py-1.5 rounded text-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              aria-label="Manage plan and billing in the Stripe customer portal"
            >
              <mat-icon class="text-base leading-none" style="font-size:1rem;width:1rem;height:1rem;">open_in_new</mat-icon>
              @if (opening()) { Opening… } @else { Manage plan &amp; billing }
            </button>
          </div>

          <p class="text-xs text-text-disabled mt-3">
            Change plan, update payment method, or view invoices in the secure Stripe portal.
          </p>

          @if (actionError()) {
            <div role="alert" class="mt-3 text-sm text-confidence-low bg-confidence-low/10 border border-confidence-low/30 rounded px-3 py-2">
              {{ actionError() }}
            </div>
          }
        </div>
      }
    </div>
  `,
  styles: [':host { display: block; }'],
})
export class SubscriptionComponent implements OnInit {
  private http = inject(HttpClient);

  loading = signal(true);
  loadError = signal(false);
  status = signal<SubscriptionStatus | null>(null);

  opening = signal(false);
  actionError = signal<string | null>(null);

  planLabel = computed(() => {
    const tier = this.status()?.plan_tier ?? 'trial';
    return `${tier} plan`;
  });

  statusLabel = computed(() => {
    const s = this.status()?.status ?? 'unknown';
    const labels: Record<string, string> = {
      active: 'Active',
      trialing: 'Trialing',
      past_due: 'Past due',
      canceled: 'Canceled',
      unpaid: 'Unpaid',
      unknown: 'Unknown',
    };
    return labels[s] ?? s;
  });

  statusClass = computed(() => {
    switch (this.status()?.status) {
      case 'active': return 'bg-accent/15 text-accent-light';
      case 'trialing': return 'bg-indigo-950 text-indigo-400';
      case 'past_due':
      case 'unpaid': return 'bg-confidence-low/10 text-confidence-low';
      case 'canceled': return 'bg-surface text-text-disabled';
      default: return 'bg-surface text-text-muted';
    }
  });

  trialDaysLeft = computed<number | null>(() => {
    const endsAt = this.status()?.trial_ends_at;
    if (!endsAt) return null;
    const diffMs = new Date(endsAt).getTime() - Date.now();
    return Math.max(0, Math.ceil(diffMs / 86_400_000));
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.loadError.set(false);
    this.http.get<SubscriptionStatus>('/api/v1/billing/subscription-status').subscribe({
      next: (data) => {
        this.status.set(data);
        this.loading.set(false);
      },
      error: () => {
        this.loadError.set(true);
        this.loading.set(false);
      },
    });
  }

  openPortal(): void {
    if (this.opening()) return;
    this.opening.set(true);
    this.actionError.set(null);
    // return_url must be same-origin as the configured frontend (server rejects
    // cross-origin to block open-redirect); send this app's settings page.
    const returnUrl = `${window.location.origin}/app/settings`;
    this.http.post<{ url: string }>('/api/v1/billing/portal', { return_url: returnUrl }).subscribe({
      next: (res) => {
        this.opening.set(false);
        this.navigateExternal(res.url);
      },
      error: (err: { status?: number; error?: { detail?: unknown } }) => {
        this.opening.set(false);
        if (err?.status === 409) {
          this.actionError.set('Billing is not set up yet for this workspace.');
          return;
        }
        const detail = err?.error?.detail;
        this.actionError.set(
          typeof detail === 'string' ? detail : 'Could not open the billing portal. Please try again.',
        );
      },
    });
  }

  /** Isolated for testability — full-page redirect to the Stripe portal URL. */
  protected navigateExternal(url: string): void {
    window.location.href = url;
  }
}
