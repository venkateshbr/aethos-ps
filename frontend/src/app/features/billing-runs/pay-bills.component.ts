import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatStepperModule } from '@angular/material/stepper';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MoneyPipe } from '../../shared/pipes/money.pipe';
import { BillingRunsService, Bill, PaymentSettlement } from '../../core/services/billing-runs.service';
import { EngagementService, EngagementSummary } from '../../core/services/engagement.service';
import { SourceDocumentLinkComponent } from '../../shared/components/source-document-link.component';
import { DecisionTimelineComponent } from '../../shared/components/decision-timeline.component';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-pay-bills',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    MatStepperModule,
    MatCheckboxModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MoneyPipe,
    SourceDocumentLinkComponent,
    DecisionTimelineComponent,
  ],
  template: `
    <div class="min-h-full bg-surface-base p-6">
      <div class="max-w-3xl mx-auto">
        <h1 class="text-2xl font-semibold text-text-primary mb-6">Billing</h1>

        <!-- ── Run Billing (#239) ───────────────────────────────────────── -->
        <div class="bg-surface-raised border border-border-default rounded-xl p-5 mb-8">
          <h2 class="text-base font-semibold text-text-primary mb-1">Run Billing</h2>
          <p class="text-sm text-text-muted mb-4">Generate invoices for your active engagements</p>

          <div class="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
            <!-- Engagement dropdown -->
            <div class="flex-1 min-w-0">
              @if (loadingEngagements()) {
                <div class="h-9 bg-surface rounded border border-border-default animate-pulse"></div>
              } @else {
                <select
                  [(ngModel)]="selectedEngagementId"
                  name="billing-engagement"
                  aria-label="Select engagement to bill"
                  class="w-full px-3 py-2 bg-surface border border-border-strong rounded-lg text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                >
                  <option value="">Select engagement…</option>
                  @for (eng of activeEngagements(); track eng.id) {
                    <option [value]="eng.id">{{ eng.name }}{{ eng.client_name ? ' — ' + eng.client_name : '' }}</option>
                  }
                </select>
              }
            </div>

            <!-- Run Billing button -->
            <button
              [disabled]="!selectedEngagementId || runningBilling()"
              (click)="runBilling()"
              class="flex-none inline-flex items-center gap-2 px-5 py-2 text-sm font-medium rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-400"
              aria-label="Run billing for selected engagement"
            >
              @if (runningBilling()) {
                <mat-spinner diameter="14" class="inline-block" />
                Running…
              } @else {
                <mat-icon class="text-base" style="font-size:1rem;width:1rem;height:1rem;" aria-hidden="true">receipt_long</mat-icon>
                Run Billing
              }
            </button>
          </div>

          @if (billingRunError()) {
            <p class="mt-3 text-xs text-confidence-low" role="alert">{{ billingRunError() }}</p>
          }
        </div>

        <!-- ── Pay Bills stepper ────────────────────────────────────────── -->
        <h2 class="text-lg font-semibold text-text-primary mb-4">Pay Bills</h2>

        @if (loadingBills()) {
          <div class="flex justify-center py-16">
            <mat-spinner diameter="40" />
          </div>
        } @else if (billsError()) {
          <div class="flex flex-col items-center justify-center h-64 text-center bg-surface-raised rounded-lg border border-border-default" role="alert">
            <mat-icon class="text-confidence-low mb-3" style="font-size:2rem;width:2rem;height:2rem;">error_outline</mat-icon>
            <p class="text-text-secondary font-medium">Failed to load approved bills</p>
            <p class="text-text-disabled text-sm mt-1 mb-4">Something went wrong. Please try again.</p>
            <button
              (click)="loadBills()"
              class="px-4 py-2 text-xs font-medium rounded bg-surface hover:bg-surface-raised text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
            >Retry</button>
          </div>
        } @else {
          <mat-stepper [linear]="false" orientation="horizontal" #stepper class="pay-bills-stepper bg-surface-raised rounded-xl border border-border-default p-6">

            <!-- ── Step 1: Select Bills ─────────────────────────────────── -->
            <mat-step label="Select Bills" [completed]="step1Complete()">
              <div class="py-4">
                @if (bills().length === 0) {
                  <div class="flex flex-col items-center justify-center h-48 text-center">
                    <mat-icon class="text-text-disabled mb-3" style="font-size:2.5rem;width:2.5rem;height:2.5rem;" aria-hidden="true">check_circle</mat-icon>
                    <p class="text-text-muted font-medium">No approved bills</p>
                    <p class="text-text-disabled text-sm mt-1">All bills have been paid or none are ready for payment.</p>
                  </div>
                } @else {
                  <!-- Select all / deselect all -->
                  <div class="flex items-center justify-between mb-4">
                    <button
                      (click)="selectAll()"
                      class="text-xs text-indigo-400 hover:text-indigo-300 font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-400 rounded"
                    >Select all</button>
                    <button
                      (click)="deselectAll()"
                      class="text-xs text-text-muted hover:text-text-secondary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-400 rounded"
                    >Deselect all</button>
                  </div>

                  <!-- Bills list -->
                  <div class="space-y-2 mb-4">
                    @for (bill of bills(); track bill.id) {
                      <label
                        class="flex items-center gap-4 p-3 rounded-lg border cursor-pointer transition-colors"
                        [class]="isSelected(bill.id)
                          ? 'bg-surface border-indigo-500/50'
                          : 'bg-surface-raised/50 border-border-default hover:border-border-strong'"
                      >
                        <mat-checkbox
                          [checked]="isSelected(bill.id)"
                          (change)="toggleBill(bill.id)"
                          [aria-label]="'Select bill ' + bill.bill_number"
                          color="primary"
                        />
                        <div class="flex-1 grid grid-cols-3 gap-2 text-sm min-w-0">
                          <span class="text-text-secondary truncate font-mono text-xs">{{ bill.bill_number }}</span>
                          <span class="text-text-muted text-xs text-center">{{ bill.client_id }}</span>
                          <span class="text-xs text-text-muted text-right">Due {{ bill.due_date | date:'mediumDate' }}</span>
                        </div>
                        @if (bill.source_document_id) {
                          <span class="ml-2 flex-shrink-0" (click)="$event.preventDefault(); $event.stopPropagation()">
                            <app-source-document-link [documentId]="bill.source_document_id" label="Invoice" />
                          </span>
                        }
                        <span class="text-text-primary font-semibold font-mono text-sm ml-2 flex-shrink-0">{{ bill.amount | money: bill.currency }}</span>
                      </label>
                    }
                  </div>

                  <!-- Running total -->
                  <div class="bg-surface-base/50 border border-border-default rounded-lg px-4 py-3 flex items-center justify-between mb-6">
                    <span class="text-sm text-text-muted">
                      <span class="font-semibold text-text-primary">{{ selectedIds().size }}</span> bills selected
                    </span>
                    <span class="text-text-primary font-bold font-mono">
                      Total: {{ runningTotal() | money }}
                    </span>
                  </div>

                  <button
                    matStepperNext
                    [disabled]="!step1Complete()"
                    class="w-full sm:w-auto px-6 py-2.5 text-sm font-medium rounded-lg bg-indigo-600 hover:bg-indigo-500 text-text-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-400"
                  >Next: Batch Details</button>
                }
              </div>
            </mat-step>

            <!-- ── Step 2: Batch Details ───────────────────────────────── -->
            <mat-step label="Batch Details" [completed]="step2Complete()">
              <div class="py-4">
                <!-- Total summary -->
                <div class="bg-surface-base/50 border border-border-default rounded-lg p-4 mb-6 text-center">
                  <p class="text-xs text-text-muted uppercase tracking-wide mb-1">Batch Total</p>
                  <p class="text-4xl font-bold text-text-primary font-mono">{{ runningTotal() | money }}</p>
                  <p class="text-sm text-text-muted mt-1">{{ selectedIds().size }} bills</p>
                </div>

                <!-- Pay date -->
                <div class="mb-4">
                  <label for="pay-date" class="block text-sm font-medium text-text-secondary mb-1.5">Pay Date</label>
                  <input
                    id="pay-date"
                    type="date"
                    [(ngModel)]="payDate"
                    class="w-full bg-surface border border-border-strong rounded-lg px-3 py-2 text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    autocomplete="off"
                  />
                </div>

                <!-- Bank label -->
                <div class="mb-6">
                  <label for="bank-label" class="block text-sm font-medium text-text-secondary mb-1.5">Bank Account</label>
                  <input
                    id="bank-label"
                    type="text"
                    [(ngModel)]="bankLabel"
                    placeholder="e.g. Operating Account"
                    class="w-full bg-surface border border-border-strong rounded-lg px-3 py-2 text-text-primary text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    autocomplete="off"
                  />
                </div>

                <div class="flex gap-3">
                  <button
                    matStepperPrevious
                    class="px-4 py-2.5 text-sm font-medium rounded-lg border border-border-strong text-text-secondary hover:border-slate-500 hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-400"
                  >Back</button>

                  <button
                    [disabled]="creatingBatch()"
                    (click)="createBatch(stepper)"
                    class="flex-1 sm:flex-none px-6 py-2.5 text-sm font-medium rounded-lg bg-indigo-600 hover:bg-indigo-500 text-text-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-400"
                  >
                    @if (creatingBatch()) { Creating... } @else { Create Batch }
                  </button>
                </div>

                @if (batchError()) {
                  <p class="mt-3 text-xs text-confidence-low" role="alert">Something went wrong creating the batch. Please try again.</p>
                }
              </div>
            </mat-step>

            <!-- ── Step 3: Export ─────────────────────────────────────── -->
            <mat-step label="Export">
              <div class="py-4">
                <p class="text-sm text-text-secondary mb-1">Batch <span class="font-mono text-text-primary">{{ batchId() || 'not created' }}</span></p>
                <p class="text-xs text-text-disabled mb-6">Approve the batch, download the payment file, then mark it as sent.</p>

                @if (batchId()) {
                  <app-decision-timeline entityType="bill_payment_batch" [entityId]="batchId()!" title="Payment approval timeline" />
                }

                <div class="mb-6 rounded-lg border border-border-default bg-surface-base/50 p-4">
                  <div class="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p class="text-xs uppercase tracking-wide text-text-muted">Batch status</p>
                      <p class="mt-1 text-sm font-medium text-text-primary">{{ batchStatusLabel() }}</p>
                    </div>
                    @if (batchStatus() === 'draft') {
                      <button
                        [disabled]="approvingBatch()"
                        (click)="approveBatch()"
                        class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-accent hover:bg-accent text-text-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
                      >
                        @if (approvingBatch()) { Approving... } @else { Approve Batch }
                      </button>
                    }
                  </div>
                  @if (approveError()) {
                    <p class="mt-3 text-xs text-confidence-low" role="alert">Could not approve this batch. Please try again.</p>
                  }
                </div>

                <div class="flex flex-col sm:flex-row gap-3 mb-8">
                  <button
                    [disabled]="downloading() || !canExport()"
                    (click)="downloadNacha()"
                    class="flex items-center justify-center gap-2 px-5 py-2.5 text-sm font-medium rounded-lg bg-surface hover:bg-surface-raised text-text-primary border border-border-strong hover:border-slate-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-400"
                  >
                    <mat-icon class="text-base" style="font-size:1.1rem;width:1.1rem;height:1.1rem;" aria-hidden="true">download</mat-icon>
                    Download NACHA
                  </button>

                  <button
                    [disabled]="downloading() || !canExport()"
                    (click)="downloadCsv()"
                    class="flex items-center justify-center gap-2 px-5 py-2.5 text-sm font-medium rounded-lg bg-surface hover:bg-surface-raised text-text-primary border border-border-strong hover:border-slate-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-400"
                  >
                    <mat-icon class="text-base" style="font-size:1.1rem;width:1.1rem;height:1.1rem;" aria-hidden="true">table_view</mat-icon>
                    Download CSV
                  </button>
                </div>
                @if (exportLabel()) {
                  <p class="mb-6 text-xs text-accent-light" role="status">{{ exportLabel() }}</p>
                }
                @if (exportError()) {
                  <p class="mb-6 text-xs text-confidence-low" role="alert">Export failed. Please try again.</p>
                }

                <div class="border-t border-border-default pt-6">
                  <p class="text-xs text-text-muted mb-4">Once you have uploaded the file to your bank's portal, mark the batch as sent.</p>
                  <button
                    [disabled]="markingSent() || !canMarkSent()"
                    (click)="markSent(stepper)"
                    class="px-6 py-2.5 text-sm font-medium rounded-lg bg-accent hover:bg-accent text-text-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
                  >
                    @if (markingSent()) { Marking... } @else { Mark as Sent to Bank }
                  </button>
                </div>

                @if (markSentError()) {
                  <p class="mt-3 text-xs text-confidence-low" role="alert">Something went wrong. Please try again.</p>
                }
              </div>
            </mat-step>

            <!-- ── Step 4: Settle ─────────────────────────────────────── -->
            <mat-step label="Settle">
              <div class="py-8 flex flex-col items-center text-center">
                <mat-icon
                  class="text-accent-light mb-4"
                  style="font-size:3rem;width:3rem;height:3rem;"
                  aria-hidden="true"
                >check_circle</mat-icon>
                @if (!settlement()) {
                  <h2 class="text-xl font-semibold text-text-primary mb-2">Batch sent to bank</h2>
                  <p class="text-sm text-text-muted mb-6">Payment batch <span class="font-mono text-text-primary">{{ batchId() }}</span> has been marked as sent.</p>
                } @else {
                  <h2 class="text-xl font-semibold text-text-primary mb-2">Batch settled</h2>
                  <p class="text-sm text-text-muted mb-2">{{ settlement()!.settled_count }} bills settled.</p>
                  @if (settlement()!.journal_entry_ids.length) {
                    <p class="text-xs text-text-disabled mb-6">Journals: {{ settlement()!.journal_entry_ids.join(', ') }}</p>
                  }
                }
                @if (batchId()) {
                  <app-decision-timeline entityType="bill_payment_batch" [entityId]="batchId()!" title="Payment approval timeline" />
                }
                @if (!settlement()) {
                  <button
                    [disabled]="settlingBatch() || !canSettle()"
                    (click)="settleBatch()"
                    class="mt-6 px-6 py-2.5 text-sm font-medium rounded-lg bg-accent hover:bg-accent text-text-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
                  >
                    @if (settlingBatch()) { Settling... } @else { Confirm Settlement }
                  </button>
                } @else {
                  <a
                    routerLink="/app/bills"
                    class="mt-6 text-sm text-indigo-400 hover:text-indigo-300 underline transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-400 rounded"
                  >Back to bills</a>
                }
                @if (settleError()) {
                  <p class="mt-3 text-xs text-confidence-low" role="alert">Settlement failed. Please try again.</p>
                }
              </div>
            </mat-step>

          </mat-stepper>
        }
      </div>
    </div>
  `,
  styles: [`
    :host { display: block; }

    ::ng-deep .pay-bills-stepper .mat-horizontal-stepper-header-container {
      margin-bottom: 1.5rem;
    }
    ::ng-deep .pay-bills-stepper .mat-step-header .mat-step-label {
      color: rgb(148 163 184); /* slate-400 */
      font-size: 0.8125rem;
    }
    ::ng-deep .pay-bills-stepper .mat-step-header.cdk-focused .mat-step-label,
    ::ng-deep .pay-bills-stepper .mat-step-header[aria-selected="true"] .mat-step-label {
      color: rgb(248 250 252); /* slate-50 */
    }
    ::ng-deep .pay-bills-stepper .mat-step-header .mat-step-icon {
      background-color: rgb(51 65 85); /* slate-700 */
    }
    ::ng-deep .pay-bills-stepper .mat-step-header .mat-step-icon-selected,
    ::ng-deep .pay-bills-stepper .mat-step-header .mat-step-icon-state-edit {
      background-color: rgb(99 102 241); /* indigo-500 */
    }
    ::ng-deep .pay-bills-stepper .mat-step-header .mat-step-icon-state-done {
      background-color: rgb(16 185 129); /* emerald-500 */
    }
    ::ng-deep .pay-bills-stepper .mat-horizontal-content-container {
      padding: 0;
    }
    ::ng-deep .pay-bills-stepper.mat-stepper-horizontal {
      background: transparent;
    }
    ::ng-deep .pay-bills-stepper .mat-checkbox-checked .mat-checkbox-background {
      background-color: rgb(99 102 241);
    }
  `],
})
export class PayBillsComponent implements OnInit {
  private svc = inject(BillingRunsService);
  private engagementService = inject(EngagementService);
  private http = inject(HttpClient);
  private snackBar = inject(MatSnackBar);
  private router = inject(Router);

