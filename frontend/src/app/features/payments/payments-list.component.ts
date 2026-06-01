import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';
import { firstValueFrom } from 'rxjs';

interface Payment {
  id: string;
  invoice_id: string;
  invoice_number: string | null;
  amount: string;
  currency: string;
  base_amount: string;
  paid_at: string;
  notes: string | null;
}

@Component({
  selector: 'app-payments-list',
  standalone: true,
  imports: [CommonModule, MatIconModule],
  template: `
    <section class="h-full flex flex-col bg-surface-base text-text-primary">

      <header class="px-6 py-5 border-b border-border-default flex items-center justify-between flex-none">
        <div>
          <h1 class="text-xl font-semibold text-text-primary">Payments</h1>
          <p class="text-xs text-text-muted mt-0.5">AR receipts — payments received from clients</p>
        </div>
      </header>

      <!-- Loading -->
      @if (loading()) {
        <div class="flex-1 flex items-center justify-center">
          <div class="w-6 h-6 rounded-full border-2 border-accent border-t-transparent animate-spin"></div>
        </div>
      }

      <!-- Error -->
      @else if (error()) {
        <div class="mx-6 mt-4 rounded-lg border border-confidence-low/30 bg-confidence-low/10 px-4 py-3 text-sm text-confidence-low">
          {{ error() }}
        </div>
      }

      <!-- Empty state -->
      @else if (payments().length === 0) {
        <div class="flex-1 flex flex-col items-center justify-center text-center px-6">
          <mat-icon class="text-text-disabled mb-3" style="font-size:2.5rem;width:2.5rem;height:2.5rem;" aria-hidden="true">account_balance</mat-icon>
          <p class="text-text-secondary font-medium">No payments yet</p>
          <p class="text-text-disabled text-sm mt-1 max-w-md">
            Payments appear here when a client pays an invoice via Stripe Payment Link
            or you manually mark an invoice as paid.
          </p>
        </div>
      }

      <!-- Payments table -->
      @else {
        <div class="flex-1 overflow-auto">
          <table class="w-full text-sm border-collapse">
            <thead>
              <tr class="bg-surface-raised border-b border-border-default">
                <th class="text-left text-xs font-medium text-text-muted uppercase tracking-wide px-5 py-3">Date</th>
                <th class="text-left text-xs font-medium text-text-muted uppercase tracking-wide px-5 py-3">Invoice</th>
                <th class="text-right text-xs font-medium text-text-muted uppercase tracking-wide px-5 py-3">Amount</th>
                <th class="text-left text-xs font-medium text-text-muted uppercase tracking-wide px-5 py-3 hidden md:table-cell">Notes</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border-default">
              @for (p of payments(); track p.id) {
                <tr class="hover:bg-surface-raised transition-colors">
                  <td class="px-5 py-3.5 text-text-muted whitespace-nowrap">
                    {{ formatDate(p.paid_at) }}
                  </td>
                  <td class="px-5 py-3.5">
                    @if (p.invoice_number) {
                      <span class="text-accent-light font-mono text-xs font-medium">{{ p.invoice_number }}</span>
                    } @else {
                      <span class="text-text-disabled text-xs font-mono">{{ p.invoice_id.slice(0, 8) }}</span>
                    }
                  </td>
                  <td class="px-5 py-3.5 text-right font-medium text-text-primary whitespace-nowrap">
                    {{ p.currency }} {{ (+p.amount).toLocaleString(undefined, {minimumFractionDigits: 2}) }}
                  </td>
                  <td class="px-5 py-3.5 text-text-muted hidden md:table-cell">
                    {{ p.notes || '—' }}
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>

        <!-- Footer total -->
        <div class="border-t border-border-default px-5 py-3 flex items-center justify-between text-sm flex-none bg-surface-raised">
          <span class="text-text-muted">{{ payments().length }} payment{{ payments().length !== 1 ? 's' : '' }}</span>
          <span class="font-semibold text-text-primary">
            Total: {{ totalByCurrency() }}
          </span>
        </div>
      }

    </section>
  `,
})
export class PaymentsListComponent implements OnInit {
  private http = inject(HttpClient);

  protected loading = signal(true);
  protected payments = signal<Payment[]>([]);
  protected error = signal<string | null>(null);

  ngOnInit() { this.load(); }

  private async load() {
    try {
      const data = await firstValueFrom(
        this.http.get<{ items: Payment[] }>('/api/v1/payments')
      );
      this.payments.set(data.items ?? []);
    } catch {
      this.error.set('Could not load payments. Please refresh.');
    } finally {
      this.loading.set(false);
    }
  }

  protected formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
  }

  /** Summarise totals by currency e.g. "USD 12,500.00 · GBP 3,200.00" */
  protected totalByCurrency(): string {
    const totals: Record<string, number> = {};
    for (const p of this.payments()) {
      totals[p.currency] = (totals[p.currency] ?? 0) + (+p.amount);
    }
    return Object.entries(totals)
      .map(([cur, amt]) => `${cur} ${amt.toLocaleString(undefined, { minimumFractionDigits: 2 })}`)
      .join(' · ') || '—';
  }
}
