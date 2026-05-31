import { Component, inject, signal, OnInit } from '@angular/core';
import { TitleCasePipe } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatIconModule } from '@angular/material/icon';

import { ExpensesService, Expense } from '../../core/services/expenses.service';
import { MoneyPipe } from '../../shared/pipes/money.pipe';
import { EmptyStateComponent } from '../../shared/components/empty-state.component';
import { SkeletonRowsComponent } from '../../shared/components/skeleton-rows.component';
import { SourceDocumentLinkComponent } from '../../shared/components/source-document-link.component';

@Component({
  selector: 'app-expenses-list',
  standalone: true,
  imports: [
    TitleCasePipe,
    MatTableModule,
    MatIconModule,
    MoneyPipe,
    EmptyStateComponent,
    SkeletonRowsComponent,
    SourceDocumentLinkComponent,
  ],
  template: `
    <div class="p-6 bg-surface-base min-h-full">
      <!-- Page header -->
      <div class="mb-6">
        <h1 class="text-2xl font-bold text-text-primary">Expenses</h1>
        <p class="text-sm text-text-muted mt-1">Track and review project expenses.</p>
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

  loading  = signal(true);
  error    = signal<string | null>(null);
  expenses = signal<Expense[]>([]);

  displayedColumns = ['date', 'vendor', 'amount', 'category', 'billable', 'receipt'];

  ngOnInit(): void {
    this.expensesService.getExpenses().subscribe({
      next: (res) => {
        this.expenses.set(res);
        this.loading.set(false);
      },
      error: (e) => {
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
}
