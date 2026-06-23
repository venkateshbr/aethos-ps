import { Component, inject, signal, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { HttpClient } from '@angular/common/http';

import { MoneyPipe } from '../../shared/pipes/money.pipe';

export interface PublicInvoiceLine {
  description: string;
  quantity: string;
  unit_price: string;
  amount: string;
  currency: string;
  service_catalogue_id?: string | null;
}

export interface PublicInvoice {
  id: string;
  invoice_number: string;
  status: string;
  currency: string;
  client_name: string;
  issue_date: string;
  due_date: string;
  subtotal: string;
  tax_amount: string;
  total_amount: string;
  stripe_payment_link_url?: string | null;
  tenant_name?: string;
  lines: PublicInvoiceLine[];
}

@Component({
  selector: 'app-public-invoice',
  standalone: true,
  imports: [MoneyPipe],
  template: `
    <!-- Full-page branded layout — no app shell, no sidebar -->
    <div class="min-h-screen bg-surface-base text-text-primary flex flex-col">

      <!-- Topbar -->
      <header class="border-b border-border-subtle bg-slate-950 px-6 py-4">
        <div class="max-w-3xl mx-auto flex items-center justify-between">
          <div class="flex items-center gap-3">
            <!-- Aethos wordmark -->
            <span class="text-lg font-semibold tracking-tight text-text-primary">Aethos</span>
            <span class="text-text-disabled">|</span>
            @if (invoice()) {
              <span class="text-sm text-text-muted">{{ invoice()!.tenant_name }}</span>
            }
          </div>
          <span class="text-xs text-text-disabled">Secure invoice</span>
        </div>
      </header>

      <!-- Main content -->
      <main class="flex-1 flex items-start justify-center py-12 px-4" role="main">
        <div class="w-full max-w-3xl">

          <!-- Loading skeleton -->
          @if (loading()) {
            <div class="bg-surface-raised border border-border-default rounded-xl p-8 animate-pulse" aria-busy="true" aria-label="Loading invoice">
              <div class="h-6 bg-surface rounded w-1/3 mb-4"></div>
              <div class="h-4 bg-surface rounded w-1/5 mb-8"></div>
              @for (i of [1, 2, 3]; track i) {
                <div class="h-4 bg-surface rounded mb-3"></div>
              }
              <div class="h-12 bg-surface rounded mt-8"></div>
            </div>
          }

          <!-- Not found / error state -->
          @if (!loading() && error()) {
            <div class="bg-surface-raised border border-confidence-low/30 rounded-xl p-8 text-center" role="alert">
              <div class="text-5xl mb-4" aria-hidden="true">&#x1F4C4;</div>
              <h1 class="text-xl font-semibold text-confidence-low mb-2">{{ error() }}</h1>
              <p class="text-text-muted text-sm">
                @if (error() === 'Invoice not found') {
                  This invoice link may be expired or incorrect. Please contact the sender.
                } @else {
                  Please try refreshing the page or contact support.
                }
              </p>
            </div>
          }

          <!-- Invoice card -->
          @if (!loading() && !error() && invoice()) {
            <article class="bg-surface-raised border border-border-default rounded-xl overflow-hidden shadow-2xl">

              <!-- Invoice header -->
              <div class="px-8 pt-8 pb-6 border-b border-border-default">
                <div class="flex items-start justify-between gap-4 mb-6">
                  <div>
                    <h1 class="text-2xl font-bold text-text-primary">{{ invoice()!.invoice_number }}</h1>
                    <p class="text-text-muted text-sm mt-1">Invoice</p>
                  </div>
                  <!-- Status badge -->
                  @if (invoice()!.status === 'paid') {
                    <span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-semibold
                                 bg-accent/15 text-accent-light border border-emerald-800">
                      <span class="w-2 h-2 rounded-full bg-emerald-400" aria-hidden="true"></span>
                      Paid
                    </span>
                  } @else {
                    <span
                      class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-semibold"
                      [class]="statusBadgeClass(invoice()!.status)"
                    >
                      <span class="w-2 h-2 rounded-full" [class]="statusDotClass(invoice()!.status)" aria-hidden="true"></span>
                      {{ statusLabel(invoice()!.status) }}
                    </span>
                  }
                </div>

                <!-- Bill-to and dates -->
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-6">
                  <div>
                    <dt class="text-xs font-medium text-text-disabled uppercase tracking-wide mb-1">Bill To</dt>
                    <dd class="text-text-primary text-sm font-medium">{{ invoice()!.client_name }}</dd>
                  </div>
                  <div>
                    <dt class="text-xs font-medium text-text-disabled uppercase tracking-wide mb-1">Issue Date</dt>
                    <dd class="text-text-secondary text-sm tabular-nums">{{ invoice()!.issue_date }}</dd>
                  </div>
                  <div>
                    <dt class="text-xs font-medium text-text-disabled uppercase tracking-wide mb-1">Due Date</dt>
                    <dd class="text-text-secondary text-sm tabular-nums">{{ invoice()!.due_date }}</dd>
                  </div>
                </div>
              </div>

              <!-- Line items -->
              <div class="px-8 py-6 border-b border-border-default">
                <table class="w-full text-sm" aria-label="Invoice line items">
                  <thead>
                    <tr>
                      <th scope="col" class="text-left text-xs font-medium text-text-disabled uppercase tracking-wide pb-3">
                        Description
                      </th>
                      <th scope="col" class="text-right text-xs font-medium text-text-disabled uppercase tracking-wide pb-3 w-16">
                        Qty
                      </th>
                      <th scope="col" class="text-right text-xs font-medium text-text-disabled uppercase tracking-wide pb-3 w-28">
                        Rate
                      </th>
                      <th scope="col" class="text-right text-xs font-medium text-text-disabled uppercase tracking-wide pb-3 w-28">
                        Amount
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (line of invoice()!.lines; track $index) {
                      <tr class="border-t border-border-default">
                        <td class="py-3 text-text-primary align-top">{{ line.description }}</td>
                        <td class="py-3 text-text-muted text-right tabular-nums align-top">{{ line.quantity }}</td>
                        <td class="py-3 text-text-muted text-right tabular-nums align-top">
                          {{ line.unit_price | money: line.currency }}
                        </td>
                        <td class="py-3 text-text-primary text-right font-medium tabular-nums align-top">
                          {{ line.amount | money: line.currency }}
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>

              <!-- Totals -->
              <div class="px-8 py-6 border-b border-border-default bg-surface-base">
                <div class="flex flex-col gap-2 items-end">
                  <div class="flex items-center justify-between w-full sm:w-72 gap-4">
                    <span class="text-text-muted text-sm">Subtotal</span>
                    <span class="text-text-primary text-sm font-mono tabular-nums">
                      {{ invoice()!.subtotal | money: invoice()!.currency }}
                    </span>
                  </div>
                  <div class="flex items-center justify-between w-full sm:w-72 gap-4">
                    <span class="text-text-muted text-sm">Tax</span>
                    <span class="text-text-primary text-sm font-mono tabular-nums">
                      {{ invoice()!.tax_amount | money: invoice()!.currency }}
                    </span>
                  </div>
                  <div class="flex items-center justify-between w-full sm:w-72 gap-4 pt-2 border-t border-border-default">
                    <span class="text-text-primary font-semibold">Total</span>
                    <span class="text-text-primary font-bold text-lg font-mono tabular-nums">
                      {{ invoice()!.total_amount | money: invoice()!.currency }}
                    </span>
                  </div>
                </div>
              </div>

              <!-- CTA / Paid confirmation -->
              <div class="px-8 py-6">
                @if (invoice()!.status === 'paid') {
                  <div class="flex items-center gap-3 rounded-lg bg-accent/15 border border-emerald-800 px-5 py-4"
                       role="status" aria-live="polite">
                    <span class="text-accent-light text-xl" aria-hidden="true">&#10003;</span>
                    <div>
                      <p class="text-accent-light font-semibold text-sm">Payment received</p>
                      <p class="text-accent-light text-xs mt-0.5">Thank you — this invoice has been paid in full.</p>
                    </div>
                  </div>
                } @else if (invoice()!.stripe_payment_link_url) {
                  <button
                    (click)="pay()"
                    class="w-full sm:w-auto px-8 py-3 text-base font-semibold rounded-lg
                           bg-accent hover:bg-accent active:bg-emerald-700
                           text-text-primary transition-colors shadow-lg shadow-emerald-900/30
                           focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
                    [attr.aria-label]="'Pay invoice ' + (invoice()!.total_amount | money: invoice()!.currency)"
                  >
                    Pay Now — {{ invoice()!.total_amount | money: invoice()!.currency }}
                  </button>
                  <p class="text-xs text-text-disabled mt-3">
                    You will be redirected to Stripe's secure payment page.
                  </p>
                } @else {
                  <p class="text-text-muted text-sm">
                    To pay this invoice, please contact your account manager.
                  </p>
                }
              </div>

            </article>

            <!-- Footer -->
            <p class="text-center text-xs text-text-disabled mt-6">
              Powered by Aethos for Professional Services
            </p>
          }

        </div>
      </main>
    </div>
  `,
  styles: [':host { display: block; }'],
})
export class PublicInvoiceComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private http   = inject(HttpClient);

  invoice = signal<PublicInvoice | null>(null);
  loading = signal(true);
  error   = signal<string | null>(null);

  ngOnInit(): void {
    const token = this.route.snapshot.paramMap.get('token');
    if (!token) {
      this.error.set('Invoice not found');
      this.loading.set(false);
      return;
    }

    // skip-auth tells the auth interceptor to omit the Authorization header.
    this.http
      .get<PublicInvoice>(`/api/v1/public/invoices/${token}`, {
        headers: { 'skip-auth': 'true' },
      })
      .subscribe({
        next: (inv) => {
          this.invoice.set(inv);
          this.loading.set(false);
        },
        error: (e) => {
          this.error.set(e.status === 404 ? 'Invoice not found' : 'Error loading invoice');
          this.loading.set(false);
        },
      });
  }

  pay(): void {
    const url = this.invoice()?.stripe_payment_link_url;
    if (url) window.open(url, '_blank');
  }

  statusLabel(status: string): string {
    const labels: Record<string, string> = {
      draft:    'Draft',
      approved: 'Approved',
      sent:     'Sent',
      overdue:  'Overdue',
      void:     'Void',
    };
    return labels[status] ?? status;
  }

  statusBadgeClass(status: string): string {
    switch (status) {
      case 'approved': return 'bg-indigo-950 text-indigo-400 border border-indigo-800';
      case 'sent':     return 'bg-indigo-950 text-indigo-300 border border-indigo-800';
      case 'overdue':  return 'bg-confidence-low/10 text-confidence-low border border-confidence-low/40';
      case 'void':     return 'bg-surface-raised text-text-disabled border border-border-default';
      default:         return 'bg-surface-raised text-text-muted border border-border-default';
    }
  }

  statusDotClass(status: string): string {
    switch (status) {
      case 'approved': return 'bg-indigo-400';
      case 'sent':     return 'bg-indigo-300';
      case 'overdue':  return 'bg-red-400';
      default:         return 'bg-slate-400';
    }
  }
}
