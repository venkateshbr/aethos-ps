import { Component, inject, signal, OnInit } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';

import { MoneyPipe } from '../../shared/pipes/money.pipe';
import { ConfidenceChipComponent } from '../../shared/components/confidence-chip.component';
import { SourceDocumentLinkComponent } from '../../shared/components/source-document-link.component';
import { userMessageForError } from '../../core/utils/error-message';

interface BillLine {
  id: string;
  description: string;
  quantity: string;
  unit_price: string;
  tax_rate?: string | null;
  amount: string;
  tax_amount?: string | null;
}

interface BillDetail {
  id: string;
  bill_number: string;
  vendor_name?: string | null;
  vendor_id?: string | null;
  currency: string;
  subtotal: string;
  tax_total: string;
  total: string;
  status: string;
  issue_date: string | null;
  due_date: string | null;
  paid_at?: string | null;
  notes?: string | null;
  source_document_id?: string | null;
  confidence?: string | number | null;
  lines: BillLine[];
}

// TODO: Wire up journal entries once GET /api/v1/accounting/journals?reference_id=...
// &reference_type=bill endpoint is confirmed by Karya. See issue #202.
// interface JournalLine {
//   id: string;
//   account_name: string;
//   direction: 'debit' | 'credit';
//   amount: string;
//   currency: string;
// }