  // ── Pay Bills loading states ───────────────────────────────────────────
  loadingBills = signal(true);
  billsError = signal(false);
  creatingBatch = signal(false);
  batchError = signal(false);
  approvingBatch = signal(false);
  approveError = signal(false);
  downloading = signal(false);
  exportError = signal(false);
  markingSent = signal(false);
  markSentError = signal(false);
  settlingBatch = signal(false);
  settleError = signal(false);

  // ── Run Billing state (#239) ───────────────────────────────────────────
  loadingEngagements = signal(true);
  activeEngagements = signal<EngagementSummary[]>([]);
  selectedEngagementId = '';
  runningBilling = signal(false);
  billingRunError = signal<string | null>(null);

  // ── Pay Bills data ─────────────────────────────────────────────────────
  bills = signal<Bill[]>([]);
  selectedIds = signal<Set<string>>(new Set());
  batchId = signal<string | null>(null);
  batchStatus = signal<string | null>(null);
  exported = signal(false);
  exportLabel = signal<string | null>(null);
  settlement = signal<PaymentSettlement | null>(null);

  // Form values
  payDate = '';
  bankLabel = '';

  // Computed
  step1Complete = computed(() => this.selectedIds().size > 0);
  step2Complete = computed(() => this.batchId() !== null);
  canExport = computed(() => this.batchStatus() === 'approved');
  canMarkSent = computed(() => this.batchStatus() === 'approved' && this.exported());
  canSettle = computed(() => this.batchStatus() === 'sent_to_bank');

