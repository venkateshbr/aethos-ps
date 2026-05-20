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
    <div class="min-h-screen bg-slate-900 text-slate-50 flex flex-col">

      <!-- Topbar -->
      <header class="border-b border-slate-800 bg-slate-950 px-6 py-4">
        <div class="max-w-3xl mx-auto flex items-center justify-between">
          <div class="flex items-center gap-3">
            <!-- Aethos wordmark -->
            <span class="text-lg font-semibold tracking-tight text-white">Aethos</span>
            <span class="text-slate-600">|</span>
            @if (invoice()) {
              <span class="text-sm text-slate-400">{{ invoice()!.tenant_name }}</span>
            }
          </div>
          <span class="text-xs text-slate-500">Secure invoice</span>
        </div>
      </header>

      <!-- Main content -->
      <main class="flex-1 flex items-start justify-center py-12 px-4" role="main">
        <div class="w-full max-w-3xl">

          <!-- Loading skeleton -->
          @if (loading()) {
            <div class="bg-slate-800 border border-slate-700 rounded-xl p-8 animate-pulse" aria-busy="true" aria-label="Loading invoice">
              <div class="h-6 bg-slate-700 rounded w-1/3 mb-4"></div>
              <div class="h-4 bg-slate-700 rounded w-1/5 mb-8"></div>
              @for (i of [1, 2, 3]; track i) {
                <div class="h-4 bg-slate-700 rounded mb-3"></div>
              }
              <div class="h-12 bg-slate-700 rounded mt-8"></div>
            </div>
          }

          <!-- Not found / error state -->
          @if (!loading() && error()) {
            <div class="bg-slate-800 border border-red-900 rounded-xl p-8 text-center" role="alert">
              <div class="text-5xl mb-4" aria-hidden="true">&#x1F4C4;</div>
              <h1 class="text-xl font-semibold text-red-400 mb-2">{{ error() }}</h1>
              <p class="text-slate-400 text-sm">
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
            <article class="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden shadow-2xl">

              <!-- Invoice header -->
              <div class="px-8 pt-8 pb-6 border-b border-slate-700">
                <div class="flex items-start justify-between gap-4 mb-6">
                  <div>
                    <h1 class="text-2xl font-bold text-slate-50">{{ invoice()!.invoice_number }}</h1>
                    <p class="text-slate-400 text-sm mt-1">Invoice</p>
                  </div>
                  <!-- Status badge -->
                  @if (invoice()!.status === 'paid') {
                    <span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-semibold
                                 bg-emerald-900 text-emerald-400 border border-emerald-800">
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
                    <dt class="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1">Bill To</dt>
                    <dd class="text-slate-50 text-sm font-medium">{{ invoice()!.client_name }}</dd>
                  </div>
                  <div>
                    <dt class="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1">Issue Date</dt>
                    <dd class="text-slate-300 text-sm tabular-nums">{{ invoice()!.issue_date }}</dd>
                  </div>
                  <div>
                    <dt class="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1">Due Date</dt>
                    <dd class="text-slate-300 text-sm tabular-nums">{{ invoice()!.due_date }}</dd>
                  </div>
                </div>
              </div>

              <!-- Line items -->
              <div class="px-8 py-6 border-b border-slate-700">
                <table class="w-full text-sm" aria-label="Invoice line items">
                  <thead>
                    <tr>
                      <th scope="col" class="text-left text-xs font-medium text-slate-500 uppercase tracking-wide pb-3">
                        Description
                      </th>
                      <th scope="col" class="text-right text-xs font-medium text-slate-500 uppercase tracking-wide pb-3 w-16">
                        Qty
                      </th>
                      <th scope="col" class="text-right text-xs font-medium text-slate-500 uppercase tracking-wide pb-3 w-28">
                        Rate
                      </th>
                      <th scope="col" class="text-right text-xs font-medium text-slate-500 uppercase tracking-wide pb-3 w-28">
                        Amount
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (line of invoice()!.lines; track $index) {
                      <tr class="border-t border-slate-700">
                        <td class="py-3 text-slate-50 align-top">{{ line.description }}</td>
                        <td class="py-3 text-slate-400 text-right tabular-nums align-top">{{ line.quantity }}</td>
                        <td class="py-3 text-slate-400 text-right tabular-nums align-top">
                          {{ line.unit_price | money: line.currency }}
                        </td>
                        <td class="py-3 text-slate-50 text-right font-medium tabular-nums align-top">
                          {{ line.amount | money: line.currency }}
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>

              <!-- Totals -->
              <div class="px-8 py-6 border-b border-slate-700 bg-slate-900">
                <div class="flex flex-col gap-2 items-end">
                  <div class="flex items-center justify-between w-full sm:w-72 gap-4">
                    <span class="text-slate-400 text-sm">Subtotal</span>
                    <span class="text-slate-50 text-sm font-mono tabular-nums">
                      {{ invoice()!.subtotal | money: invoice()!.currency }}
                    </span>
                  </div>
                  <div class="flex items-center justify-between w-full sm:w-72 gap-4">
                    <span class="text-slate-400 text-sm">Tax</span>
                    <span class="text-slate-50 text-sm font-mono tabular-nums">
                      {{ invoice()!.tax_amount | money: invoice()!.currency }}
                    </span>
                  </div>
                  <div class="flex items-center justify-between w-full sm:w-72 gap-4 pt-2 border-t border-slate-700">
                    <span class="text-slate-50 font-semibold">Total</span>
                    <span class="text-slate-50 font-bold text-lg font-mono tabular-nums">
                      {{ invoice()!.total_amount | money: invoice()!.currency }}
                    </span>
                  </div>
                </div>
              </div>

              <!-- CTA / Paid confirmation -->
              <div class="px-8 py-6">
                @if (invoice()!.status === 'paid') {
                  <div class="flex items-center gap-3 rounded-lg bg-emerald-900 border border-emerald-800 px-5 py-4"
                       role="status" aria-live="polite">
                    <span class="text-emerald-400 text-xl" aria-hidden="true">&#10003;</span>
                    <div>
                      <p class="text-emerald-400 font-semibold text-sm">Payment received</p>
                      <p class="text-emerald-300 text-xs mt-0.5">Thank you — this invoice has been paid in full.</p>
                    </div>
                  </div>
                } @else if (invoice()!.stripe_payment_link_url) {
                  <button
                    (click)="pay()"
                    class="w-full sm:w-auto px-8 py-3 text-base font-semibold rounded-lg
                           bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700
                           text-white transition-colors shadow-lg shadow-emerald-900/30
                           focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
                    aria-label="Pay invoice {{ invoice()!.total_amount | money: invoice()!.currency }}"
                  >
                    Pay Now — {{ invoice()!.total_amount | money: invoice()!.currency }}
                  </button>
                  <p class="text-xs text-slate-500 mt-3">
                    You will be redirected to Stripe's secure payment page.
                  </p>
                } @else {
                  <p class="text-slate-400 text-sm">
                    To pay this invoice, please contact your account manager.
                  </p>
                }
              </div>

            </article>

            <!-- Footer -->
            <p class="text-center text-xs text-slate-600 mt-6">
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
      case 'overdue':  return 'bg-red-950 text-red-400 border border-red-800';
      case 'void':     return 'bg-slate-800 text-slate-500 border border-slate-700';
      default:         return 'bg-slate-800 text-slate-400 border border-slate-700';
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
