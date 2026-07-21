import { Component, computed, inject, signal, OnInit } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';

import { MoneyPipe } from '../../shared/pipes/money.pipe';
import { ConfidenceChipComponent } from '../../shared/components/confidence-chip.component';
import { SourceDocumentLinkComponent } from '../../shared/components/source-document-link.component';
import { DecisionTimelineComponent } from '../../shared/components/decision-timeline.component';
import { userMessageForError } from '../../core/utils/error-message';
import { CurrentPermissionsService } from '../../core/services/current-permissions.service';

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
  purchase_order_id?: string | null;
  po_match_status?: string | null;
  po_match_summary?: Record<string, unknown> | null;
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
  vendor_invoice_review?: Record<string, unknown> | null;
  confidence?: string | number | null;
  lines: BillLine[];
}

interface PoMatchSource {
  po_match_summary?: Record<string, unknown> | null;
}

interface PoLineException {
  code: string;
  message: string;
  billLineDescription: string;
  orderLineDescription: string;
}

interface PoLineMatch {
  billLineDescription: string;
  orderLineDescription: string;
  quantityStatus: string;
  unitPriceStatus: string;
  amountStatus: string;
  servicePeriodStatus: string;
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
    DecisionTimelineComponent,
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
                [disabled]="actionLoading() || !canApproveBill()"
                class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
                [matTooltip]="canApproveBill() ? 'Approve bill — posts DR Expense / CR AP journal' : 'Requires bill approval permission'"
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
                [disabled]="actionLoading() || !canManageBills()"
                class="inline-flex items-center gap-2 border border-border-strong hover:border-slate-500 text-text-muted hover:text-confidence-low font-medium px-4 py-2 rounded text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-400"
                [matTooltip]="canManageBills() ? 'Void this bill' : 'Requires bill management permission'"
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

        @if (hasVendorInvoiceReview(bill()!)) {
          <section class="mb-6 bg-surface-raised border border-border-default rounded-lg p-4" aria-labelledby="ap-review-heading">
            <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 id="ap-review-heading" class="text-sm font-semibold text-text-primary">AP review evidence</h2>
                <p class="mt-0.5 text-xs text-text-muted">Vendor invoice intake, coding, and duplicate review trail.</p>
              </div>
              <span class="rounded bg-surface px-2 py-0.5 text-xs text-text-secondary">
                {{ reviewValue(bill()!, 'match_status') || 'reviewed' }}
              </span>
            </div>
            <div class="grid gap-3 md:grid-cols-3">
              <div class="rounded border border-border-subtle bg-surface px-3 py-2">
                <p class="text-[11px] uppercase tracking-wide text-text-disabled">Vendor match</p>
                <p class="mt-1 text-xs text-text-primary">{{ vendorMatchSummary(bill()!) }}</p>
              </div>
              <div class="rounded border border-border-subtle bg-surface px-3 py-2">
                <p class="text-[11px] uppercase tracking-wide text-text-disabled">Duplicate guard</p>
                <p class="mt-1 text-xs text-text-primary">{{ duplicateReviewSummary(bill()!) }}</p>
              </div>
              <div class="rounded border border-border-subtle bg-surface px-3 py-2">
                <p class="text-[11px] uppercase tracking-wide text-text-disabled">Coding</p>
                <p class="mt-1 text-xs text-text-primary">{{ reviewValue(bill()!, 'coding_status') || 'unknown' }}</p>
              </div>
            </div>
            @if (reviewExceptions(bill()!).length) {
              <div class="mt-3 space-y-1">
                @for (exception of reviewExceptions(bill()!); track exception.code + exception.message) {
                  <div class="rounded border border-confidence-low/20 bg-confidence-low/10 px-2 py-1.5 text-xs text-confidence-low">
                    <span class="font-medium">{{ exception.code }}</span>
                    @if (exception.message) { <span> - {{ exception.message }}</span> }
                  </div>
                }
              </div>
            }
            @if (reviewBadges(bill()!).length) {
              <div class="mt-3 flex flex-wrap gap-1.5">
                @for (badge of reviewBadges(bill()!); track badge) {
                  <span class="rounded bg-surface px-2 py-1 text-xs text-text-secondary">{{ badge }}</span>
                }
              </div>
            }
          </section>
        }