  runningTotal = computed(() => {
    const ids = this.selectedIds();
    const total = this.bills()
      .filter(b => ids.has(b.id))
      .reduce((sum, b) => sum + Number(b.amount), 0);
    return total.toFixed(2);
  });

  ngOnInit(): void {
    this.loadBills();
    this.loadActiveEngagements();
  }

  loadBills(): void {
    this.loadingBills.set(true);
    this.billsError.set(false);
    this.svc.getBills('approved').subscribe({
      next: bills => {
        this.bills.set(bills);
        this.loadingBills.set(false);
      },
      error: () => {
        this.billsError.set(true);
        this.loadingBills.set(false);
      },
    });
  }

  isSelected(id: string): boolean {
    return this.selectedIds().has(id);
  }

  toggleBill(id: string): void {
    const ids = new Set(this.selectedIds());
    if (ids.has(id)) {
      ids.delete(id);
    } else {
      ids.add(id);
    }
    this.selectedIds.set(ids);
  }

  selectAll(): void {
    this.selectedIds.set(new Set(this.bills().map(b => b.id)));
  }

  deselectAll(): void {
    this.selectedIds.set(new Set());
  }

  createBatch(stepper: { selectedIndex: number }): void {
    if (this.creatingBatch()) return;
    this.creatingBatch.set(true);
    this.batchError.set(false);
    const ids = [...this.selectedIds()];
    this.svc.createBatch(ids, this.payDate || undefined, this.bankLabel).subscribe({
      next: batch => {
        this.batchId.set(batch.id);
        this.batchStatus.set(batch.status ?? 'draft');
        this.exported.set(false);
        this.exportLabel.set(null);
        this.settlement.set(null);
        this.creatingBatch.set(false);
        setTimeout(() => {
          stepper.selectedIndex = 2;
        });
      },
      error: () => {
        this.batchError.set(true);
        this.creatingBatch.set(false);
      },
    });
  }

