import { Component, inject, signal, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

import { MoneyPipe } from '../../shared/pipes/money.pipe';
import { userMessageForError } from '../../core/utils/error-message';

export interface InvoiceSummary {
  id: string;
  invoice_number: string;
  client_name: string;
  status: string;
  currency: string;
  total_amount: string;
  issue_date: string;
  due_date: string;
  payment_link_url?: string | null;
}

// Backend returns a bare array (not a paginated wrapper).
type InvoiceListResponse = InvoiceSummary[];

@Component({
  selector: 'app-invoices-list',
  standalone: true,
  imports: [
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    MoneyPipe,
  ],
  template: `
    <div class="p-6 bg-surface-base min-h-full">
      <!-- Page header -->
      <div class="mb-6 flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-text-primary">Invoices</h1>
          <p class="text-sm text-text-muted mt-1">Review and send client invoices.</p>
        </div>
        <button
          type="button"
          class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          aria-label="Create new invoice — go to Engagements to draft"
          (click)="goToNewInvoice()"
        >
          <mat-icon class="text-base leading-none">add</mat-icon>
          New invoice
        </button>
      </div>

      <!-- Send confirmation toast -->
      @if (sentMessage()) {
        <div class="mb-4 rounded-lg border border-emerald-800 bg-accent/10 px-4 py-3 text-sm text-accent-light flex items-center gap-2"
             role="status" aria-live="polite">
          <mat-icon class="text-base">check_circle</mat-icon>
          {{ sentMessage() }}
        </div>
      }

      <!-- Loading skeleton -->
      @if (loading()) {
        <div class="rounded-lg overflow-hidden border border-border-default animate-pulse" aria-busy="true" aria-label="Loading invoices">
          @for (row of [1, 2, 3]; track row) {
            <div class="flex gap-4 px-4 py-3 border-b border-border-subtle last:border-0 bg-surface-raised">
              <div class="h-4 bg-surface rounded w-24"></div>
              <div class="h-4 bg-surface rounded w-32"></div>
              <div class="h-4 bg-surface rounded w-20"></div>
              <div class="h-4 bg-surface rounded w-28"></div>
              <div class="h-4 bg-surface rounded w-16"></div>
            </div>
          }
        </div>
      }

      <!-- Error state -->
      @if (error() && !loading()) {
        <div class="rounded-lg border border-confidence-low/30 bg-confidence-low/10 px-4 py-3 text-sm text-confidence-low" role="alert">
          <mat-icon class="text-base align-middle mr-1">error_outline</mat-icon>
          {{ error() }}
        </div>
      }

      <!-- Empty state -->
      @if (!loading() && !error() && invoices().length === 0) {
        <div class="rounded-lg border border-border-default bg-surface-raised px-4 py-12 text-center">
          <mat-icon class="text-4xl text-text-disabled mb-3 block">receipt</mat-icon>
          <p class="text-text-secondary font-medium mb-1">No invoices yet</p>
          <p class="text-text-disabled text-sm">Invoices generated from billing runs will appear here.</p>
        </div>
      }

      <!-- Table -->
      @if (!loading() && !error() && invoices().length > 0) {
        <div class="rounded-lg overflow-hidden border border-border-default">
          <table
            mat-table
            [dataSource]="invoices()"
            class="w-full bg-surface-base"
            aria-label="Invoices"
          >
            <!-- Invoice number -->
            <ng-container matColumnDef="invoice_number">
              <th mat-header-cell *matHeaderCellDef
                  class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Invoice
              </th>
              <td mat-cell *matCellDef="let row"
                  class="text-text-primary text-sm font-mono font-medium px-4 py-3 border-b border-border-subtle">
                {{ row.invoice_number }}
              </td>
            </ng-container>

            <!-- Client -->
            <ng-container matColumnDef="client_name">
              <th mat-header-cell *matHeaderCellDef
                  class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Client
              </th>
              <td mat-cell *matCellDef="let row"
                  class="text-text-primary text-sm px-4 py-3 border-b border-border-subtle">
                {{ row.client_name }}
              </td>
            </ng-container>

            <!-- Status -->
            <ng-container matColumnDef="status">
              <th mat-header-cell *matHeaderCellDef
                  class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Status
              </th>
              <td mat-cell *matCellDef="let row" class="px-4 py-3 border-b border-border-subtle">
                <span
                  class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium"
                  [class]="statusClass(row.status)"
                >
                  {{ statusLabel(row.status) }}
                </span>
              </td>
            </ng-container>

            <!-- Total -->
            <ng-container matColumnDef="total_amount">
              <th mat-header-cell *matHeaderCellDef
                  class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3 text-right">
                Total
              </th>
              <td mat-cell *matCellDef="let row"
                  class="text-text-primary text-sm font-mono px-4 py-3 border-b border-border-subtle text-right tabular-nums">
                {{ row.total_amount | money: row.currency }}
              </td>
            </ng-container>

            <!-- Due date -->
            <ng-container matColumnDef="due_date">
              <th mat-header-cell *matHeaderCellDef
                  class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Due
              </th>
              <td mat-cell *matCellDef="let row"
                  class="text-text-secondary text-sm px-4 py-3 border-b border-border-subtle tabular-nums">
                {{ row.due_date }}
              </td>
            </ng-container>

            <!-- Actions -->
            <ng-container matColumnDef="actions">
              <th mat-header-cell *matHeaderCellDef
                  class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Actions
              </th>
              <td mat-cell *matCellDef="let row" class="px-4 py-3 border-b border-border-subtle">
                @if (row.status === 'approved') {
                  <button
                    (click)="sendInvoice(row)"
                    [disabled]="sendingId() === row.id"
                    mat-stroked-button
                    class="text-xs text-indigo-400 border-indigo-700 hover:bg-indigo-900 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    matTooltip="Send this invoice to the client"
                    [attr.aria-label]="'Send invoice ' + (row.invoice_number)"
                  >
                    <mat-icon class="text-sm">send</mat-icon>
                    @if (sendingId() === row.id) { Sending… } @else { Send }
                  </button>
                }
                @if (row.status === 'sent' && row.payment_link_url) {
                  <a
                    [href]="row.payment_link_url"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="inline-flex items-center gap-1 text-xs text-accent-light hover:text-accent-light transition-colors"
                    [attr.aria-label]="'Open payment link for ' + (row.invoice_number)"
                  >
                    <mat-icon class="text-sm">open_in_new</mat-icon>
                    Payment link
                  </a>
                }
              </td>
            </ng-container>

            <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
            <tr mat-row *matRowDef="let row; columns: displayedColumns"
                class="hover:bg-surface-raised transition-colors cursor-pointer"
                (click)="viewInvoice(row)"></tr>
          </table>
        </div>

        <p class="text-xs text-text-disabled mt-3 text-right">
          {{ invoices().length }} {{ invoices().length === 1 ? 'invoice' : 'invoices' }}
        </p>
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
export class InvoicesListComponent implements OnInit {
  private http = inject(HttpClient);
  private router = inject(Router);

  loading     = signal(true);
  error       = signal<string | null>(null);
  invoices    = signal<InvoiceSummary[]>([]);
  sendingId   = signal<string | null>(null);
  sentMessage = signal<string | null>(null);

  displayedColumns = ['invoice_number', 'client_name', 'status', 'total_amount', 'due_date', 'actions'];

  ngOnInit(): void {
    this.http.get<InvoiceListResponse>('/api/v1/invoices').subscribe({
      next: (res) => {
        this.invoices.set(res);
        this.loading.set(false);
      },
      error: (err: unknown) => {
        // #113: per-status-code copy.
        this.error.set(userMessageForError(err, 'Invoices'));
        this.loading.set(false);
      },
    });
  }

  sendInvoice(invoice: InvoiceSummary): void {
    this.sendingId.set(invoice.id);
    this.sentMessage.set(null);

    this.http.post<{ payment_link_url?: string }>(`/api/v1/invoices/${invoice.id}/send`, {}).subscribe({
      next: (res) => {
        // Update invoice status and payment link in-place
        this.invoices.set(
          this.invoices().map(inv =>
            inv.id === invoice.id
              ? { ...inv, status: 'sent', payment_link_url: res.payment_link_url ?? null }
              : inv
          )
        );
        this.sendingId.set(null);
        const msg = res.payment_link_url
          ? `Invoice sent. Payment link: ${res.payment_link_url}`
          : 'Invoice sent successfully.';
        this.sentMessage.set(msg);
        // Auto-dismiss after 8 seconds
        setTimeout(() => this.sentMessage.set(null), 8000);
      },
      error: () => {
        this.sendingId.set(null);
        this.sentMessage.set(null);
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

  statusLabel(status: string): string {
    const labels: Record<string, string> = {
      draft:    'Draft',
      approved: 'Approved',
      sent:     'Sent',
      paid:     'Paid',
      overdue:  'Overdue',
      void:     'Void',
    };
    return labels[status] ?? status;
  }

  /**
   * Invoices are generated from engagements — navigate there to start the
   * draft-invoice flow rather than opening a standalone create form.
   */
  viewInvoice(invoice: InvoiceSummary): void {
    this.router.navigate(['/app/invoices', invoice.id]);
  }

  goToNewInvoice(): void {
    this.router.navigate(['/app/engagements']);
  }
}