        <app-decision-timeline entityType="bill" [entityId]="bill()!.id" />

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
            <dt class="text-xs font-medium text-text-muted uppercase tracking-wide mb-1">PO / SO Match</dt>
            <dd class="text-sm">
              @if (bill()!.purchase_order_id) {
                <div class="flex flex-col gap-1">
                  <span class="font-mono text-accent-light">{{ poNumber(bill()!) }}</span>
                  <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium w-fit" [class]="poMatchClass(bill()!.po_match_status)">
                    {{ poMatchLabel(bill()!.po_match_status) }}
                  </span>
                  @if (poLineEvidenceLabel(bill()!)) {
                    <span class="text-xs text-text-muted">{{ poLineEvidenceLabel(bill()!) }}</span>
                  }
                </div>
              } @else {
                <span class="text-text-muted">Not linked</span>
              }
            </dd>
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

        @if (bill()!.purchase_order_id && hasPoMatchEvidence(bill()!)) {
          <section class="mb-6 bg-surface-raised border border-border-default rounded-lg p-4" aria-labelledby="po-match-evidence-heading">
            <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 id="po-match-evidence-heading" class="text-sm font-semibold text-text-primary">PO / SO match evidence</h2>
                <p class="mt-0.5 text-xs text-text-muted">{{ poNumber(bill()!) }}</p>
              </div>
              <span class="rounded bg-surface px-2 py-0.5 text-xs text-text-secondary">
                {{ poLineEvidenceLabel(bill()!) || poMatchLabel(bill()!.po_match_status) }}
              </span>
            </div>

            @if (poLineExceptions(bill()!).length) {
              <div class="space-y-1.5">
                @for (exception of poLineExceptions(bill()!); track exception.code + exception.billLineDescription + exception.orderLineDescription) {
                  <div class="rounded border border-confidence-low/20 bg-confidence-low/10 px-2 py-1.5 text-xs text-confidence-low">
                    <span class="font-medium">{{ poExceptionLabel(exception.code) }}</span>
                    @if (exception.billLineDescription) { <span> - {{ exception.billLineDescription }}</span> }
                    @if (exception.orderLineDescription) { <span> against {{ exception.orderLineDescription }}</span> }
                    @if (exception.message) { <span class="block text-[11px] text-confidence-low/90">{{ exception.message }}</span> }
                  </div>
                }
              </div>
            }

            @if (poLineMatches(bill()!).length) {
              <div class="mt-3 grid gap-2 md:grid-cols-2">
                @for (match of poLineMatches(bill()!); track match.billLineDescription + match.orderLineDescription) {
                  <div class="rounded border border-border-subtle bg-surface px-3 py-2">
                    <p class="text-xs font-medium text-text-primary">{{ match.billLineDescription }}</p>
                    <p class="mt-0.5 text-[11px] text-text-muted">Order line: {{ match.orderLineDescription }}</p>
                    <p class="mt-1 text-[11px] text-text-secondary">{{ poLineMatchSummary(match) }}</p>
                  </div>
                }
              </div>
            }
          </section>
        }

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
  private permissions = inject(CurrentPermissionsService);

  loading       = signal(true);
  error         = signal<string | null>(null);
  bill          = signal<BillDetail | null>(null);
  actionLoading = signal(false);
  actionMessage = signal<string | null>(null);
  actionError   = signal<string | null>(null);
  canApproveBill = computed(() => this.permissions.hasPrivilege('bills.approve'));
  canManageBills = computed(() => this.permissions.hasPrivilege('bills.manage'));

  readonly lineColumns = ['description', 'quantity', 'unit_price', 'tax_rate', 'amount'];