  approveBatch(): void {
    const id = this.batchId();
    if (!id || this.approvingBatch()) return;
    this.approvingBatch.set(true);
    this.approveError.set(false);
    this.svc.approveBatch(id).subscribe({
      next: batch => {
        this.batchStatus.set(batch.status ?? 'approved');
        this.approvingBatch.set(false);
      },
      error: () => {
        this.approveError.set(true);
        this.approvingBatch.set(false);
      },
    });
  }

  downloadNacha(): void {
    const id = this.batchId();
    if (!id || this.downloading()) return;
    this.downloading.set(true);
    this.svc.exportBatch(id, 'nacha').subscribe({
      next: blob => {
        this.downloadFile(blob, 'batch.txt');
        this.exported.set(true);
        this.exportLabel.set('NACHA export downloaded and recorded.');
        this.exportError.set(false);
        this.downloading.set(false);
      },
      error: () => {
        this.exportError.set(true);
        this.downloading.set(false);
      },
    });
  }

  downloadCsv(): void {
    const id = this.batchId();
    if (!id || this.downloading()) return;
    this.downloading.set(true);
    this.svc.exportBatch(id, 'csv').subscribe({
      next: blob => {
        this.downloadFile(blob, 'batch.csv');
        this.exported.set(true);
        this.exportLabel.set('CSV export downloaded and recorded.');
        this.exportError.set(false);
        this.downloading.set(false);
      },
      error: () => {
        this.exportError.set(true);
        this.downloading.set(false);
      },
    });
  }

