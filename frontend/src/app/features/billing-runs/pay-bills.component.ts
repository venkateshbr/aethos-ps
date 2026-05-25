import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatStepperModule } from '@angular/material/stepper';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MoneyPipe } from '../../shared/pipes/money.pipe';
import { BillingRunsService, Bill } from '../../core/services/billing-runs.service';

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
    MoneyPipe,
  ],
  template: `
    <div class="min-h-full bg-surface-base p-6">
      <div class="max-w-3xl mx-auto">
        <h1 class="text-2xl font-semibold text-text-primary mb-6">Pay Bills</h1>

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
          <mat-stepper [linear]="true" orientation="horizontal" #stepper class="pay-bills-stepper bg-surface-raised rounded-xl border border-border-default p-6">

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
                <p class="text-sm text-text-secondary mb-1">Batch <span class="font-mono text-text-primary">{{ batchId() }}</span> created.</p>
                <p class="text-xs text-text-disabled mb-6">Download your payment file before marking as sent.</p>

                <div class="flex flex-col sm:flex-row gap-3 mb-8">
                  <button
                    [disabled]="downloading()"
                    (click)="downloadNacha()"
                    class="flex items-center justify-center gap-2 px-5 py-2.5 text-sm font-medium rounded-lg bg-surface hover:bg-surface-raised text-text-primary border border-border-strong hover:border-slate-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-400"
                  >
                    <mat-icon class="text-base" style="font-size:1.1rem;width:1.1rem;height:1.1rem;" aria-hidden="true">download</mat-icon>
                    Download NACHA
                  </button>

                  <button
                    [disabled]="downloading()"
                    (click)="downloadCsv()"
                    class="flex items-center justify-center gap-2 px-5 py-2.5 text-sm font-medium rounded-lg bg-surface hover:bg-surface-raised text-text-primary border border-border-strong hover:border-slate-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-400"
                  >
                    <mat-icon class="text-base" style="font-size:1.1rem;width:1.1rem;height:1.1rem;" aria-hidden="true">table_view</mat-icon>
                    Download CSV
                  </button>
                </div>

                <div class="border-t border-border-default pt-6">
                  <p class="text-xs text-text-muted mb-4">Once you have uploaded the file to your bank's portal, mark the batch as sent.</p>
                  <button
                    [disabled]="markingSent()"
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

            <!-- ── Step 4: Complete ───────────────────────────────────── -->
            <mat-step label="Complete">
              <div class="py-8 flex flex-col items-center text-center">
                <mat-icon
                  class="text-accent-light mb-4"
                  style="font-size:3rem;width:3rem;height:3rem;"
                  aria-hidden="true"
                >check_circle</mat-icon>
                <h2 class="text-xl font-semibold text-text-primary mb-2">Batch sent to bank</h2>
                <p class="text-sm text-text-muted mb-6">Payment batch <span class="font-mono text-text-primary">{{ batchId() }}</span> has been marked as sent.</p>
                <a
                  routerLink="/app/expenses"
                  class="text-sm text-indigo-400 hover:text-indigo-300 underline transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-400 rounded"
                >Back to bills</a>
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
export class PayBillsComponent {
  private svc = inject(BillingRunsService);

  // Loading states
  loadingBills = signal(true);
  billsError = signal(false);
  creatingBatch = signal(false);
  batchError = signal(false);
  downloading = signal(false);
  markingSent = signal(false);
  markSentError = signal(false);

  // Data
  bills = signal<Bill[]>([]);
  selectedIds = signal<Set<string>>(new Set());
  batchId = signal<string | null>(null);

  // Form values
  payDate = '';
  bankLabel = '';

  // Computed
  step1Complete = computed(() => this.selectedIds().size > 0);
  step2Complete = computed(() => this.batchId() !== null);

  runningTotal = computed(() => {
    const ids = this.selectedIds();
    const total = this.bills()
      .filter(b => ids.has(b.id))
      .reduce((sum, b) => sum + Number(b.amount), 0);
    return total.toFixed(2);
  });

  constructor() {
    this.loadBills();
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

  createBatch(stepper: { next: () => void }): void {
    if (this.creatingBatch()) return;
    this.creatingBatch.set(true);
    this.batchError.set(false);
    const ids = [...this.selectedIds()];
    this.svc.createBatch(ids, this.payDate || undefined, this.bankLabel).subscribe({
      next: batch => {
        this.batchId.set(batch.id);
        this.creatingBatch.set(false);
        stepper.next();
      },
      error: () => {
        this.batchError.set(true);
        this.creatingBatch.set(false);
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
        this.downloading.set(false);
      },
      error: () => {
        console.error('NACHA export failed');
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
        this.downloading.set(false);
      },
      error: () => {
        console.error('CSV export failed');
        this.downloading.set(false);
      },
    });
  }

  markSent(stepper: { next: () => void }): void {
    const id = this.batchId();
    if (!id || this.markingSent()) return;
    this.markingSent.set(true);
    this.markSentError.set(false);
    this.svc.markSent(id).subscribe({
      next: () => {
        this.markingSent.set(false);
        stepper.next();
      },
      error: () => {
        this.markSentError.set(true);
        this.markingSent.set(false);
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