@Component({
  selector: 'app-bill-detail',
  standalone: true,
  imports: [
    RouterLink,
    MatButtonModule,
    MatIconModule,
    MatTableModule,
    MatTooltipModule,
    MoneyPipe,
    ConfidenceChipComponent,
    SourceDocumentLinkComponent,
  ],
  template: `
    <div class="p-6 bg-surface-base min-h-full">

      <!-- ── Back nav ─────────────────────────────────────────────────── -->
      <button
        mat-button
        class="text-text-muted hover:text-text-primary mb-4 -ml-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
        (click)="goBack()"
        aria-label="Back to bills list"
      >
        <mat-icon>arrow_back</mat-icon>
        Bills
      </button>

      <!-- ── Loading skeleton ─────────────────────────────────────────── -->
      @if (loading()) {
        <div class="animate-pulse" aria-busy="true" aria-label="Loading bill">
          <div class="h-8 bg-surface-raised rounded w-1/3 mb-3"></div>
          <div class="h-4 bg-surface-raised rounded w-1/5 mb-6"></div>
          <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            @for (item of [1,2,3,4]; track item) {
              <div class="bg-surface-raised rounded p-4 h-16"></div>
            }
          </div>
          <div class="h-48 bg-surface-raised rounded"></div>
        </div>
      }

      <!-- ── Error state ──────────────────────────────────────────────── -->
      @if (error() && !loading()) {
        <div class="rounded-lg border border-confidence-low/30 bg-confidence-low/10 px-4 py-3 text-sm text-confidence-low flex items-center gap-2"
             role="alert">
          <mat-icon class="text-base flex-none">error_outline</mat-icon>
          {{ error() }}
        </div>
      }

      <!-- ── Main content ─────────────────────────────────────────────── -->
      @if (!loading() && !error() && bill()) {

        <!-- ── Header row ──────────────────────────────────────────────── -->
        <div class="flex flex-wrap items-start justify-between gap-4 mb-6">
          <div class="flex flex-wrap items-center gap-3">
            <h1 class="text-2xl font-bold text-text-primary font-mono">{{ bill()!.bill_number }}</h1>

            <!-- Status badge -->
            <span
              class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium"
              [class]="statusClass(bill()!.status)"
            >
              <span class="w-1.5 h-1.5 rounded-full" [class]="statusDotClass(bill()!.status)" aria-hidden="true"></span>
              {{ statusLabel(bill()!.status) }}
            </span>

            <!-- Confidence chip — only on AI-extracted bills -->
            @if (bill()!.confidence != null) {
              <app-confidence-chip [confidence]="bill()!.confidence!" />
            }
          </div>

          <!-- Action buttons -->
          <div class="flex items-center gap-2">
            @if (bill()!.status === 'draft') {
              <button
                type="button"
                (click)="approveBill()"
                [disabled]="actionLoading()"
                class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
                matTooltip="Approve bill — posts DR Expense / CR AP journal"
              >
                <mat-icon class="text-base" style="font-size:1rem;width:1rem;height:1rem;">check_circle</mat-icon>
                @if (actionLoading()) { Approving… } @else { Approve }
              </button>
            }

            @if (bill()!.status === 'approved') {
              <a
                routerLink="/app/billing-runs"
                class="inline-flex items-center gap-2 bg-indigo-700 hover:bg-indigo-600 text-white font-medium px-4 py-2 rounded text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-400"
                matTooltip="Go to Pay Bills wizard to include in a payment batch"
              >
                <mat-icon class="text-base" style="font-size:1rem;width:1rem;height:1rem;">payments</mat-icon>
                Pay
              </a>
              <button
                type="button"
                (click)="voidBill()"
                [disabled]="actionLoading()"
                class="inline-flex items-center gap-2 border border-border-strong hover:border-slate-500 text-text-muted hover:text-confidence-low font-medium px-4 py-2 rounded text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-400"
                matTooltip="Void this bill"
              >
                <mat-icon class="text-base" style="font-size:1rem;width:1rem;height:1rem;">block</mat-icon>
                @if (actionLoading()) { Voiding… } @else { Void }
              </button>
            }
          </div>
        </div>

        <!-- ── Action feedback ────────────────────────────────────────── -->
        @if (actionMessage()) {
          <div class="mb-4 rounded-lg border border-emerald-800 bg-accent/10 px-4 py-3 text-sm text-accent-light flex items-center gap-2"
               role="status" aria-live="polite">
            <mat-icon class="text-base">check_circle</mat-icon>
            {{ actionMessage() }}
          </div>
        }
        @if (actionError()) {
          <div class="mb-4 rounded-lg border border-confidence-low/30 bg-confidence-low/10 px-4 py-3 text-sm text-confidence-low flex items-center gap-2"
               role="alert">
            <mat-icon class="text-base">error_outline</mat-icon>
            {{ actionError() }}
          </div>
        }

        <!-- ── Source document link ───────────────────────────────────── -->
        @if (bill()!.source_document_id) {
          <div class="mb-6 bg-surface-raised border border-border-default rounded-lg px-4 py-3 flex items-center gap-3">
            <mat-icon class="text-text-muted flex-none" style="font-size:1rem;width:1rem;height:1rem;" aria-hidden="true">description</mat-icon>
            <span class="text-xs text-text-muted font-medium uppercase tracking-wide">Source document</span>
            <app-source-document-link
              [documentId]="bill()!.source_document_id!"
              label="Open vendor invoice"
            />
          </div>
        }

        <!-- ── Meta cards ─────────────────────────────────────────────── -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div class="bg-surface-raised border border-border-default rounded-lg p-4">
            <dt class="text-xs font-medium text-text-muted uppercase tracking-wide mb-1">Vendor</dt>
            <dd class="text-sm">
              @if (bill()!.vendor_id) {
                <a
                  [routerLink]="['/app/clients', bill()!.vendor_id]"
                  class="text-indigo-400 hover:text-indigo-300 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-400 rounded"
                >
                  {{ bill()!.vendor_name || bill()!.vendor_id }}
                </a>
              } @else {
                <span class="text-text-primary">{{ bill()!.vendor_name || '—' }}</span>
              }
            </dd>
          </div>
          <div class="bg-surface-raised border border-border-default rounded-lg p-4">
            <dt class="text-xs font-medium text-text-muted uppercase tracking-wide mb-1">Issue Date</dt>
            <dd class="text-text-primary text-sm tabular-nums">{{ bill()!.issue_date ?? '—' }}</dd>
          </div>
          <div class="bg-surface-raised border border-border-default rounded-lg p-4">
            <dt class="text-xs font-medium text-text-muted uppercase tracking-wide mb-1">Due Date</dt>
            <dd class="text-text-primary text-sm tabular-nums">{{ bill()!.due_date ?? '—' }}</dd>
          </div>
          @if (bill()!.paid_at) {
            <div class="bg-surface-raised border border-border-default rounded-lg p-4">
              <dt class="text-xs font-medium text-text-muted uppercase tracking-wide mb-1">Paid On</dt>
              <dd class="text-accent-light text-sm tabular-nums">{{ bill()!.paid_at }}</dd>
            </div>
          }
        </div>

        @if (bill()!.notes) {
          <div class="mb-6 bg-surface-raised border border-border-default rounded-lg p-4">
            <p class="text-xs font-medium text-text-muted uppercase tracking-wide mb-1">Notes</p>
            <p class="text-text-secondary text-sm">{{ bill()!.notes }}</p>
          </div>
        }

        <!-- ── Line items table ───────────────────────────────────────── -->
        <h2 class="text-base font-semibold text-text-primary mb-3">Line items</h2>

        @if (bill()!.lines.length > 0) {
          <div class="rounded-lg overflow-hidden border border-border-default mb-6">
            <table
              mat-table
              [dataSource]="bill()!.lines"
              class="w-full bg-surface-base"
              aria-label="Bill line items"
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
                  Unit Price
                </th>
                <td mat-cell *matCellDef="let line"
                    class="text-text-secondary text-sm font-mono px-4 py-3 border-b border-border-subtle text-right tabular-nums">
                  {{ line.unit_price | money: bill()!.currency }}
                </td>
              </ng-container>

              <ng-container matColumnDef="tax_rate">
                <th mat-header-cell *matHeaderCellDef
                    class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3 text-right">
                  Tax %
                </th>
                <td mat-cell *matCellDef="let line"
                    class="text-text-muted text-sm font-mono px-4 py-3 border-b border-border-subtle text-right tabular-nums">
                  {{ line.tax_rate != null ? line.tax_rate + '%' : '—' }}
                </td>
              </ng-container>

              <ng-container matColumnDef="amount">
                <th mat-header-cell *matHeaderCellDef
                    class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3 text-right">
                  Amount
                </th>
                <td mat-cell *matCellDef="let line"
                    class="text-text-primary text-sm font-mono font-medium px-4 py-3 border-b border-border-subtle text-right tabular-nums">
                  {{ line.amount | money: bill()!.currency }}
                </td>
              </ng-container>

              <tr mat-header-row *matHeaderRowDef="lineColumns"></tr>
              <tr mat-row *matRowDef="let row; columns: lineColumns"
                  class="hover:bg-surface-raised transition-colors"></tr>
            </table>
          </div>

          <!-- ── Totals footer ──────────────────────────────────────────── -->
          <div class="flex justify-end">
            <dl class="w-full max-w-xs space-y-2">
              <div class="flex justify-between text-sm">
                <dt class="text-text-muted">Subtotal</dt>
                <dd class="font-mono text-text-primary tabular-nums">
                  {{ bill()!.subtotal | money: bill()!.currency }}
                </dd>
              </div>
              <div class="flex justify-between text-sm">
                <dt class="text-text-muted">Tax</dt>
                <dd class="font-mono text-text-primary tabular-nums">
                  {{ bill()!.tax_total | money: bill()!.currency }}
                </dd>
              </div>
              <div class="flex justify-between text-base font-bold border-t border-border-default pt-2">
                <dt class="text-text-primary">Total</dt>
                <dd class="font-mono text-text-primary tabular-nums">
                  {{ bill()!.total | money: bill()!.currency }}
                </dd>
              </div>
            </dl>
          </div>
        } @else {
          <div class="rounded-lg border border-border-default bg-surface-raised px-4 py-8 text-center mb-6">
            <p class="text-text-disabled text-sm">No line items on this bill.</p>
          </div>
        }

        <!-- ── Journal entries section ────────────────────────────────── -->
        <!-- TODO (#202): Wire up once GET /api/v1/accounting/journals?reference_id={id}
             &reference_type=bill is confirmed live by Karya. Skipped to avoid
             blocking the rest of the AP detail page. -->

      } <!-- end @if bill() -->

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
export class BillDetailComponent implements OnInit {
  private route  = inject(ActivatedRoute);
  private router = inject(Router);
  private http   = inject(HttpClient);

  loading       = signal(true);
  error         = signal<string | null>(null);
  bill          = signal<BillDetail | null>(null);
  actionLoading = signal(false);
  actionMessage = signal<string | null>(null);
  actionError   = signal<string | null>(null);

  readonly lineColumns = ['description', 'quantity', 'unit_price', 'tax_rate', 'amount'];

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) {
      this.router.navigate(['/app/bills']);
      return;
    }
    this.http.get<BillDetail>(`/api/v1/bills/${id}`).subscribe({
      next: (data) => {
        this.bill.set(data);
        this.loading.set(false);
      },
      error: (err: unknown) => {
        this.error.set(userMessageForError(err, 'Bill'));
        this.loading.set(false);
      },
    });
  }

  goBack(): void {
    this.router.navigate(['/app/bills']);
  }

  approveBill(): void {
    const b = this.bill();
    if (!b) return;
    this.actionLoading.set(true);
    this.actionMessage.set(null);
    this.actionError.set(null);

    this.http.post<BillDetail>(`/api/v1/bills/${b.id}/approve`, {}).subscribe({
      next: (updated) => {
        this.bill.set(updated);
        this.actionLoading.set(false);
        this.actionMessage.set(
          `${b.bill_number} approved — DR Expense / CR AP journal posted.`,
        );
        setTimeout(() => this.actionMessage.set(null), 6000);
      },
      error: (err: unknown) => {
        this.actionLoading.set(false);
        this.actionError.set(userMessageForError(err, 'Approve bill'));
        setTimeout(() => this.actionError.set(null), 6000);
      },
    });
  }

  voidBill(): void {
    const b = this.bill();
    if (!b) return;
    this.actionLoading.set(true);
    this.actionMessage.set(null);
    this.actionError.set(null);

    this.http.post<BillDetail>(`/api/v1/bills/${b.id}/void`, {}).subscribe({
      next: (updated) => {
        this.bill.set(updated);
        this.actionLoading.set(false);
        this.actionMessage.set(`${b.bill_number} has been voided.`);
        setTimeout(() => this.actionMessage.set(null), 6000);
      },
      error: (err: unknown) => {
        this.actionLoading.set(false);
        this.actionError.set(userMessageForError(err, 'Void bill'));
        setTimeout(() => this.actionError.set(null), 6000);
      },
    });
  }

  statusClass(status: string): string {
    switch (status) {
      case 'draft':    return 'bg-surface text-text-muted border border-border-default';
      case 'approved': return 'bg-indigo-950 text-indigo-400';
      case 'paid':     return 'bg-accent/15 text-accent-light';
      case 'overdue':  return 'bg-confidence-low/10 text-confidence-low';
      case 'voided':
      case 'void':     return 'bg-surface-raised text-text-disabled';
      default:         return 'bg-surface text-text-muted';
    }
  }

  statusDotClass(status: string): string {
    switch (status) {
      case 'draft':    return 'bg-slate-400';
      case 'approved': return 'bg-indigo-400';
      case 'paid':     return 'bg-emerald-400';
      case 'overdue':  return 'bg-red-400';
      case 'voided':
      case 'void':     return 'bg-slate-500';
      default:         return 'bg-slate-400';
    }
  }

  statusLabel(status: string): string {
    const labels: Record<string, string> = {
      draft:    'Draft',
      approved: 'Approved',
      paid:     'Paid',
      overdue:  'Overdue',
      voided:   'Voided',
      void:     'Voided',
    };
    return labels[status] ?? status;
  }
}