  markSent(stepper: { selectedIndex: number }): void {
    const id = this.batchId();
    if (!id || this.markingSent()) return;
    this.markingSent.set(true);
    this.markSentError.set(false);
    this.svc.markSent(id).subscribe({
      next: batch => {
        this.batchStatus.set(batch.status ?? 'sent_to_bank');
        this.markingSent.set(false);
        setTimeout(() => {
          stepper.selectedIndex = 3;
        });
      },
      error: () => {
        this.markSentError.set(true);
        this.markingSent.set(false);
      },
    });
  }

  settleBatch(): void {
    const id = this.batchId();
    if (!id || this.settlingBatch()) return;
    this.settlingBatch.set(true);
    this.settleError.set(false);
    this.svc.settleBatch(id).subscribe({
      next: result => {
        this.settlement.set(result);
        this.batchStatus.set(result.status);
        this.settlingBatch.set(false);
      },
      error: () => {
        this.settleError.set(true);
        this.settlingBatch.set(false);
      },
    });
  }

  batchStatusLabel(): string {
    if (!this.batchId()) return 'Create a batch first';
    const labels: Record<string, string> = {
      draft: 'Draft - approval required',
      approved: 'Approved - ready to export',
      sent_to_bank: 'Sent to bank',
      settled: 'Settled',
    };
    return labels[this.batchStatus() ?? 'draft'] ?? (this.batchStatus() ?? 'Draft');
  }