  ngOnInit(): void {
    this.permissions.ensureLoaded();
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
    if (!b || !this.canApproveBill()) return;
    this.actionLoading.set(true);
    this.actionMessage.set(null);
    this.actionError.set(null);

    this.http.patch<{ status: string }>(`/api/v1/bills/${b.id}/approve`, {}).subscribe({
      next: (updated) => {
        this.bill.set({ ...b, status: updated.status });
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
    if (!b || !this.canManageBills()) return;
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

  hasVendorInvoiceReview(bill: BillDetail): boolean {
    return !!bill.vendor_invoice_review && Object.keys(bill.vendor_invoice_review).length > 0;
  }

  reviewValue(bill: BillDetail, key: string): string {
    const value = bill.vendor_invoice_review?.[key];
    return value == null ? '' : String(value);
  }

  vendorMatchSummary(bill: BillDetail): string {
    const review = bill.vendor_invoice_review ?? {};
    const match = (
      typeof review['vendor_match'] === 'object' && review['vendor_match'] !== null
        ? review['vendor_match']
        : {}
    ) as Record<string, unknown>;
    const status = String(review['match_status'] ?? 'unknown');
    const confidence = match['confidence'] != null
      ? ` - ${Math.round(Number(match['confidence']) * 100)}%`
      : '';
    const reason = match['match_reason'] ? ` - ${String(match['match_reason'])}` : '';
    return `${status}${confidence}${reason}`;
  }

  duplicateReviewSummary(bill: BillDetail): string {
    const review = bill.vendor_invoice_review ?? {};
    const duplicate = (
      typeof review['duplicate_review'] === 'object' && review['duplicate_review'] !== null
        ? review['duplicate_review']
        : {}
    ) as Record<string, unknown>;
    if (duplicate['approved_duplicate'] === true && duplicate['reason']) {
      return `Approved duplicate - ${String(duplicate['reason'])}`;
    }
    const exceptions = this.reviewExceptions(bill).map(item => item.code);
    return exceptions.includes('possible_duplicate') ? 'Possible duplicate reviewed' : 'No duplicate flagged';
  }

  reviewExceptions(bill: BillDetail): { code: string; message: string }[] {
    const exceptions = bill.vendor_invoice_review?.['review_exceptions'];
    if (!Array.isArray(exceptions)) return [];
    return exceptions
      .filter((item): item is Record<string, unknown> => typeof item === 'object' && item !== null)
      .map(item => ({
        code: String(item['code'] ?? 'review_required'),
        message: String(item['message'] ?? ''),
      }));
  }

  reviewBadges(bill: BillDetail): string[] {
    const review = bill.vendor_invoice_review ?? {};
    const badges: string[] = [];
    const suggestions = Array.isArray(review['gl_suggestions']) ? review['gl_suggestions'] : [];
    for (const item of suggestions) {
      if (typeof item !== 'object' || item === null) continue;
      const suggestion = item as Record<string, unknown>;
      const account = [suggestion['account_code'], suggestion['account_name']]
        .filter(value => value !== undefined && value !== null && String(value).trim())
        .join(' ');
      const confidence = suggestion['confidence'] != null
        ? ` (${Math.round(Number(suggestion['confidence']) * 100)}%)`
        : '';
      badges.push(`${account || 'Suggested account'}${confidence}`);
    }
    this.pushHintBadge(badges, review['project_hints'], 'project');
    this.pushHintBadge(badges, review['customer_hints'], 'customer');
    return badges.slice(0, 8);
  }

  private pushHintBadge(badges: string[], value: unknown, label: string): void {
    if (Array.isArray(value) && value.length) {
      badges.push(`${value.length} ${label} hint(s)`);
    }
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

  poNumber(bill: BillDetail): string {
    const summary = bill.po_match_summary ?? {};
    return String(summary['purchase_order_number'] ?? bill.purchase_order_id ?? 'Linked');
  }

  poMatchLabel(status: string | null | undefined): string {
    const labels: Record<string, string> = {
      not_linked: 'Not linked',
      matched: 'Matched',
      over_tolerance: 'Over tolerance',
      vendor_mismatch: 'Vendor mismatch',
      currency_mismatch: 'Currency mismatch',
      order_not_approved: 'Order not approved',
      order_not_found: 'Order not found',
      line_mismatch: 'Line mismatch',
      service_period_mismatch: 'Service period mismatch',
    };
    return labels[status ?? 'not_linked'] ?? status ?? 'Not linked';
  }

  poMatchClass(status: string | null | undefined): string {
    switch (status) {
      case 'matched': return 'bg-accent/15 text-accent-light';
      case 'over_tolerance':
      case 'vendor_mismatch':
      case 'currency_mismatch':
      case 'order_not_approved':
      case 'order_not_found':
      case 'line_mismatch':
      case 'service_period_mismatch':
        return 'bg-confidence-low/10 text-confidence-low';
      default:
        return 'bg-surface text-text-muted border border-border-default';
    }
  }

  hasPoMatchEvidence(bill: BillDetail): boolean {
    return !!this.poLineEvidenceLabel(bill)
      || this.poLineExceptions(bill).length > 0
      || this.poLineMatches(bill).length > 0;
  }

  poLineEvidenceLabel(row: PoMatchSource): string {
    const status = String(row.po_match_summary?.['line_match_status'] ?? '');
    const labels: Record<string, string> = {
      matched: 'Line evidence matched',
      mismatch: 'Line evidence exception',
      not_available: 'Line evidence not available',
    };
    return labels[status] ?? '';
  }

  poLineExceptions(row: PoMatchSource): PoLineException[] {
    const raw = row.po_match_summary?.['line_exceptions'];
    if (!Array.isArray(raw)) return [];
    return raw
      .filter((item): item is Record<string, unknown> => typeof item === 'object' && item !== null)
      .map((item) => ({
        code: String(item['code'] ?? 'line_mismatch'),
        message: String(item['message'] ?? ''),
        billLineDescription: String(item['bill_line_description'] ?? ''),
        orderLineDescription: String(item['order_line_description'] ?? ''),
      }));
  }

  poLineMatches(row: PoMatchSource): PoLineMatch[] {
    const raw = row.po_match_summary?.['line_matches'];
    if (!Array.isArray(raw)) return [];
    return raw
      .filter((item): item is Record<string, unknown> => typeof item === 'object' && item !== null)
      .map((item) => ({
        billLineDescription: String(item['bill_line_description'] ?? ''),
        orderLineDescription: String(item['order_line_description'] ?? ''),
        quantityStatus: this.matchFieldStatus(item['quantity']),
        unitPriceStatus: this.matchFieldStatus(item['unit_price']),
        amountStatus: this.matchFieldStatus(item['amount']),
        servicePeriodStatus: this.matchFieldStatus(item['service_period']),
      }));
  }

  poLineMatchSummary(match: PoLineMatch): string {
    const parts = [
      `Qty ${this.matchStatusLabel(match.quantityStatus)}`,
      `unit price ${this.matchStatusLabel(match.unitPriceStatus)}`,
      `amount ${this.matchStatusLabel(match.amountStatus)}`,
    ];
    if (match.servicePeriodStatus && match.servicePeriodStatus !== 'not_applicable') {
      parts.push(`service period ${this.matchStatusLabel(match.servicePeriodStatus)}`);
    }
    return parts.join(', ');
  }

  poExceptionLabel(code: string): string {
    const labels: Record<string, string> = {
      quantity_mismatch: 'Quantity mismatch',
      unit_price_mismatch: 'Unit price mismatch',
      amount_mismatch: 'Amount mismatch',
      unmatched_bill_line: 'Unmatched bill line',
      service_period_missing: 'Service period missing',
      service_period_mismatch: 'Service period mismatch',
    };
    return labels[code] ?? code.replace(/_/g, ' ');
  }

  private matchFieldStatus(value: unknown): string {
    if (typeof value !== 'object' || value === null) return '';
    return String((value as Record<string, unknown>)['status'] ?? '');
  }

  private matchStatusLabel(status: string): string {
    const labels: Record<string, string> = {
      matched: 'matched',
      mismatch: 'mismatch',
      missing: 'missing',
      not_available: 'not available',
      not_applicable: 'not applicable',
    };
    return labels[status] ?? status;
  }
}
