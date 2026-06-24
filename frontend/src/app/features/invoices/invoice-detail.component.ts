import { Component, inject, signal, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';

import { MoneyPipe } from '../../shared/pipes/money.pipe';
import { DecisionTimelineComponent } from '../../shared/components/decision-timeline.component';
import { userMessageForError } from '../../core/utils/error-message';

interface InvoiceLine {
  id: string;
  description: string;
  quantity: string;
  unit_price: string;
  amount: string;
  tax_amount: string;
  service_catalogue_id?: string | null;
}

interface InvoiceDetail {
  id: string;
  invoice_number: string;
  engagement_id: string;
  client_id: string;
  currency: string;
  subtotal: string;
  tax_total: string;
  total: string;
  status: string;
  issue_date: string | null;
  due_date: string | null;
  paid_at: string | null;
  sent_at: string | null;
  notes: string | null;
  stripe_payment_link_url: string | null;
  public_token: string | null;
  lines: InvoiceLine[];
}

@Component({
  selector: 'app-invoice-detail',
  standalone: true,
  imports: [MatButtonModule, MatIconModule, MatTableModule, MatTooltipModule, MoneyPipe, DecisionTimelineComponent],
  template: `
    <div class="p-6 bg-surface-base min-h-full">
      <button
        mat-button
        class="text-text-muted hover:text-text-primary mb-4 -ml-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
        (click)="goBack()"
        aria-label="Back to invoices"
      >
        <mat-icon>arrow_back</mat-icon>
        Invoices
      </button>

      @if (loading()) {
        <div class="animate-pulse" aria-busy="true" aria-label="Loading invoice">
          <div class="h-8 bg-surface-raised rounded w-1/3 mb-3"></div>
          <div class="h-4 bg-surface-raised rounded w-1/5 mb-6"></div>
          <div class="grid grid-cols-2 gap-4">
            @for (item of [1,2,3,4]; track item) {
              <div class="bg-surface-raised rounded p-4 h-16"></div>
            }
          </div>
        </div>
      }

      @if (error() && !loading()) {
        <div class="rounded-lg border border-confidence-low/30 bg-confidence-low/10 px-4 py-3 text-sm text-confidence-low" role="alert">
          <mat-icon class="text-base align-middle mr-1">error_outline</mat-icon>
          {{ error() }}
        </div>
      }

      @if (!loading() && !error() && invoice()) {
        <!-- Header -->
        <div class="flex items-start justify-between mb-6">
          <div>
            <h1 class="text-2xl font-bold text-text-primary font-mono">{{ invoice()!.invoice_number }}</h1>
            <p class="text-sm text-text-muted mt-1">Invoice detail</p>
          </div>
          <div class="flex items-center gap-3">
            @if (invoice()!.status === 'draft') {
              <button
                (click)="approveInvoice()"
                [disabled]="actionLoading()"
                class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors disabled:opacity-50"
                matTooltip="Approve this invoice"
              >
                <mat-icon class="text-base">check_circle</mat-icon>
                @if (actionLoading()) { Approving… } @else { Approve }
              </button>
            }
            @if (invoice()!.status === 'approved') {
              <button
                (click)="sendInvoice()"
                [disabled]="actionLoading()"
                class="inline-flex items-center gap-2 bg-indigo-700 hover:bg-indigo-600 text-white font-medium px-4 py-2 rounded text-sm transition-colors disabled:opacity-50"
                matTooltip="Send this invoice to the client"
              >
                <mat-icon class="text-base">send</mat-icon>
                @if (actionLoading()) { Sending… } @else { Send }
              </button>
            }
            @if (invoice()!.stripe_payment_link_url) {
              <a
                [href]="invoice()!.stripe_payment_link_url!"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center gap-2 text-sm text-accent-light hover:text-accent-light transition-colors"
              >
                <mat-icon class="text-base">open_in_new</mat-icon>
                Payment link
              </a>
            }
            <span
              class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium"
              [class]="statusClass(invoice()!.status)"
            >
              <span class="w-1.5 h-1.5 rounded-full" [class]="statusDotClass(invoice()!.status)"></span>
              {{ statusLabel(invoice()!.status) }}
            </span>
          </div>
        </div>

        @if (actionMessage()) {
          <div class="mb-4 rounded-lg border border-emerald-800 bg-accent/10 px-4 py-3 text-sm text-accent-light flex items-center gap-2"
               role="status" aria-live="polite">
            <mat-icon class="text-base">check_circle</mat-icon>
            {{ actionMessage() }}
          </div>
        }

        <!-- Key metrics -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div class="bg-surface-raised border border-border-default rounded-lg p-4">
            <dt class="text-xs font-medium text-text-muted uppercase tracking-wide mb-1">Subtotal</dt>
            <dd class="text-text-primary text-sm font-mono font-medium tabular-nums">
              {{ invoice()!.subtotal | money: invoice()!.currency }}
            </dd>
          </div>
          <div class="bg-surface-raised border border-border-default rounded-lg p-4">
            <dt class="text-xs font-medium text-text-muted uppercase tracking-wide mb-1">Tax</dt>
            <dd class="text-text-primary text-sm font-mono font-medium tabular-nums">
              {{ invoice()!.tax_total | money: invoice()!.currency }}
            </dd>
          </div>
          <div class="bg-surface-raised border border-border-default rounded-lg p-4">
            <dt class="text-xs font-medium text-text-muted uppercase tracking-wide mb-1">Total</dt>
            <dd class="text-text-primary text-lg font-mono font-bold tabular-nums">
              {{ invoice()!.total | money: invoice()!.currency }}
            </dd>
          </div>
          <div class="bg-surface-raised border border-border-default rounded-lg p-4">
            <dt class="text-xs font-medium text-text-muted uppercase tracking-wide mb-1">Due Date</dt>
            <dd class="text-text-primary text-sm">{{ invoice()!.due_date ?? '—' }}</dd>
          </div>
        </div>

        @if (invoice()!.notes) {
          <div class="mb-6 bg-surface-raised border border-border-default rounded-lg p-4">
            <p class="text-xs font-medium text-text-muted uppercase tracking-wide mb-1">Notes</p>
            <p class="text-text-secondary text-sm">{{ invoice()!.notes }}</p>
          </div>
        }

        <app-decision-timeline entityType="invoice" [entityId]="invoice()!.id" />

        <!-- Line items -->
        @if (invoice()!.lines.length > 0) {
          <h2 class="text-base font-semibold text-text-primary mb-3">Line items</h2>
          <div class="rounded-lg overflow-hidden border border-border-default">
            <table
              mat-table
              [dataSource]="invoice()!.lines"
              class="w-full bg-surface-base"
              aria-label="Invoice line items"
            >
              <ng-container matColumnDef="description">
                <th mat-header-cell *matHeaderCellDef
                    class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                  Description
                </th>
                <td mat-cell *matCellDef="let line"
                    class="text-text-primary text-sm px-4 py-3 border-b border-border-subtle">
                  {{ line.description }}
                </td>
              </ng-container>

              <ng-container matColumnDef="quantity">
                <th mat-header-cell *matHeaderCellDef
                    class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3 text-right">
                  Qty
                </th>
                <td mat-cell *matCellDef="let line"
                    class="text-text-secondary text-sm font-mono px-4 py-3 border-b border-border-subtle text-right tabular-nums">
                  {{ line.quantity }}
                </td>
              </ng-container>

              <ng-container matColumnDef="unit_price">
                <th mat-header-cell *matHeaderCellDef
                    class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3 text-right">
                  Rate
                </th>
                <td mat-cell *matCellDef="let line"
                    class="text-text-secondary text-sm font-mono px-4 py-3 border-b border-border-subtle text-right tabular-nums">
                  {{ line.unit_price | money: invoice()!.currency }}
                </td>
              </ng-container>

              <ng-container matColumnDef="amount">
                <th mat-header-cell *matHeaderCellDef
                    class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3 text-right">
                  Amount
                </th>
                <td mat-cell *matCellDef="let line"
                    class="text-text-primary text-sm font-mono font-medium px-4 py-3 border-b border-border-subtle text-right tabular-nums">
                  {{ line.amount | money: invoice()!.currency }}
                </td>
              </ng-container>

              <tr mat-header-row *matHeaderRowDef="lineColumns"></tr>
              <tr mat-row *matRowDef="let row; columns: lineColumns"
                  class="hover:bg-surface-raised transition-colors"></tr>
            </table>
          </div>
        } @else {
          <div class="rounded-lg border border-border-default bg-surface-raised px-4 py-8 text-center">
            <p class="text-text-disabled text-sm">No line items on this invoice.</p>
          </div>
        }
      }
    </div>
  `,
  styles: [`
    :host { display: block; }
    ::ng-deep .mat-mdc-table { background: transparent !important; }
    ::ng-deep .mat-mdc-header-row,
    ::ng-deep .mat-mdc-row { background: transparent !important; }
    ::ng-deep .mat-mdc-cell,
    ::ng-deep .mat-mdc-header-cell { border-bottom: none !important; }
  `],
})
export class InvoiceDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private http = inject(HttpClient);

  loading = signal(true);
  error = signal<string | null>(null);
  invoice = signal<InvoiceDetail | null>(null);
  actionLoading = signal(false);
  actionMessage = signal<string | null>(null);

  readonly lineColumns = ['description', 'quantity', 'unit_price', 'amount'];

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) {
      this.router.navigate(['/app/invoices']);
      return;
    }
    this.http.get<InvoiceDetail>(`/api/v1/invoices/${id}`).subscribe({
      next: (data) => {
        this.invoice.set(data);
        this.loading.set(false);
      },
      error: (err: unknown) => {
        this.error.set(userMessageForError(err, 'Invoice'));
        this.loading.set(false);
      },
    });
  }

  goBack(): void {
    this.router.navigate(['/app/invoices']);
  }

  approveInvoice(): void {
    const inv = this.invoice();
    if (!inv) return;
    this.actionLoading.set(true);
    this.actionMessage.set(null);
    this.http.patch<InvoiceDetail>(`/api/v1/invoices/${inv.id}/approve`, {}).subscribe({
      next: (updated) => {
        this.invoice.set(updated);
        this.actionLoading.set(false);
        this.actionMessage.set('Invoice approved.');
        setTimeout(() => this.actionMessage.set(null), 5000);
      },
      error: () => {
        this.actionLoading.set(false);
        this.actionMessage.set(null);
      },
    });
  }

  sendInvoice(): void {
    const inv = this.invoice();
    if (!inv) return;
    this.actionLoading.set(true);
    this.actionMessage.set(null);
    this.http.post<InvoiceDetail>(`/api/v1/invoices/${inv.id}/send`, {}).subscribe({
      next: (updated) => {
        this.invoice.set(updated);
        this.actionLoading.set(false);
        this.actionMessage.set('Invoice sent successfully.');
        setTimeout(() => this.actionMessage.set(null), 5000);
      },
      error: () => {
        this.actionLoading.set(false);
        this.actionMessage.set(null);
      },
    });
  }

  statusClass(status: string): string {
    switch (status) {
      case 'draft':    return 'bg-surface text-text-muted';
      case 'approved': return 'bg-indigo-950 text-indigo-400';
      case 'sent':     return 'bg-blue-950 text-blue-400';
      case 'paid':     return 'bg-accent/15 text-accent-light';
      case 'overdue':  return 'bg-confidence-low/10 text-confidence-low';
      case 'void':     return 'bg-surface-raised text-text-disabled';
      default:         return 'bg-surface text-text-muted';
    }
  }

  statusDotClass(status: string): string {
    switch (status) {
      case 'draft':    return 'bg-slate-400';
      case 'approved': return 'bg-indigo-400';
      case 'sent':     return 'bg-blue-400';
      case 'paid':     return 'bg-emerald-400';
      case 'overdue':  return 'bg-red-400';
      case 'void':     return 'bg-slate-500';
      default:         return 'bg-slate-400';
    }
  }

  statusLabel(status: string): string {
    const labels: Record<string, string> = {
      draft: 'Draft', approved: 'Approved', sent: 'Sent',
      paid: 'Paid', overdue: 'Overdue', void: 'Void',
    };
    return labels[status] ?? status;
  }
}