  // ── Run Billing methods (#239) ─────────────────────────────────────────

  loadActiveEngagements(): void {
    this.loadingEngagements.set(true);
    this.engagementService.getEngagements({ status: 'active' }).subscribe({
      next: engs => {
        this.activeEngagements.set(engs);
        this.loadingEngagements.set(false);
      },
      error: () => {
        this.activeEngagements.set([]);
        this.loadingEngagements.set(false);
      },
    });
  }

  runBilling(): void {
    const engId = this.selectedEngagementId;
    if (!engId || this.runningBilling()) return;
    this.runningBilling.set(true);
    this.billingRunError.set(null);

    const engagement = this.activeEngagements().find(e => e.id === engId);
    const engName = engagement?.name ?? 'Engagement';

    // Draft an invoice for the selected engagement — the same POST endpoint used
    // by the invoice drawer on the engagement detail page.
    this.http.post<{ id: string }>('/api/v1/invoices/draft', { engagement_id: engId }).subscribe({
      next: () => {
        this.runningBilling.set(false);
        this.selectedEngagementId = '';
        this.snackBar.open(
          `Invoice drafted for ${engName} — view in Invoices`,
          'View',
          { duration: 6000, panelClass: ['snack-success'] },
        ).onAction().subscribe(() => {
          this.router.navigate(['/app/invoices']);
        });
      },
      error: (err: { status?: number; error?: { detail?: string } }) => {
        this.runningBilling.set(false);
        const detail = err?.error?.detail;
        this.billingRunError.set(
          typeof detail === 'string'
            ? detail
            : 'Could not initiate billing run. Please try again or use Draft Invoice on the engagement page.',
        );
      },
    });
  }

  private downloadFile(blob: Blob, name: string): void {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = name;
    a.click();
    URL.revokeObjectURL(url);
  }
}
