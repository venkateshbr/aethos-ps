import { Component, inject, signal, OnInit } from '@angular/core';
import { TitleCasePipe } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatTableModule } from '@angular/material/table';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';

import { ExpensesService, Expense } from '../../core/services/expenses.service';
import { EngagementService, ProjectSummary } from '../../core/services/engagement.service';
import { MoneyPipe } from '../../shared/pipes/money.pipe';
import { EmptyStateComponent } from '../../shared/components/empty-state.component';
import { SkeletonRowsComponent } from '../../shared/components/skeleton-rows.component';
import { SourceDocumentLinkComponent } from '../../shared/components/source-document-link.component';

@Component({
  selector: 'app-expenses-list',
  standalone: true,
  imports: [
    TitleCasePipe,
    ReactiveFormsModule,
    MatTableModule,
    MatIconModule,
    MatButtonModule,
    MoneyPipe,
    EmptyStateComponent,
    SkeletonRowsComponent,
    SourceDocumentLinkComponent,
  ],
  template: `
    <div class="p-6 bg-surface-base min-h-full">
      <!-- Page header -->
      <div class="mb-6 flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-text-primary">Expenses</h1>
          <p class="text-sm text-text-muted mt-1">Track and review project expenses.</p>
        </div>
        <button
          type="button"
          class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          aria-label="Log new expense"
          (click)="openCreateForm()"
        >
          <mat-icon class="text-base leading-none">add</mat-icon>
          Log expense
        </button>
      </div>

      <!-- Loading skeleton -->
      @if (loading()) {
        <app-skeleton-rows [count]="4" ariaLabel="Loading expenses" />
      }

      <!-- Error state -->
      @if (error() && !loading()) {
        <div class="rounded-lg border border-confidence-low/30 bg-confidence-low/10 px-4 py-3 text-sm text-confidence-low" role="alert">
          <mat-icon class="text-base align-middle mr-1">error_outline</mat-icon>
          Something went wrong loading expenses. Please try again.
        </div>
      }

      <!-- Empty state (also shown when endpoint returns 404 — handled as empty) -->
      @if (!loading() && !error() && expenses().length === 0) {
        <app-empty-state
          icon="receipt_long"
          heading="No expenses yet"
          message="Expenses logged by the agent or entered manually will appear here."
        />
      }

      <!-- Table -->
      @if (!loading() && !error() && expenses().length > 0) {
        <div class="rounded-lg overflow-hidden border border-border-default">
          <table
            mat-table
            [dataSource]="expenses()"
            class="w-full bg-surface-base"
            aria-label="Expenses"
          >
            <!-- Date column -->
            <ng-container matColumnDef="date">
              <th mat-header-cell *matHeaderCellDef
                  class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Date
              </th>
              <td mat-cell *matCellDef="let row"
                  class="text-text-secondary text-sm px-4 py-3 border-b border-border-subtle tabular-nums">
                {{ row.date }}
              </td>
            </ng-container>

            <!-- Vendor column -->
            <ng-container matColumnDef="vendor">
              <th mat-header-cell *matHeaderCellDef
                  class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Vendor
              </th>
              <td mat-cell *matCellDef="let row"
                  class="text-text-primary text-sm font-medium px-4 py-3 border-b border-border-subtle">
                {{ row.vendor }}
              </td>
            </ng-container>

            <!-- Amount column -->
            <ng-container matColumnDef="amount">
              <th mat-header-cell *matHeaderCellDef
                  class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3 text-right">
                Amount
              </th>
              <td mat-cell *matCellDef="let row"
                  class="text-text-primary text-sm font-mono px-4 py-3 border-b border-border-subtle text-right tabular-nums">
                {{ row.amount | money: row.currency }}
              </td>
            </ng-container>

            <!-- Category column -->
            <ng-container matColumnDef="category">
              <th mat-header-cell *matHeaderCellDef
                  class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Category
              </th>
              <td mat-cell *matCellDef="let row"
                  class="text-text-secondary text-sm px-4 py-3 border-b border-border-subtle">
                {{ row.category | titlecase }}
              </td>
            </ng-container>

            <!-- Billable column -->
            <ng-container matColumnDef="billable">
              <th mat-header-cell *matHeaderCellDef
                  class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Billable
              </th>
              <td mat-cell *matCellDef="let row" class="px-4 py-3 border-b border-border-subtle">
                <span
                  class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium"
                  [class]="row.billable ? 'bg-accent/15 text-accent-light' : 'bg-surface text-text-muted'"
                  [attr.aria-label]="row.billable ? 'Billable' : 'Non-billable'"
                >
                  <mat-icon class="text-xs leading-none" style="font-size:12px;width:12px;height:12px;">
                    {{ row.billable ? 'check' : 'remove' }}
                  </mat-icon>
                  {{ row.billable ? 'Yes' : 'No' }}
                </span>
              </td>
            </ng-container>

            <!-- Receipt / source-document column (#127) -->
            <ng-container matColumnDef="receipt">
              <th mat-header-cell *matHeaderCellDef
                  class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Receipt
              </th>
              <td mat-cell *matCellDef="let row"
                  class="px-4 py-3 border-b border-border-subtle">
                @if (row.document_id) {
                  <app-source-document-link
                    [documentId]="row.document_id"
                    label="View"
                  />
                } @else {
                  <span class="text-xs text-text-disabled" aria-hidden="true">—</span>
                }
              </td>
            </ng-container>

            <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
            <tr mat-row *matRowDef="let row; columns: displayedColumns"
                class="hover:bg-surface-raised transition-colors"></tr>
          </table>
        </div>

        <p class="text-xs text-text-disabled mt-3 text-right">
          {{ expenses().length }} {{ expenses().length === 1 ? 'expense' : 'expenses' }}
        </p>
      }
    </div>

    <!-- Create expense slide-in panel -->
    @if (showCreateForm()) {
      <div class="fixed inset-0 bg-black/50 z-40" (click)="closeCreateForm()" aria-hidden="true"></div>
      <aside class="fixed right-0 top-0 h-full w-full max-w-md bg-surface border-l border-border-default z-50 flex flex-col shadow-2xl"
        role="dialog" aria-modal="true" aria-labelledby="create-expense-title">
        <div class="flex items-center justify-between px-6 py-4 border-b border-border-default flex-none">
          <h2 id="create-expense-title" class="text-base font-semibold text-text-primary">Log expense</h2>
          <button class="text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded" (click)="closeCreateForm()" aria-label="Close panel">
            <mat-icon>close</mat-icon>
          </button>
        </div>
        <form [formGroup]="createForm" (ngSubmit)="submitCreate()" class="flex-1 overflow-y-auto px-6 py-5 space-y-5" novalidate>
          <!-- Project -->
          <div>
            <label for="exp-project" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Project</label>
            <select id="exp-project" formControlName="project_id"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm">
              <option value="">No project (general)</option>
              @for (p of availableProjects(); track p.id) {
                <option [value]="p.id">{{ p.name }}</option>
              }
            </select>
          </div>
          <!-- Description -->
          <div>
            <label for="exp-desc" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Description *</label>
            <input id="exp-desc" type="text" formControlName="description"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
              placeholder="e.g. Client dinner — Acme Q3 kickoff" />
            @if (createForm.controls.description.touched && createForm.controls.description.errors) {
              <p class="text-xs text-confidence-low mt-1">Description is required.</p>
            }
          </div>
          <!-- Date -->
          <div>
            <label for="exp-date" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Date *</label>
            <input id="exp-date" type="date" formControlName="expense_date"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm" />
            @if (createForm.controls.expense_date.touched && createForm.controls.expense_date.errors) {
              <p class="text-xs text-confidence-low mt-1">Date is required.</p>
            }
          </div>
          <!-- Amount + Currency (side by side) -->
          <div class="flex gap-3">
            <div class="flex-1">
              <label for="exp-amount" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Amount *</label>
              <input id="exp-amount" type="text" formControlName="amount"
                class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm font-mono"
                placeholder="0.00" />
              @if (createForm.controls.amount.touched && createForm.controls.amount.errors) {
                <p class="text-xs text-confidence-low mt-1">Amount is required.</p>
              }
            </div>
            <div class="w-28">
              <label for="exp-currency" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Currency</label>
              <select id="exp-currency" formControlName="currency"
                class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm">
                <option value="USD">USD</option>
                <option value="GBP">GBP</option>
                <option value="SGD">SGD</option>
                <option value="INR">INR</option>
                <option value="AUD">AUD</option>
              </select>
            </div>
          </div>
          <!-- Category -->
          <div>
            <label for="exp-category" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Category *</label>
            <select id="exp-category" formControlName="category"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm">
              <option value="">Select…</option>
              <option value="travel">Travel</option>
              <option value="meals">Meals &amp; Entertainment</option>
              <option value="software">Software</option>
              <option value="hardware">Hardware</option>
              <option value="office">Office supplies</option>
              <option value="professional">Professional services</option>
              <option value="other">Other</option>
            </select>
            @if (createForm.controls.category.touched && createForm.controls.category.errors) {
              <p class="text-xs text-confidence-low mt-1">Category is required.</p>
            }
          </div>
          @if (createError()) {
            <div role="alert" class="text-sm text-confidence-low bg-confidence-low/10 border border-confidence-low/30 rounded px-3 py-2">{{ createError() }}</div>
          }
        </form>
        <div class="flex-none px-6 py-4 border-t border-border-default flex items-center justify-end gap-3">
          <button type="button" class="px-4 py-2 text-sm text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded" (click)="closeCreateForm()">Cancel</button>
          <button type="button"
            class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            [disabled]="createForm.invalid || creating()" (click)="submitCreate()">
            @if (creating()) { Saving… } @else { Log expense }
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
export class ExpensesListComponent implements OnInit {
  private expensesService = inject(ExpensesService);
  private engagementService = inject(EngagementService);
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);

  loading  = signal(true);
  error    = signal<string | null>(null);
  expenses = signal<Expense[]>([]);

  // Create form state
  showCreateForm = signal(false);
  creating = signal(false);
  createError = signal<string | null>(null);
  availableProjects = signal<ProjectSummary[]>([]);
  createForm = this.fb.nonNullable.group({
    project_id:   [''],
    description:  ['', [Validators.required]],
    expense_date: ['', [Validators.required]],
    amount:       ['', [Validators.required]],
    currency:     ['USD'],
    category:     ['', [Validators.required]],
  });

  displayedColumns = ['date', 'vendor', 'amount', 'category', 'billable', 'receipt'];

  ngOnInit(): void {
    this.expensesService.getExpenses().subscribe({
      next: (res) => {
        this.expenses.set(res);
        this.loading.set(false);
      },
      error: (e: { status?: number }) => {
        if (e.status === 404) {
          // Endpoint not yet implemented — treat as empty gracefully
          this.expenses.set([]);
        } else {
          this.error.set('Failed to load');
        }
        this.loading.set(false);
      },
    });
  }

  openCreateForm(): void {
    const today = new Date().toISOString().split('T')[0];
    this.createForm.reset({ project_id: '', description: '', expense_date: today, amount: '', currency: 'USD', category: '' });
    this.createError.set(null);
    // Load projects for the dropdown
    this.engagementService.getProjects().subscribe({
      next: (list) => this.availableProjects.set(list),
      error: () => this.availableProjects.set([]),
    });
    this.showCreateForm.set(true);
  }

  closeCreateForm(): void {
    this.showCreateForm.set(false);
  }

  submitCreate(): void {
    if (this.createForm.invalid) {
      this.createForm.markAllAsTouched();
      return;
    }
    this.creating.set(true);
    this.createError.set(null);
    const v = this.createForm.getRawValue();
    const projectId = v.project_id || null;
    const endpoint = projectId
      ? `/api/v1/projects/${projectId}/expenses`
      : '/api/v1/expenses';
    this.http.post<Expense>(endpoint, {
      description:  v.description,
      amount:       v.amount,
      currency:     v.currency,
      category:     v.category,
      expense_date: v.expense_date,
      billable:     true,
    }).subscribe({
      next: (newExp) => {
        this.expenses.update(list => [newExp, ...list]);
        this.creating.set(false);
        this.closeCreateForm();
      },
      error: (err: { error?: { detail?: string } }) => {
        this.creating.set(false);
        const detail = err?.error?.detail;
        this.createError.set(
          typeof detail === 'string' ? detail : 'Could not log expense. Please try again.'
        );
      },
    });
  }
}
