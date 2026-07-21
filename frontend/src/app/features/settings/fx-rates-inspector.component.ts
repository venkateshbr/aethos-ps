import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';

interface FxRateProvenance {
  from_currency: string;
  to_currency: string;
  rate: string;
  refreshed_at: string;
  stale: boolean;
  requested_rate_date: string;
  rate_date: string;
  fx_rate_id: string | null;
  source: string;
  staleness_days: number;
}

@Component({
  selector: 'app-fx-rates-inspector',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="rounded-lg border border-border-default bg-surface-raised overflow-hidden">
      <div class="border-b border-border-default px-5 py-4">
        <h3 class="text-base font-semibold text-text-primary">Historical FX provenance</h3>
        <p class="mt-1 text-xs text-text-muted">
          Read-only lookup of the immutable rate available on a document date.
        </p>
      </div>

      <div class="grid gap-3 px-5 py-4 md:grid-cols-[1fr_1fr_1.2fr_auto] md:items-end">
        <div>
          <label for="fx-from-currency" class="mb-1.5 block text-xs uppercase tracking-wide text-text-muted">
            From
          </label>
          <select
            id="fx-from-currency"
            [ngModel]="fromCurrency()"
            (ngModelChange)="fromCurrency.set($event)"
            class="w-full rounded border border-border-default bg-surface-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
          >
            @for (currency of launchCurrencies; track currency) {
              <option [value]="currency">{{ currency }}</option>
            }
          </select>
        </div>

        <div>
          <label for="fx-to-currency" class="mb-1.5 block text-xs uppercase tracking-wide text-text-muted">
            To
          </label>
          <select
            id="fx-to-currency"
            [ngModel]="toCurrency()"
            (ngModelChange)="toCurrency.set($event)"
            class="w-full rounded border border-border-default bg-surface-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
          >
            @for (currency of launchCurrencies; track currency) {
              <option [value]="currency">{{ currency }}</option>
            }
          </select>
        </div>

        <div>
          <label for="fx-rate-date" class="mb-1.5 block text-xs uppercase tracking-wide text-text-muted">
            Document date
          </label>
          <input
            id="fx-rate-date"
            type="date"
            [max]="today"
            [ngModel]="rateDate()"
            (ngModelChange)="rateDate.set($event)"
            class="w-full rounded border border-border-default bg-surface-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
          />
        </div>

        <button
          type="button"
          class="rounded bg-accent px-4 py-2 text-sm font-medium text-accent-on transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          [disabled]="loading() || !rateDate()"
          (click)="lookup()"
        >{{ loading() ? 'Looking up…' : 'Lookup' }}</button>
      </div>

      @if (error()) {
        <div class="border-t border-border-default px-5 py-3 text-sm text-confidence-low" role="alert">
          {{ error() }}
        </div>
      }

      @if (result(); as rate) {
        <div
          class="border-t border-border-default bg-surface-base/40 px-5 py-4"
          aria-label="Matched FX rate provenance"
        >
          <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
            <p class="font-mono text-sm font-semibold text-text-primary">
              {{ rate.from_currency }} → {{ rate.to_currency }} · {{ rate.rate }}
            </p>
            <span
              class="rounded px-2 py-0.5 text-xs font-medium"
              [class]="rate.staleness_days > 3
                ? 'bg-confidence-med/15 text-confidence-med'
                : 'bg-accent/15 text-accent-light'"
            >{{ rate.staleness_days > 3 ? 'Stale fallback' : 'Matched' }}</span>
          </div>
          <dl class="grid gap-3 text-xs sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <dt class="uppercase tracking-wide text-text-muted">Requested date</dt>
              <dd class="mt-1 font-mono text-text-primary">{{ rate.requested_rate_date }}</dd>
            </div>
            <div>
              <dt class="uppercase tracking-wide text-text-muted">Matched rate date</dt>
              <dd class="mt-1 font-mono text-text-primary">{{ rate.rate_date }}</dd>
            </div>
            <div>
              <dt class="uppercase tracking-wide text-text-muted">Staleness</dt>
              <dd class="mt-1 text-text-primary">{{ stalenessLabel(rate.staleness_days) }}</dd>
            </div>
            <div>
              <dt class="uppercase tracking-wide text-text-muted">Immutable FX rate ID</dt>
              <dd class="mt-1 break-all font-mono text-text-primary">
                {{ rate.fx_rate_id || 'Identity rate — no stored row' }}
              </dd>
            </div>
            <div>
              <dt class="uppercase tracking-wide text-text-muted">Source</dt>
              <dd class="mt-1 break-all font-mono text-text-primary">{{ rate.source }}</dd>
            </div>
            <div>
              <dt class="uppercase tracking-wide text-text-muted">Recorded at</dt>
              <dd class="mt-1 break-all font-mono text-text-primary">{{ rate.refreshed_at }}</dd>
            </div>
          </dl>
        </div>
      }
    </div>
  `,
  styles: [':host { display: block; }'],
})
export class FxRatesInspectorComponent {
  private http = inject(HttpClient);

  readonly launchCurrencies = ['USD', 'GBP', 'SGD', 'INR', 'AUD'];
  readonly today = new Date().toISOString().slice(0, 10);

  fromCurrency = signal('USD');
  toCurrency = signal('SGD');
  rateDate = signal(this.today);
  loading = signal(false);
  result = signal<FxRateProvenance | null>(null);
  error = signal<string | null>(null);

  lookup(): void {
    const requestedDate = this.rateDate().trim();
    if (!requestedDate) return;

    this.loading.set(true);
    this.result.set(null);
    this.error.set(null);
    const from = this.fromCurrency();
    const to = this.toCurrency();
    this.http.get<FxRateProvenance>(
      `/api/v1/fx-rates/${encodeURIComponent(from)}/${encodeURIComponent(to)}?rate_date=${encodeURIComponent(requestedDate)}`,
    ).subscribe({
      next: (rate) => {
        this.result.set(rate);
        this.loading.set(false);
      },
      error: (err: unknown) => {
        this.error.set(this.lookupErrorMessage(err));
        this.loading.set(false);
      },
    });
  }

  stalenessLabel(days: number): string {
    return `${days} ${days === 1 ? 'day' : 'days'}`;
  }

  private lookupErrorMessage(err: unknown): string {
    if (err instanceof HttpErrorResponse) {
      const detail = err.error?.detail;
      if (typeof detail === 'string' && detail.trim()) return detail;
      if (err.status === 404) return 'No FX rate was found on or before that date.';
      if (err.status === 422) return 'Choose launch currencies and a valid historical date.';
    }
    return 'FX rate provenance is not available right now. Try again.';
  }
}
