import { Component, inject, signal, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';

export interface StripeConnectStatus {
  status: 'active' | 'pending' | 'not_connected';
  charges_enabled: boolean;
  payouts_enabled: boolean;
  account_id?: string;
}

@Component({
  selector: 'app-stripe-connect',
  standalone: true,
  imports: [MatIconModule],
  template: `
    <div class="bg-surface-raised border border-border-default rounded-lg p-6">
      <div class="flex items-center gap-3 mb-4">
        <mat-icon class="text-indigo-400">payment</mat-icon>
        <h3 class="text-base font-semibold text-text-primary">Stripe Connect</h3>
      </div>

      @if (loading()) {
        <div class="space-y-2" aria-busy="true" aria-label="Loading Stripe Connect status">
          <div class="h-4 w-48 bg-surface rounded animate-pulse"></div>
          <div class="h-4 w-32 bg-surface rounded animate-pulse"></div>
        </div>
      } @else if (status()?.status === 'active' && status()?.charges_enabled) {
        <!-- Connected and active -->
        <div class="flex items-center gap-2 mb-4" role="status">
          <span class="w-2 h-2 rounded-full bg-emerald-400" aria-hidden="true"></span>
          <span class="text-sm text-accent-light font-medium">Connected</span>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div class="flex items-center gap-1.5">
            <mat-icon
              class="text-sm"
              style="font-size:16px;width:16px;height:16px;"
              [class]="status()!.charges_enabled ? 'text-accent-light' : 'text-confidence-low'"
            >
              {{ status()!.charges_enabled ? 'check_circle' : 'cancel' }}
            </mat-icon>
            <span class="text-xs text-text-secondary">Charges enabled</span>
          </div>
          <div class="flex items-center gap-1.5">
            <mat-icon
              class="text-sm"
              style="font-size:16px;width:16px;height:16px;"
              [class]="status()!.payouts_enabled ? 'text-accent-light' : 'text-confidence-med'"
            >
              {{ status()!.payouts_enabled ? 'check_circle' : 'schedule' }}
            </mat-icon>
            <span class="text-xs text-text-secondary">Payouts enabled</span>
          </div>
        </div>
      } @else if (status()?.status === 'pending') {
        <!-- Connected but incomplete -->
        <p class="text-sm text-confidence-med mb-4" role="status">
          Stripe needs more information to enable payments.
        </p>
        <button
          (click)="connect()"
          [disabled]="connecting()"
          class="px-4 py-2 text-sm font-medium rounded
                 bg-amber-600 hover:bg-confidence-med active:bg-amber-700
                 text-text-primary transition-colors
                 disabled:opacity-50 disabled:cursor-not-allowed
                 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-400"
          aria-label="Complete Stripe setup"
        >
          @if (connecting()) { Redirecting… } @else { Complete setup }
        </button>
      } @else {
        <!-- Not connected -->
        <p class="text-sm text-text-muted mb-4">
          Connect your Stripe account to accept payments directly from clients via Stripe Payment Links.
        </p>
        <button
          (click)="connect()"
          [disabled]="connecting()"
          class="px-4 py-2 text-sm font-medium rounded
                 bg-accent hover:bg-accent active:bg-emerald-700
                 text-text-primary transition-colors
                 disabled:opacity-50 disabled:cursor-not-allowed
                 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
          aria-label="Connect Stripe account"
        >
          @if (connecting()) { Redirecting… } @else { Connect Stripe }
        </button>
        @if (connectError()) {
          <p class="mt-2 text-xs text-confidence-low" role="alert">{{ connectError() }}</p>
        }
      }
    </div>
  `,
  styles: [':host { display: block; }'],
})
export class StripeConnectComponent implements OnInit {
  private http = inject(HttpClient);

  loading      = signal(true);
  connecting   = signal(false);
  status       = signal<StripeConnectStatus | null>(null);
  connectError = signal<string | null>(null);

  ngOnInit(): void {
    this.http.get<StripeConnectStatus>('/api/v1/stripe/connect/status').subscribe({
      next: (s) => {
        this.status.set(s);
        this.loading.set(false);
      },
      error: () => {
        // If the endpoint doesn't exist yet, treat as not connected.
        this.status.set({ status: 'not_connected', charges_enabled: false, payouts_enabled: false });
        this.loading.set(false);
      },
    });
  }

  connect(): void {
    this.connecting.set(true);
    this.connectError.set(null);
    this.http.get<{ url: string }>('/api/v1/stripe/connect/oauth-url').subscribe({
      next: ({ url }) => {
        window.location.href = url;
        // Note: we leave connecting() = true; the page is navigating away.
      },
      error: () => {
        this.connecting.set(false);
        this.connectError.set('Could not start Stripe Connect. Please try again.');
      },
    });
  }
}
