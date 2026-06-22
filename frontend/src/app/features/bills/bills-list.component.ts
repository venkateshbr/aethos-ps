import { Component, inject, signal, OnInit } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { FormBuilder, ReactiveFormsModule, Validators, FormArray, FormGroup } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

import { MoneyPipe } from '../../shared/pipes/money.pipe';
import { SkeletonRowsComponent } from '../../shared/components/skeleton-rows.component';
import { EmptyStateComponent } from '../../shared/components/empty-state.component';
import { userMessageForError } from '../../core/utils/error-message';

export interface VendorOption {
  id: string;
  name: string;
}

export interface BillSummary {
  id: string;
  bill_number: string;
  /** Contact / vendor name. May be absent on legacy records. */
  vendor_name?: string | null;
  /** Raw vendor contact ID for linking to /contacts/:id */
  vendor_id?: string | null;
  client_id?: string | null;
  issue_date: string | null;
  due_date: string | null;
  amount: string;
  total?: string;       // API field name alias
  subtotal?: string;
  currency: string;
  status: string;
  source_document_id?: string | null;
  confidence?: string | number | null;
}

type StatusFilter = 'all' | 'draft' | 'approved' | 'paid' | 'overdue';

@Component({
  selector: 'app-bills-list',
  standalone: true,
  imports: [
    RouterLink,
    ReactiveFormsModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    MoneyPipe,
    SkeletonRowsComponent,
    EmptyStateComponent,
  ],
  template: `
    <div class="p-6 bg-surface-base min-h-full">

      <!-- ── Page header ──────────────────────────────────────────────── -->
      <div class="mb-6 flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-text-primary">Bills</h1>
          <p class="text-sm text-text-muted mt-1">Manage vendor bills and accounts payable.</p>
        </div>
        <div class="flex items-center gap-2">
          <button
            type="button"
            (click)="openNewBillForm()"
            class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            aria-label="Create new bill"
          >
            <mat-icon class="text-base leading-none" style="font-size:1rem;width:1rem;height:1rem;">add</mat-icon>
            New Bill
          </button>
          <button
            type="button"
            routerLink="/app/billing-runs"
            class="inline-flex items-center gap-2 bg-indigo-700 hover:bg-indigo-600 text-white font-medium px-4 py-2 rounded text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-400"
            aria-label="Go to Pay Bills wizard"
          >
            <mat-icon class="text-base leading-none" style="font-size:1rem;width:1rem;height:1rem;">payments</mat-icon>
            Pay Bills
          </button>
        </div>
      </div>

      <!-- ── Status filter chips ──────────────────────────────────────── -->
      <div class="flex flex-wrap gap-2 mb-6" role="group" aria-label="Filter bills by status">
        @for (chip of filterChips; track chip.value) {
          <button
            type="button"
            (click)="setFilter(chip.value)"
            class="px-3 py-1 rounded-full text-xs font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            [class]="activeFilter() === chip.value
              ? 'bg-indigo-700 text-white'
              : 'bg-surface-raised text-text-muted hover:bg-surface hover:text-text-secondary border border-border-default'"
            [attr.aria-pressed]="activeFilter() === chip.value"
          >
            {{ chip.label }}
          </button>
        }
      </div>

      <!-- ── Loading skeleton ─────────────────────────────────────────── -->
      @if (loading()) {
        <app-skeleton-rows [count]="5" ariaLabel="Loading bills" />
      }

      <!-- ── Error state ──────────────────────────────────────────────── -->
      @if (error() && !loading()) {
        <div class="rounded-lg border border-confidence-low/30 bg-confidence-low/10 px-4 py-4 flex items-center justify-between"
             role="alert">
          <div class="flex items-center gap-2 text-sm text-confidence-low">
            <mat-icon class="text-base flex-none">error_outline</mat-icon>
            {{ error() }}
          </div>
          <button
            type="button"
            (click)="loadBills()"
            class="px-3 py-1.5 text-xs font-medium rounded bg-surface-raised hover:bg-surface text-text-secondary transition-colors border border-border-default focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-400"
          >
            Retry
          </button>
        </div>
      }

      <!-- ── Empty state ──────────────────────────────────────────────── -->
      @if (!loading() && !error() && bills().length === 0) {
        <app-empty-state
          icon="upload_file"
          heading="No bills yet"
          message="Drop a vendor invoice in Copilot to get started — AI will extract the details automatically."
        />
      }

      <!-- ── Bills table ──────────────────────────────────────────────── -->
      @if (!loading() && !error() && bills().length > 0) {
        <div class="rounded-lg overflow-hidden border border-border-default">
          <table
            mat-table
            [dataSource]="bills()"
            class="w-full bg-surface-base"
            aria-label="Bills"
          >
            <!-- Bill number -->
            <ng-container matColumnDef="bill_number">
              <th mat-header-cell *matHeaderCellDef
                  class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Bill #
              </th>
              <td mat-cell *matCellDef="let row"
                  class="text-text-primary text-sm font-mono font-medium px-4 py-3 border-b border-border-subtle">
                {{ row.bill_number }}
              </td>
            </ng-container>

            <!-- Vendor -->
            <ng-container matColumnDef="vendor_name">
              <th mat-header-cell *matHeaderCellDef
                  class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Vendor
              </th>
              <td mat-cell *matCellDef="let row"
                  class="text-sm px-4 py-3 border-b border-border-subtle">
                @if (row.vendor_id) {
                  <a
                    [routerLink]="['/app/clients', row.vendor_id]"
                    class="text-indigo-400 hover:text-indigo-300 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-400 rounded"
                    (click)="$event.stopPropagation()"
                    [attr.aria-label]="'View vendor ' + (row.vendor_name || row.vendor_id)"
                  >
                    {{ row.vendor_name || row.vendor_id }}
                  </a>
                } @else {
                  <span class="text-text-muted">{{ row.vendor_name || '—' }}</span>
                }
              </td>
            </ng-container>

            <!-- Issue date -->
            <ng-container matColumnDef="issue_date">
              <th mat-header-cell *matHeaderCellDef
                  class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Issued
              </th>
              <td mat-cell *matCellDef="let row"
                  class="text-text-secondary text-sm px-4 py-3 border-b border-border-subtle tabular-nums">
                {{ row.issue_date ?? '—' }}
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
                {{ row.due_date ?? '—' }}
              </td>
            </ng-container>

            <!-- Amount -->
            <ng-container matColumnDef="amount">
              <th mat-header-cell *matHeaderCellDef
                  class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3 text-right">
                Amount
              </th>
              <td mat-cell *matCellDef="let row"
                  class="text-text-primary text-sm font-mono font-medium px-4 py-3 border-b border-border-subtle text-right tabular-nums">
                {{ row.amount | money: row.currency }}
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

            <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
            <tr mat-row *matRowDef="let row; columns: displayedColumns"
                class="hover:bg-surface-raised transition-colors cursor-pointer"
                (click)="viewBill(row)"
                [attr.aria-label]="'View bill ' + row.bill_number"
                tabindex="0"
                (keydown.enter)="viewBill(row)"
            ></tr>
          </table>
        </div>

        <p class="text-xs text-text-disabled mt-3 text-right">
          {{ bills().length }} {{ bills().length === 1 ? 'bill' : 'bills' }}
        </p>
      }

    </div>

    <!-- ── New Bill slide-in panel ─────────────────────────────────── -->
    @if (showNewBillForm()) {
      <div
        class="fixed inset-0 bg-black/50 z-40"
        (click)="closeNewBillForm()"
        aria-hidden="true"
      ></div>
      <aside
        class="fixed right-0 top-0 h-full w-full max-w-xl bg-surface border-l border-border-default z-50 flex flex-col shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="new-bill-title"
      >
        <!-- Panel header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-border-default flex-none">
          <h2 id="new-bill-title" class="text-base font-semibold text-text-primary">New Bill</h2>
          <button
            class="text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
            (click)="closeNewBillForm()"
            aria-label="Close panel"
          >
            <mat-icon>close</mat-icon>
          </button>
        </div>

        <!-- Form body -->
        <form
          [formGroup]="newBillForm"
          (ngSubmit)="submitNewBill()"
          class="flex-1 overflow-y-auto px-6 py-5 space-y-5"
          novalidate
        >

          <!-- Vendor picker -->
          <div>
            <label for="bill-vendor" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
              Vendor <span class="text-confidence-low" aria-hidden="true">*</span>
            </label>
            @if (vendorsLoading()) {
              <div class="w-full h-9 bg-surface-raised rounded animate-pulse"></div>
            } @else {
              <select
                id="bill-vendor"
                formControlName="client_id"
                class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
              >
                <option value="">Select vendor…</option>
                @for (v of vendors(); track v.id) {
                  <option [value]="v.id">{{ v.name }}</option>
                }
              </select>
            }
            @if (newBillForm.controls.client_id.touched && newBillForm.controls.client_id.errors) {
              <p class="text-xs text-confidence-low mt-1">Vendor is required.</p>
            }
          </div>

          <!-- Vendor invoice number -->
          <div>
            <label for="bill-inv-num" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
              Vendor Invoice #
            </label>
            <input
              id="bill-inv-num"
              type="text"
              formControlName="vendor_invoice_number"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
              placeholder="e.g. INV-2025-0042"
            />
          </div>

          <!-- Dates + Currency row -->
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="bill-issue-date" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
                Issue Date
              </label>
              <input
                id="bill-issue-date"
                type="date"
                formControlName="issue_date"
                class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
              />
            </div>
            <div>
              <label for="bill-due-date" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
                Due Date
              </label>
              <input
                id="bill-due-date"
                type="date"
                formControlName="due_date"
                class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
              />
            </div>
          </div>

          <!-- Currency -->
          <div>
            <label for="bill-currency" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
              Currency
            </label>
            <select
              id="bill-currency"
              formControlName="currency"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
            >
              <option value="USD">USD</option>
              <option value="GBP">GBP</option>
              <option value="SGD">SGD</option>
              <option value="INR">INR</option>
              <option value="AUD">AUD</option>
            </select>
          </div>

          <!-- Notes -->
          <div>
            <label for="bill-notes" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
              Notes
            </label>
            <textarea
              id="bill-notes"
              formControlName="notes"
              rows="2"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm resize-none"
              placeholder="Optional notes about this bill"
            ></textarea>
          </div>

          <!-- ── Line items ─────────────────────────────────────────── -->
          <div>
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs uppercase tracking-wide text-text-muted font-medium">Line Items</span>
              <button
                type="button"
                (click)="addLine()"
                class="inline-flex items-center gap-1 text-xs text-accent-light hover:text-accent transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
                aria-label="Add line item"
              >
                <mat-icon class="text-sm leading-none" style="font-size:14px;width:14px;height:14px;">add_circle_outline</mat-icon>
                Add line
              </button>
            </div>

            @if (lines.length === 0) {
              <p class="text-xs text-text-disabled py-3 text-center border border-dashed border-border-default rounded">
                No lines yet — add at least one.
              </p>
            }

            <div formArrayName="lines" class="space-y-3">
              @for (line of lines.controls; track $index; let i = $index) {
                <div [formGroupName]="i" class="bg-surface-raised border border-border-default rounded-lg p-3 space-y-2">
                  <!-- Description -->
                  <div>
                    <label [for]="'line-desc-' + i" class="block text-xs text-text-muted mb-1">Description *</label>
                    <input
                      [id]="'line-desc-' + i"
                      type="text"
                      formControlName="description"
                      class="w-full px-3 py-1.5 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
                      placeholder="e.g. Subcontractor services — May"
                    />
                    @if (lineAt(i).get('description')?.touched && lineAt(i).get('description')?.errors) {
                      <p class="text-xs text-confidence-low mt-0.5">Description is required.</p>
                    }
                  </div>
                  <!-- Qty / Unit Price / Tax Amount -->
                  <div class="grid grid-cols-3 gap-2">
                    <div>
                      <label [for]="'line-qty-' + i" class="block text-xs text-text-muted mb-1">Qty</label>
                      <input
                        [id]="'line-qty-' + i"
                        type="number"
                        formControlName="quantity"
                        min="0.001"
                        step="any"
                        class="w-full px-2 py-1.5 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm font-mono"
                        (input)="recalcLine(i)"
                      />
                    </div>
                    <div>
                      <label [for]="'line-price-' + i" class="block text-xs text-text-muted mb-1">Unit Price</label>
                      <input
                        [id]="'line-price-' + i"
                        type="number"
                        formControlName="unit_price"
                        min="0"
                        step="any"
                        class="w-full px-2 py-1.5 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm font-mono"
                        (input)="recalcLine(i)"
                      />
                    </div>
                    <div>
                      <label [for]="'line-tax-' + i" class="block text-xs text-text-muted mb-1">Tax Amt</label>
                      <input
                        [id]="'line-tax-' + i"
                        type="number"
                        formControlName="tax_amount"
                        min="0"
                        step="any"
                        class="w-full px-2 py-1.5 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm font-mono"
                      />
                    </div>
                  </div>
                  <!-- Line amount display + remove -->
                  <div class="flex items-center justify-between pt-1">
                    <span class="text-xs text-text-muted">
                      Line total:
                      <span class="font-mono text-text-primary ml-1">
                        {{ lineAmount(i) | money: newBillForm.controls.currency.value }}
                      </span>
                    </span>
                    @if (lines.length > 1) {
                      <button
                        type="button"
                        (click)="removeLine(i)"
                        class="text-text-disabled hover:text-confidence-low transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-confidence-low rounded"
                        [attr.aria-label]="'Remove line ' + (i + 1)"
                      >
                        <mat-icon class="text-base leading-none" style="font-size:1rem;width:1rem;height:1rem;">remove_circle_outline</mat-icon>
                      </button>
                    }
                  </div>
                </div>
              }
            </div>

            <!-- Totals summary -->
            @if (lines.length > 0) {
              <div class="mt-3 border-t border-border-default pt-3 flex flex-col items-end gap-1">
                <div class="flex justify-between w-48 text-sm">
                  <span class="text-text-muted">Subtotal</span>
                  <span class="font-mono text-text-primary tabular-nums">{{ formSubtotal() | money: newBillForm.controls.currency.value }}</span>
                </div>
                <div class="flex justify-between w-48 text-sm">
                  <span class="text-text-muted">Tax</span>
                  <span class="font-mono text-text-primary tabular-nums">{{ formTaxTotal() | money: newBillForm.controls.currency.value }}</span>
                </div>
                <div class="flex justify-between w-48 text-base font-bold border-t border-border-default pt-1 mt-1">
                  <span class="text-text-primary">Total</span>
                  <span class="font-mono text-text-primary tabular-nums">{{ formTotal() | money: newBillForm.controls.currency.value }}</span>
                </div>
              </div>
            }
          </div>

          <!-- Error banner -->
          @if (createError()) {
            <div
              role="alert"
              class="text-sm text-confidence-low bg-confidence-low/10 border border-confidence-low/30 rounded px-3 py-2"
            >{{ createError() }}</div>
          }

        </form>

        <!-- Panel footer -->
        <div class="flex-none px-6 py-4 border-t border-border-default flex items-center justify-end gap-3">
          <button
            type="button"
            class="px-4 py-2 text-sm text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
            (click)="closeNewBillForm()"
          >
            Cancel
          </button>
          <button
            type="button"
            class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            [disabled]="newBillForm.invalid || creating() || lines.length === 0"
            (click)="submitNewBill()"
          >
            @if (creating()) { Saving… } @else { Create Bill }
          </button>
        </div>
      </aside>
    }
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
export class BillsListComponent implements OnInit {
  private http   = inject(HttpClient);
  private router = inject(Router);
  private fb     = inject(FormBuilder);

  loading     = signal(true);
  error       = signal<string | null>(null);
  bills       = signal<BillSummary[]>([]);
  activeFilter = signal<StatusFilter>('all');

  // ── New Bill form state ───────────────────────────────────────────────
  showNewBillForm = signal(false);
  creating        = signal(false);
  createError     = signal<string | null>(null);
  vendors         = signal<VendorOption[]>([]);
  vendorsLoading  = signal(false);

  newBillForm = this.fb.nonNullable.group({
    client_id:             ['', [Validators.required]],
    vendor_invoice_number: [''],
    issue_date:            [''],
    due_date:              [''],
    currency:              ['USD'],
    notes:                 [''],
    lines: this.fb.array([this.buildLine()]),
  });

  readonly displayedColumns = ['bill_number', 'vendor_name', 'issue_date', 'due_date', 'amount', 'status'];

  readonly filterChips: { label: string; value: StatusFilter }[] = [
    { label: 'All',      value: 'all' },
    { label: 'Draft',    value: 'draft' },
    { label: 'Approved', value: 'approved' },
    { label: 'Paid',     value: 'paid' },
    { label: 'Overdue',  value: 'overdue' },
  ];

  // ── Lifecycle ─────────────────────────────────────────────────────────

  ngOnInit(): void {
    this.loadBills();
  }

  // ── List ──────────────────────────────────────────────────────────────

  setFilter(filter: StatusFilter): void {
    if (this.activeFilter() === filter) return;
    this.activeFilter.set(filter);
    this.loadBills();
  }

  loadBills(): void {
    this.loading.set(true);
    this.error.set(null);
    const filter = this.activeFilter();
    const url = filter === 'all'
      ? '/api/v1/bills'
      : `/api/v1/bills?status=${filter}`;

    this.http.get<BillSummary[] | { items: BillSummary[]; total: number }>(url).subscribe({
      next: (res) => {
        // API may return either a flat array or {items, total}
        const raw = Array.isArray(res) ? res : ((res as any).items ?? []);
        // Normalise field names: API uses 'total', interface uses 'amount'
        const bills = raw.map((b: any) => ({
          ...b,
          amount: b.amount ?? b.total ?? b.subtotal ?? '0.00',
          vendor_name: b.vendor_name ?? b.client_name ?? null,
          vendor_id: b.vendor_id ?? b.client_id ?? null,
        }));
        this.bills.set(bills);
        this.loading.set(false);
      },
      error: (err: unknown) => {
        this.error.set(userMessageForError(err, 'Bills'));
        this.loading.set(false);
      },
    });
  }

  viewBill(bill: BillSummary): void {
    this.router.navigate(['/app/bills', bill.id]);
  }

  // ── New Bill panel ────────────────────────────────────────────────────

  get lines(): FormArray {
    return this.newBillForm.get('lines') as FormArray;
  }

  lineAt(i: number): FormGroup {
    return this.lines.at(i) as FormGroup;
  }

  private buildLine(): FormGroup {
    return this.fb.group({
      description: ['', [Validators.required]],
      quantity:    [1],
      unit_price:  [0],
      tax_amount:  [0],
      amount:      [{ value: 0, disabled: true }],
    });
  }

  openNewBillForm(): void {
    // Reset form to defaults
    while (this.lines.length > 1) this.lines.removeAt(1);
    this.newBillForm.reset({
      client_id: '',
      vendor_invoice_number: '',
      issue_date: '',
      due_date: '',
      currency: 'USD',
      notes: '',
    });
    // Reset the first line
    this.lines.at(0).reset({ description: '', quantity: 1, unit_price: 0, tax_amount: 0, amount: 0 });
    this.createError.set(null);

    // Load vendors (kind=vendor or kind=both)
    this.vendorsLoading.set(true);
    this.http
      .get<{ items: Array<{ id: string; name: string; kind: string }>; total: number }>(
        '/api/v1/clients?kind=vendor'
      )
      .subscribe({
        next: (res) => {
          // Also fetch kind=both and merge
          const vendorItems = res.items ?? [];
          this.http
            .get<{ items: Array<{ id: string; name: string; kind: string }>; total: number }>(
              '/api/v1/clients?kind=both'
            )
            .subscribe({
              next: (res2) => {
                const bothItems = res2.items ?? [];
                const merged = [...vendorItems, ...bothItems].map((c) => ({
                  id: c.id,
                  name: c.name,
                }));
                // Deduplicate (in case API returns overlapping results)
                const seen = new Set<string>();
                const deduped = merged.filter((v) => {
                  if (seen.has(v.id)) return false;
                  seen.add(v.id);
                  return true;
                });
                this.vendors.set(deduped.sort((a, b) => a.name.localeCompare(b.name)));
                this.vendorsLoading.set(false);
              },
              error: () => {
                this.vendors.set(vendorItems.map((c) => ({ id: c.id, name: c.name })));
                this.vendorsLoading.set(false);
              },
            });
        },
        error: () => {
          this.vendors.set([]);
          this.vendorsLoading.set(false);
        },
      });

    this.showNewBillForm.set(true);
  }

  closeNewBillForm(): void {
    this.showNewBillForm.set(false);
  }

  addLine(): void {
    this.lines.push(this.buildLine());
  }

  removeLine(i: number): void {
    if (this.lines.length <= 1) return;
    this.lines.removeAt(i);
  }

  recalcLine(i: number): void {
    const line = this.lineAt(i);
    const qty   = parseFloat(line.get('quantity')?.value ?? '0') || 0;
    const price = parseFloat(line.get('unit_price')?.value ?? '0') || 0;
    const amount = +(qty * price).toFixed(2);
    line.get('amount')?.setValue(amount, { emitEvent: false });
  }

  lineAmount(i: number): string {
    const line = this.lineAt(i);
    const qty   = parseFloat(line.get('quantity')?.value ?? '0') || 0;
    const price = parseFloat(line.get('unit_price')?.value ?? '0') || 0;
    return (qty * price).toFixed(2);
  }

  formSubtotal(): string {
    let total = 0;
    for (let i = 0; i < this.lines.length; i++) {
      const l = this.lineAt(i);
      const qty   = parseFloat(l.get('quantity')?.value ?? '0') || 0;
      const price = parseFloat(l.get('unit_price')?.value ?? '0') || 0;
      total += qty * price;
    }
    return total.toFixed(2);
  }

  formTaxTotal(): string {
    let total = 0;
    for (let i = 0; i < this.lines.length; i++) {
      const l = this.lineAt(i);
      total += parseFloat(l.get('tax_amount')?.value ?? '0') || 0;
    }
    return total.toFixed(2);
  }

  formTotal(): string {
    const sub = parseFloat(this.formSubtotal()) || 0;
    const tax = parseFloat(this.formTaxTotal()) || 0;
    return (sub + tax).toFixed(2);
  }

  submitNewBill(): void {
    if (this.newBillForm.invalid || this.creating() || this.lines.length === 0) {
      this.newBillForm.markAllAsTouched();
      return;
    }
    this.creating.set(true);
    this.createError.set(null);

    const v = this.newBillForm.getRawValue();
    const linesPayload = this.lines.controls.map((ctrl, i) => {
      const l = ctrl as FormGroup;
      const qty   = parseFloat(l.get('quantity')?.value ?? '1') || 1;
      const price = parseFloat(l.get('unit_price')?.value ?? '0') || 0;
      const amount = +(qty * price).toFixed(2);
      const tax    = +(parseFloat(l.get('tax_amount')?.value ?? '0') || 0).toFixed(2);
      return {
        description: l.get('description')?.value ?? '',
        quantity:    qty,
        unit_price:  price,
        amount,
        tax_amount:  tax,
      };
    });

    const payload: Record<string, unknown> = {
      client_id: v.client_id,
      currency:  v.currency || 'USD',
      lines:     linesPayload,
    };
    if (v.vendor_invoice_number?.trim()) payload['vendor_invoice_number'] = v.vendor_invoice_number.trim();
    if (v.issue_date) payload['issue_date'] = v.issue_date;
    if (v.due_date)   payload['due_date']   = v.due_date;
    if (v.notes?.trim()) payload['notes']   = v.notes.trim();

    this.http.post<BillSummary>('/api/v1/bills', payload).subscribe({
      next: (created) => {
        // Normalise returned bill for the list
        const normalised: BillSummary = {
          ...created,
          amount: (created as any).total ?? (created as any).subtotal ?? '0.00',
          vendor_name: (created as any).vendor_name ?? null,
          vendor_id:   (created as any).vendor_id   ?? (created as any).client_id ?? null,
        };
        this.bills.update((list) => [normalised, ...list]);
        this.creating.set(false);
        this.closeNewBillForm();
      },
      error: (err: { error?: { detail?: string } }) => {
        this.creating.set(false);
        const detail = (err as any)?.error?.detail;
        this.createError.set(
          typeof detail === 'string' ? detail : 'Could not create bill. Please try again.'
        );
      },
    });
  }

  // ── Status helpers ────────────────────────────────────────────────────

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
