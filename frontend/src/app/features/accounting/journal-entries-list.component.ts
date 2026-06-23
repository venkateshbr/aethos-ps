import {
  Component,
  inject,
  signal,
  computed,
  OnInit,
} from '@angular/core';
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
  FormArray,
  AbstractControl,
} from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';

import { MoneyPipe } from '../../shared/pipes/money.pipe';
import { EmptyStateComponent } from '../../shared/components/empty-state.component';
import { SkeletonRowsComponent } from '../../shared/components/skeleton-rows.component';
import { userMessageForError } from '../../core/utils/error-message';

// ─── Interfaces ───────────────────────────────────────────────────────────────

interface JournalLine {
  id: string;
  direction: 'DR' | 'CR';
  account_id: string;
  account_code?: string;
  account_name?: string;
  amount: string;
  currency: string;
  description?: string | null;
}

interface JournalEntry {
  id: string;
  entry_number: string;
  description: string;
  entry_date: string;
  reference?: string | null;
  reference_type: 'manual' | 'auto' | 'invoice' | 'bill' | 'payment';
  posted_by?: string | null;
  total_dr: string;
  lines?: JournalLine[];
}

interface Account {
  id: string;
  code: string;
  name: string;
  account_type: string;
}

interface CloseTask {
  id: string;
  period: string;
  code: string;
  title: string;
  description?: string | null;
  owner_role: string;
  status: 'open' | 'in_progress' | 'done' | 'waived' | 'blocked' | string;
  due_date?: string | null;
  completed_at?: string | null;
  completed_by?: string | null;
  evidence: Record<string, unknown>;
  order_index: number;
}

interface CloseProposalResponse {
  period: string;
  proposal_count: number;
  created_count: number;
  skipped_duplicates: number;
}

// ─── Type guard for API error shape ───────────────────────────────────────────
function isApiError(err: unknown): err is { error?: { detail?: string } } {
  return typeof err === 'object' && err !== null;
}

// ─── Filter type ──────────────────────────────────────────────────────────────
type FilterChip = 'all' | 'manual' | 'auto';

@Component({
  selector: 'app-journal-entries-list',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatIconModule,
    MatButtonModule,
    MatTableModule,
    MatTooltipModule,
    MoneyPipe,
    EmptyStateComponent,
    SkeletonRowsComponent,
  ],
  template: `
    <div class="p-6 bg-surface-base min-h-full">

      <!-- ── Page header ────────────────────────────────────────────── -->
      <div class="mb-6 flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-text-primary">Journal Entries</h1>
          <p class="text-sm text-text-muted mt-1">
            General ledger journals — auto-posted and manual adjustments.
          </p>
        </div>
        <!-- New Entry button — only for manager/owner -->
        @if (canPost()) {
          <button
            type="button"
            class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            aria-label="New Journal Entry"
            (click)="openForm()"
          >
            <mat-icon class="text-base leading-none" style="font-size:1rem;width:1rem;height:1rem;">add</mat-icon>
            New Journal Entry
          </button>
        }
      </div>

      <!-- ── Close checklist ────────────────────────────────────────── -->
      <section class="mb-6 border border-border-default rounded-lg bg-surface-raised overflow-hidden" aria-labelledby="close-tasks-title">
        <div class="flex items-center justify-between gap-4 px-4 py-3 border-b border-border-default">
          <div>
            <h2 id="close-tasks-title" class="text-sm font-semibold text-text-primary">Month-end close</h2>
            <p class="text-xs text-text-muted mt-0.5">{{ closePeriod() }} · {{ completedCloseTasks() }}/{{ closeTasks().length }} complete</p>
          </div>
          @if (closeTasks().length === 0 && !closeTasksLoading()) {
            <button
              type="button"
              class="inline-flex items-center gap-1.5 bg-accent hover:bg-accent-hover text-accent-on font-medium px-3 py-1.5 rounded text-xs transition-colors disabled:opacity-60"
              [disabled]="closeTaskAction() === 'bootstrap'"
              (click)="bootstrapCloseTasks()"
            >
              <mat-icon class="text-sm leading-none" style="font-size:1rem;width:1rem;height:1rem;">playlist_add_check</mat-icon>
              Start checklist
            </button>
          }
        </div>
        @if (canClose()) {
          <div class="flex flex-wrap items-center gap-2 px-4 py-3 border-b border-border-default bg-surface-base/60">
            <button
              type="button"
              class="inline-flex items-center gap-1.5 border border-border-default bg-surface hover:bg-surface-raised text-text-primary px-3 py-1.5 rounded text-xs transition-colors disabled:opacity-60"
              [disabled]="closeProposalAction() !== null"
              (click)="requestCloseProposal('propose-wip-accrual', 'WIP accrual')"
            >
              <mat-icon class="text-sm leading-none" style="font-size:1rem;width:1rem;height:1rem;">inventory</mat-icon>
              WIP accrual
            </button>
            <button
              type="button"
              class="inline-flex items-center gap-1.5 border border-border-default bg-surface hover:bg-surface-raised text-text-primary px-3 py-1.5 rounded text-xs transition-colors disabled:opacity-60"
              [disabled]="closeProposalAction() !== null"
              (click)="requestCloseProposal('propose-deferred-revenue-release', 'Deferred release')"
            >
              <mat-icon class="text-sm leading-none" style="font-size:1rem;width:1rem;height:1rem;">move_up</mat-icon>
              Deferred release
            </button>
            <button
              type="button"
              class="inline-flex items-center gap-1.5 border border-border-default bg-surface hover:bg-surface-raised text-text-primary px-3 py-1.5 rounded text-xs transition-colors disabled:opacity-60"
              [disabled]="closeProposalAction() !== null"
              (click)="requestCloseProposal('propose-milestone-recognition', 'Milestone recognition')"
            >
              <mat-icon class="text-sm leading-none" style="font-size:1rem;width:1rem;height:1rem;">task_alt</mat-icon>
              Milestone recognition
            </button>
          </div>
        }
        @if (closeTasksLoading()) {
          <div class="px-4 py-3 text-sm text-text-muted">Loading close tasks…</div>
        } @else if (closeTasksError()) {
          <div class="px-4 py-3 text-sm text-confidence-low" role="alert">{{ closeTasksError() }}</div>
        } @else if (closeTasks().length === 0) {
          <div class="px-4 py-4 text-sm text-text-muted">No close checklist has been started for this period.</div>
        } @else {
          <div class="divide-y divide-border-subtle">
            @for (task of closeTasks(); track task.id) {
              <div class="px-4 py-3 flex items-start gap-3">
                <span class="mt-1 w-2 h-2 rounded-full flex-none" [class]="closeTaskDotClass(task.status)" aria-hidden="true"></span>
                <div class="flex-1 min-w-0">
                  <div class="flex flex-wrap items-center gap-2">
                    <p class="text-sm font-medium text-text-primary">{{ task.title }}</p>
                    <span class="rounded bg-surface-base border border-border-subtle px-2 py-0.5 text-xs text-text-muted">{{ closeTaskLabel(task.status) }}</span>
                    <span class="text-xs text-text-disabled">{{ task.owner_role }}</span>
                  </div>
                  @if (task.description) {
                    <p class="text-xs text-text-muted mt-1">{{ task.description }}</p>
                  }
                </div>
                <div class="flex items-center gap-2 flex-none">
                  @if (task.status !== 'done') {
                    <button
                      type="button"
                      class="text-xs text-accent-light hover:text-accent transition-colors disabled:opacity-60"
                      [disabled]="closeTaskAction() === task.id"
                      (click)="updateCloseTask(task, 'done')"
                    >Done</button>
                  }
                  @if (task.status !== 'waived') {
                    <button
                      type="button"
                      class="text-xs text-text-muted hover:text-text-primary transition-colors disabled:opacity-60"
                      [disabled]="closeTaskAction() === task.id"
                      (click)="updateCloseTask(task, 'waived')"
                    >Waive</button>
                  }
                </div>
              </div>
            }
          </div>
        }
      </section>

      <!-- ── Filter chips ───────────────────────────────────────────── -->
      <div class="flex gap-2 mb-5" role="group" aria-label="Filter journal entries">
        @for (chip of filterChips; track chip.value) {
          <button
            type="button"
            class="px-3 py-1.5 rounded-full text-xs font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            [class]="activeFilter() === chip.value
              ? 'bg-indigo-700 text-white'
              : 'bg-surface-raised text-text-muted hover:text-text-primary border border-border-default'"
            [attr.aria-pressed]="activeFilter() === chip.value"
            (click)="setFilter(chip.value)"
          >{{ chip.label }}</button>
        }
      </div>

      <!-- ── Loading skeleton ───────────────────────────────────────── -->
      @if (loading()) {
        <app-skeleton-rows [count]="5" ariaLabel="Loading journal entries" />
      }

      <!-- ── Error state ────────────────────────────────────────────── -->
      @if (error() && !loading()) {
        <div class="rounded-lg border border-confidence-low/30 bg-confidence-low/10 px-4 py-3 text-sm text-confidence-low flex items-center gap-2"
             role="alert">
          <mat-icon class="text-base flex-none">error_outline</mat-icon>
          {{ error() }}
        </div>
      }

      <!-- ── Empty state ────────────────────────────────────────────── -->
      @if (!loading() && !error() && filteredEntries().length === 0) {
        <app-empty-state
          icon="receipt_long"
          heading="No journal entries"
          message="Auto-posted and manual GL journals will appear here."
        />
      }

      <!-- ── Journal entries table ──────────────────────────────────── -->
      @if (!loading() && !error() && filteredEntries().length > 0) {
        <div class="rounded-lg overflow-hidden border border-border-default">
          <table
            mat-table
            [dataSource]="filteredEntries()"
            class="w-full bg-surface-base"
            aria-label="Journal entries"
          >
            <!-- Entry # -->
            <ng-container matColumnDef="entry_number">
              <th mat-header-cell *matHeaderCellDef
                  class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Entry #
              </th>
              <td mat-cell *matCellDef="let row"
                  class="px-4 py-3 border-b border-border-subtle font-mono text-sm text-text-primary">
                {{ row.entry_number }}
              </td>
            </ng-container>

            <!-- Date -->
            <ng-container matColumnDef="entry_date">
              <th mat-header-cell *matHeaderCellDef
                  class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Date
              </th>
              <td mat-cell *matCellDef="let row"
                  class="px-4 py-3 border-b border-border-subtle text-sm text-text-secondary tabular-nums">
                {{ row.entry_date }}
              </td>
            </ng-container>

            <!-- Description -->
            <ng-container matColumnDef="description">
              <th mat-header-cell *matHeaderCellDef
                  class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Description
              </th>
              <td mat-cell *matCellDef="let row"
                  class="px-4 py-3 border-b border-border-subtle text-sm text-text-primary max-w-xs truncate">
                {{ row.description }}
              </td>
            </ng-container>

            <!-- Type badge -->
            <ng-container matColumnDef="reference_type">
              <th mat-header-cell *matHeaderCellDef
                  class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Type
              </th>
              <td mat-cell *matCellDef="let row"
                  class="px-4 py-3 border-b border-border-subtle">
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                      [class]="typeBadgeClass(row.reference_type)">
                  {{ row.reference_type }}
                </span>
              </td>
            </ng-container>

            <!-- Total DR -->
            <ng-container matColumnDef="total_dr">
              <th mat-header-cell *matHeaderCellDef
                  class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3 text-right">
                Total DR
              </th>
              <td mat-cell *matCellDef="let row"
                  class="px-4 py-3 border-b border-border-subtle text-sm font-mono text-text-primary text-right tabular-nums">
                {{ row.total_dr | money }}
              </td>
            </ng-container>

            <!-- Posted By -->
            <ng-container matColumnDef="posted_by">
              <th mat-header-cell *matHeaderCellDef
                  class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Posted By
              </th>
              <td mat-cell *matCellDef="let row"
                  class="px-4 py-3 border-b border-border-subtle text-sm text-text-muted">
                {{ row.posted_by ?? 'System' }}
              </td>
            </ng-container>

            <!-- Expand toggle -->
            <ng-container matColumnDef="expand">
              <th mat-header-cell *matHeaderCellDef
                  class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3 w-12">
              </th>
              <td mat-cell *matCellDef="let row"
                  class="px-4 py-3 border-b border-border-subtle w-12">
                <button
                  type="button"
                  class="text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
                  [attr.aria-label]="expandedRow() === row.id ? 'Collapse journal lines' : 'Expand journal lines'"
                  (click)="toggleRow($event, row.id)"
                >
                  <mat-icon class="text-base" style="font-size:1rem;width:1rem;height:1rem;">
                    {{ expandedRow() === row.id ? 'expand_less' : 'expand_more' }}
                  </mat-icon>
                </button>
              </td>
            </ng-container>

            <!-- Expanded detail row -->
            <ng-container matColumnDef="expandedDetail">
              <td mat-cell *matCellDef="let row"
                  [attr.colspan]="displayedColumns.length"
                  class="p-0 border-b border-border-default bg-surface-raised">
                @if (expandedRow() === row.id) {
                  <div class="px-6 py-4">
                    @if (row.lines && row.lines.length > 0) {
                      <table class="w-full text-sm" [attr.aria-label]="'Journal lines for ' + row.entry_number">
                        <thead>
                          <tr class="text-text-muted text-xs uppercase tracking-wide border-b border-border-subtle">
                            <th scope="col" class="text-left py-2 pr-4 w-8">D/C</th>
                            <th scope="col" class="text-left py-2 pr-4">Account</th>
                            <th scope="col" class="text-right py-2 pr-4 w-36">Amount</th>
                            <th scope="col" class="text-left py-2">Note</th>
                          </tr>
                        </thead>
                        <tbody>
                          @for (line of row.lines; track line.id) {
                            <tr class="border-b border-border-subtle last:border-0">
                              <td class="py-2 pr-4">
                                <span class="font-mono text-xs font-bold"
                                      [class]="line.direction === 'DR' ? 'text-blue-400' : 'text-emerald-400'">
                                  {{ line.direction }}
                                </span>
                              </td>
                              <td class="py-2 pr-4 text-text-secondary">
                                @if (line.account_code) {
                                  <span class="font-mono text-xs text-text-muted mr-2">{{ line.account_code }}</span>
                                }
                                {{ line.account_name ?? line.account_id }}
                              </td>
                              <td class="py-2 pr-4 text-right font-mono text-text-primary tabular-nums">
                                {{ line.amount | money: line.currency }}
                              </td>
                              <td class="py-2 text-text-muted text-xs">
                                {{ line.description ?? '—' }}
                              </td>
                            </tr>
                          }
                        </tbody>
                      </table>
                    } @else {
                      <p class="text-text-disabled text-xs">No line detail available.</p>
                    }
                  </div>
                }
              </td>
            </ng-container>

            <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
            <tr mat-row
                *matRowDef="let row; columns: displayedColumns"
                class="hover:bg-surface-raised transition-colors cursor-pointer"
                (click)="toggleRow($event, row.id)"
                [attr.aria-expanded]="expandedRow() === row.id"
            ></tr>
            <tr mat-row
                *matRowDef="let row; columns: ['expandedDetail']; when: isExpandedRow"
                class="detail-row"
            ></tr>
          </table>
        </div>
        <p class="text-xs text-text-disabled mt-3 text-right">
          {{ filteredEntries().length }} {{ filteredEntries().length === 1 ? 'entry' : 'entries' }}
        </p>
      }
    </div>

    <!-- ── New Journal Entry slide-in panel ──────────────────────────── -->
    @if (showForm()) {
      <div
        class="fixed inset-0 bg-black/50 z-40"
        (click)="closeForm()"
        aria-hidden="true"
      ></div>
      <aside
        class="fixed right-0 top-0 h-full w-full max-w-2xl bg-surface border-l border-border-default z-50 flex flex-col shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="journal-form-title"
      >
        <!-- Panel header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-border-default flex-none">
          <h2 id="journal-form-title" class="text-base font-semibold text-text-primary">
            Post Manual Journal Entry
          </h2>
          <button
            type="button"
            class="text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
            (click)="closeForm()"
            aria-label="Close panel"
          >
            <mat-icon>close</mat-icon>
          </button>
        </div>

        <!-- Panel body -->
        <form
          [formGroup]="journalForm"
          (ngSubmit)="submitJournal()"
          class="flex-1 overflow-y-auto px-6 py-5 space-y-5"
          novalidate
        >
          <!-- Description -->
          <div>
            <label for="jnl-desc" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
              Description <span class="text-confidence-low">*</span>
            </label>
            <input
              id="jnl-desc"
              type="text"
              formControlName="description"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
              placeholder="Reason for this entry (e.g. Month-end accrual)"
            />
            @if (journalForm.controls.description.touched && journalForm.controls.description.errors?.['required']) {
              <p class="text-xs text-confidence-low mt-1">Description is required.</p>
            }
          </div>

          <!-- Entry Date + Reference (side by side) -->
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label for="jnl-date" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
                Entry Date <span class="text-confidence-low">*</span>
              </label>
              <input
                id="jnl-date"
                type="date"
                formControlName="entry_date"
                class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
              />
              @if (journalForm.controls.entry_date.touched && journalForm.controls.entry_date.errors?.['required']) {
                <p class="text-xs text-confidence-low mt-1">Date is required.</p>
              }
            </div>
            <div>
              <label for="jnl-ref" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
                Reference
              </label>
              <input
                id="jnl-ref"
                type="text"
                formControlName="reference"
                class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
                placeholder="e.g. Month-end accrual"
              />
            </div>
          </div>

          <!-- Lines table -->
          <div>
            <div class="flex items-center justify-between mb-2">
              <label class="block text-xs uppercase tracking-wide text-text-muted">
                Journal Lines <span class="text-confidence-low">*</span>
              </label>
              <span class="text-xs text-text-disabled">Min 2 lines — DR must equal CR</span>
            </div>

            <!-- Lines header -->
            <div class="grid grid-cols-[1fr_64px_140px_120px_32px] gap-2 mb-1 text-xs uppercase tracking-wide text-text-muted px-1">
              <span>Account</span>
              <span class="text-center">D/C</span>
              <span class="text-right pr-1">Amount</span>
              <span>Note</span>
              <span></span>
            </div>

            <div formArrayName="lines" class="space-y-2">
              @for (ctrl of linesArray.controls; track $index) {
                <div [formGroupName]="$index"
                     class="grid grid-cols-[1fr_64px_140px_120px_32px] gap-2 items-start">

                  <!-- Account picker -->
                  <div>
                    <input
                      type="text"
                      formControlName="account_search"
                      [attr.aria-label]="'Account for line ' + ($index + 1)"
                      [attr.id]="'jnl-acct-' + $index"
                      class="w-full px-2.5 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
                      placeholder="Search account…"
                      (input)="onAccountSearch($index)"
                      autocomplete="off"
                    />
                    <!-- Dropdown suggestions -->
                    @if (activeSuggestionLine() === $index && filteredAccounts().length > 0) {
                      <div
                        class="absolute z-50 mt-1 w-72 bg-surface-raised border border-border-default rounded shadow-xl max-h-52 overflow-y-auto"
                        role="listbox"
                        [attr.aria-label]="'Account suggestions for line ' + ($index + 1)"
                      >
                        @for (acct of filteredAccounts(); track acct.id) {
                          <button
                            type="button"
                            role="option"
                            class="w-full text-left px-3 py-2.5 text-sm hover:bg-surface transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                            (click)="selectAccount($index, acct)"
                          >
                            <span class="font-mono text-xs text-text-muted mr-2">{{ acct.code }}</span>
                            <span class="text-text-primary">{{ acct.name }}</span>
                            <span class="ml-2 text-xs text-text-disabled capitalize">{{ acct.account_type }}</span>
                          </button>
                        }
                      </div>
                    }
                    @if (getLineControl($index, 'account_id').touched && !getLineControl($index, 'account_id').value) {
                      <p class="text-xs text-confidence-low mt-0.5">Select an account.</p>
                    }
                  </div>

                  <!-- Direction (DR / CR) -->
                  <div>
                    <select
                      formControlName="direction"
                      [attr.aria-label]="'Direction for line ' + ($index + 1)"
                      class="w-full px-2 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm font-mono"
                    >
                      <option value="DR">DR</option>
                      <option value="CR">CR</option>
                    </select>
                  </div>

                  <!-- Amount -->
                  <div>
                    <input
                      type="text"
                      formControlName="amount"
                      [attr.aria-label]="'Amount for line ' + ($index + 1)"
                      class="w-full px-2.5 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm font-mono text-right"
                      placeholder="0.00"
                      (input)="recomputeTotals()"
                    />
                    @if (getLineControl($index, 'amount').touched && getLineControl($index, 'amount').errors?.['required']) {
                      <p class="text-xs text-confidence-low mt-0.5">Required.</p>
                    }
                    @if (getLineControl($index, 'amount').touched && getLineControl($index, 'amount').errors?.['pattern']) {
                      <p class="text-xs text-confidence-low mt-0.5">Enter a valid number.</p>
                    }
                  </div>

                  <!-- Line description -->
                  <div>
                    <input
                      type="text"
                      formControlName="line_description"
                      [attr.aria-label]="'Note for line ' + ($index + 1)"
                      class="w-full px-2.5 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
                      placeholder="Optional"
                    />
                  </div>

                  <!-- Remove line -->
                  <div class="pt-1.5">
                    <button
                      type="button"
                      class="text-text-disabled hover:text-confidence-low transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-confidence-low rounded disabled:opacity-30"
                      [disabled]="linesArray.length <= 2"
                      [attr.aria-label]="'Remove line ' + ($index + 1)"
                      (click)="removeLine($index)"
                    >
                      <mat-icon style="font-size:1rem;width:1rem;height:1rem;">close</mat-icon>
                    </button>
                  </div>
                </div>
              }
            </div>

            <!-- Add line -->
            <button
              type="button"
              class="mt-3 inline-flex items-center gap-1.5 text-sm text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
              (click)="addLine()"
            >
              <mat-icon style="font-size:1rem;width:1rem;height:1rem;">add</mat-icon>
              Add line
            </button>
          </div>

          <!-- ── Balance summary ─────────────────────────────────────── -->
          <div class="rounded-lg border px-4 py-3 flex items-center justify-between text-sm"
               [class]="isBalanced() ? 'border-emerald-800 bg-accent/10' : 'border-confidence-low/30 bg-confidence-low/10'">
            <div class="flex items-center gap-4">
              <span class="text-text-muted">DR Total</span>
              <span class="font-mono font-semibold text-text-primary tabular-nums">
                {{ drTotal() | money }}
              </span>
              <span class="text-text-disabled mx-1">=</span>
              <span class="text-text-muted">CR Total</span>
              <span class="font-mono font-semibold text-text-primary tabular-nums">
                {{ crTotal() | money }}
              </span>
            </div>
            @if (isBalanced()) {
              <span class="text-accent-light flex items-center gap-1 font-medium" role="status">
                <mat-icon style="font-size:1rem;width:1rem;height:1rem;">check_circle</mat-icon>
                Balanced
              </span>
            } @else {
              <span class="text-confidence-low flex items-center gap-1 font-medium" role="alert">
                <mat-icon style="font-size:1rem;width:1rem;height:1rem;">warning</mat-icon>
                Out of balance
              </span>
            }
          </div>

          <!-- Error banner -->
          @if (formError()) {
            <div role="alert"
                 class="text-sm text-confidence-low bg-confidence-low/10 border border-confidence-low/30 rounded px-3 py-2 flex items-start gap-2">
              <mat-icon class="text-base flex-none mt-0.5">error_outline</mat-icon>
              {{ formError() }}
            </div>
          }

        </form>

        <!-- Panel footer -->
        <div class="flex-none px-6 py-4 border-t border-border-default flex items-center justify-end gap-3">
          <button
            type="button"
            class="px-4 py-2 text-sm text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
            (click)="closeForm()"
          >Cancel</button>
          <button
            type="button"
            class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            [disabled]="!isBalanced() || journalForm.invalid || submitting()"
            (click)="submitJournal()"
          >
            @if (submitting()) { Posting… } @else { Post Journal Entry }
          </button>
        </div>
      </aside>
    }

    <!-- ── Success toast ──────────────────────────────────────────────── -->
    @if (successToast()) {
      <div
        class="fixed bottom-6 right-6 z-60 flex items-center gap-3 bg-surface-raised border border-emerald-800 text-accent-light px-4 py-3 rounded-lg shadow-xl text-sm"
        role="status"
        aria-live="polite"
      >
        <mat-icon class="text-base flex-none">check_circle</mat-icon>
        {{ successToast() }}
      </div>
    }
  `,
  styles: [`
    :host { display: block; }
    ::ng-deep .mat-mdc-table { background: transparent !important; }
    ::ng-deep .mat-mdc-header-row,
    ::ng-deep .mat-mdc-row { background: transparent !important; }
    ::ng-deep .mat-mdc-cell,
    ::ng-deep .mat-mdc-header-cell { border-bottom: none !important; }

    /* Hide the expanded-detail row's own border when collapsed */
    tr.detail-row { height: 0; }
    tr.detail-row td { padding: 0; border: none; }
  `],
})
export class JournalEntriesListComponent implements OnInit {
  private http = inject(HttpClient);
  private fb   = inject(FormBuilder);

  // ── List state ──────────────────────────────────────────────────────
  loading  = signal(true);
  error    = signal<string | null>(null);
  entries  = signal<JournalEntry[]>([]);
  expandedRow = signal<string | null>(null);
  closePeriod = signal(new Date().toISOString().slice(0, 7));
  closeTasks = signal<CloseTask[]>([]);
  closeTasksLoading = signal(false);
  closeTasksError = signal<string | null>(null);
  closeTaskAction = signal<string | null>(null);
  closeProposalAction = signal<string | null>(null);
  completedCloseTasks = computed(() =>
    this.closeTasks().filter(task => ['done', 'waived'].includes(task.status)).length,
  );

  // RBAC: read role from localStorage (set by login flow)
  // The back-end enforces this too — this is only a UI affordance.
  canPost = computed(() => {
    try {
      const raw = localStorage.getItem('aethos_role');
      return raw === 'manager' || raw === 'owner';
    } catch {
      return false;
    }
  });

  canClose = computed(() => {
    try {
      const raw = localStorage.getItem('aethos_role');
      return raw === 'admin' || raw === 'owner';
    } catch {
      return false;
    }
  });

  // ── Filter chips ────────────────────────────────────────────────────
  readonly filterChips: { label: string; value: FilterChip }[] = [
    { label: 'All', value: 'all' },
    { label: 'Manual', value: 'manual' },
    { label: 'Auto-posted', value: 'auto' },
  ];
  activeFilter = signal<FilterChip>('all');

  filteredEntries = computed(() => {
    const f = this.activeFilter();
    const all = this.entries();
    if (f === 'all') return all;
    if (f === 'manual') return all.filter(e => e.reference_type === 'manual');
    if (f === 'auto') return all.filter(e => e.reference_type === 'auto');
    return all;
  });

  // ── Table columns ────────────────────────────────────────────────────
  readonly displayedColumns = [
    'entry_number', 'entry_date', 'description',
    'reference_type', 'total_dr', 'posted_by', 'expand',
  ];

  // ── Form state ───────────────────────────────────────────────────────
  showForm  = signal(false);
  submitting = signal(false);
  formError  = signal<string | null>(null);
  successToast = signal<string | null>(null);

  // COA for account picker
  accounts = signal<Account[]>([]);
  filteredAccounts = signal<Account[]>([]);
  activeSuggestionLine = signal<number | null>(null);

  // DR / CR running totals (as numeric strings)
  drTotal = signal<string>('0.00');
  crTotal = signal<string>('0.00');
  isBalanced = computed(() => {
    const dr = parseFloat(this.drTotal()) || 0;
    const cr = parseFloat(this.crTotal()) || 0;
    return Math.abs(dr - cr) < 0.005 && dr > 0;
  });

  // Reactive form
  journalForm = this.fb.nonNullable.group({
    description: ['', [Validators.required, Validators.maxLength(255)]],
    entry_date:  ['', [Validators.required]],
    reference:   [''],
    lines: this.fb.array([
      this.buildLine(),
      this.buildLine('CR'),
    ]),
  });

  get linesArray(): FormArray {
    return this.journalForm.get('lines') as FormArray;
  }

  // ── Lifecycle ────────────────────────────────────────────────────────
  ngOnInit(): void {
    this.loadEntries();
    this.loadCloseTasks();
  }

  // ── List operations ──────────────────────────────────────────────────
  loadEntries(): void {
    this.loading.set(true);
    this.error.set(null);
    this.http.get<JournalEntry[] | { items: JournalEntry[] }>('/api/v1/accounting/journal-entries').subscribe({
      next: (data: any) => {
        // API may return either flat array or { items, total }
        const entries = Array.isArray(data) ? data : (data?.items ?? []);
        this.entries.set(entries);
        this.loading.set(false);
      },
      error: (err: unknown) => {
        this.error.set(userMessageForError(err, 'Journal Entries'));
        this.loading.set(false);
      },
    });
  }

  setFilter(f: FilterChip): void {
    this.activeFilter.set(f);
  }

  loadCloseTasks(): void {
    this.closeTasksLoading.set(true);
    this.closeTasksError.set(null);
    this.http.get<{ tasks: CloseTask[] }>(
      `/api/v1/accounting/periods/${this.closePeriod()}/close-tasks`,
    ).subscribe({
      next: (res) => {
        this.closeTasks.set(res.tasks ?? []);
        this.closeTasksLoading.set(false);
      },
      error: (err: unknown) => {
        this.closeTasksError.set(userMessageForError(err, 'Close Tasks'));
        this.closeTasksLoading.set(false);
      },
    });
  }

  bootstrapCloseTasks(): void {
    this.closeTaskAction.set('bootstrap');
    this.closeTasksError.set(null);
    this.http.post<{ tasks: CloseTask[] }>(
      `/api/v1/accounting/periods/${this.closePeriod()}/close-tasks/bootstrap`,
      {},
    ).subscribe({
      next: (res) => {
        this.closeTasks.set(res.tasks ?? []);
        this.closeTaskAction.set(null);
      },
      error: (err: unknown) => {
        this.closeTasksError.set(userMessageForError(err, 'Close Tasks'));
        this.closeTaskAction.set(null);
      },
    });
  }

  updateCloseTask(task: CloseTask, status: 'done' | 'waived'): void {
    this.closeTaskAction.set(task.id);
    this.closeTasksError.set(null);
    this.http.patch<CloseTask>(
      `/api/v1/accounting/periods/${this.closePeriod()}/close-tasks/${task.id}`,
      { status },
    ).subscribe({
      next: (updated) => {
        this.closeTasks.update(tasks => tasks.map(row => row.id === updated.id ? updated : row));
        this.closeTaskAction.set(null);
      },
      error: (err: unknown) => {
        this.closeTasksError.set(userMessageForError(err, 'Close Tasks'));
        this.closeTaskAction.set(null);
      },
    });
  }

  requestCloseProposal(action: string, label: string): void {
    this.closeProposalAction.set(action);
    this.closeTasksError.set(null);
    this.http.post<CloseProposalResponse>(
      `/api/v1/accounting/periods/${this.closePeriod()}/${action}`,
      {},
    ).subscribe({
      next: (res) => {
        this.successToast.set(
          `${label}: ${res.created_count} review task(s), ${res.skipped_duplicates} duplicate(s) skipped.`,
        );
        this.closeProposalAction.set(null);
        this.loadCloseTasks();
      },
      error: (err: unknown) => {
        this.closeTasksError.set(userMessageForError(err, label));
        this.closeProposalAction.set(null);
      },
    });
  }

  toggleRow(event: Event, id: string): void {
    // Don't toggle when clicking the button inside the row (it handles itself)
    const target = event.target as HTMLElement;
    if (target.closest('button') && !target.closest('[aria-label*="Expand"]') && !target.closest('[aria-label*="Collapse"]')) {
      return;
    }
    this.expandedRow.set(this.expandedRow() === id ? null : id);
  }

  /** Row predicate for the expandedDetail row definition. */
  isExpandedRow = (_index: number, row: JournalEntry) => this.expandedRow() === row.id;

  // ── Form operations ─────────────────────────────────────────────────
  openForm(): void {
    const today = new Date().toISOString().split('T')[0];
    // Reset to 2 lines
    this.journalForm.reset({
      description: '',
      entry_date: today,
      reference: '',
    });
    // Clear lines array and add 2 fresh lines
    while (this.linesArray.length > 0) this.linesArray.removeAt(0);
    this.linesArray.push(this.buildLine('DR'));
    this.linesArray.push(this.buildLine('CR'));

    this.formError.set(null);
    this.drTotal.set('0.00');
    this.crTotal.set('0.00');
    this.activeSuggestionLine.set(null);
    this.filteredAccounts.set([]);

    // Load chart of accounts
    this.loadAccounts();
    this.showForm.set(true);
  }

  closeForm(): void {
    this.showForm.set(false);
    this.activeSuggestionLine.set(null);
    this.filteredAccounts.set([]);
  }

  loadAccounts(): void {
    if (this.accounts().length > 0) return;
    this.http.get<Account[]>('/api/v1/accounts').subscribe({
      next: (data) => this.accounts.set(data ?? []),
      error: () => { /* non-blocking — user sees no suggestions */ },
    });
  }

  buildLine(direction: 'DR' | 'CR' = 'DR') {
    return this.fb.nonNullable.group({
      account_id:       ['', [Validators.required]],
      account_search:   [''],
      direction:        [direction as 'DR' | 'CR', [Validators.required]],
      amount:           ['', [Validators.required, Validators.pattern(/^\d+(\.\d{1,2})?$/)]],
      line_description: [''],
    });
  }

  addLine(): void {
    this.linesArray.push(this.buildLine('DR'));
  }

  removeLine(index: number): void {
    if (this.linesArray.length <= 2) return;
    this.linesArray.removeAt(index);
    this.recomputeTotals();
  }

  getLineControl(index: number, name: string): AbstractControl {
    return (this.linesArray.at(index) as ReturnType<typeof this.buildLine>).get(name)!;
  }

  // ── Account search ──────────────────────────────────────────────────
  onAccountSearch(index: number): void {
    const term = (this.getLineControl(index, 'account_search').value as string ?? '').toLowerCase().trim();
    if (!term) {
      this.filteredAccounts.set([]);
      this.activeSuggestionLine.set(null);
      return;
    }
    const matches = this.accounts().filter(
      a =>
        a.code.toLowerCase().includes(term) ||
        a.name.toLowerCase().includes(term) ||
        a.account_type.toLowerCase().includes(term),
    ).slice(0, 12);
    this.filteredAccounts.set(matches);
    this.activeSuggestionLine.set(matches.length > 0 ? index : null);
  }

  selectAccount(index: number, acct: Account): void {
    const lineGroup = this.linesArray.at(index);
    lineGroup.patchValue({
      account_id: acct.id,
      account_search: `${acct.code} — ${acct.name}`,
    });
    this.activeSuggestionLine.set(null);
    this.filteredAccounts.set([]);
  }

  // ── Balance computation ──────────────────────────────────────────────
  recomputeTotals(): void {
    let dr = 0;
    let cr = 0;
    for (let i = 0; i < this.linesArray.length; i++) {
      const ctrl = this.linesArray.at(i);
      const dir = ctrl.get('direction')?.value as string;
      const amt = parseFloat(ctrl.get('amount')?.value as string ?? '') || 0;
      if (dir === 'DR') dr += amt;
      else cr += amt;
    }
    this.drTotal.set(dr.toFixed(2));
    this.crTotal.set(cr.toFixed(2));
  }

  // ── Submit ────────────────────────────────────────────────────────────
  submitJournal(): void {
    this.recomputeTotals();
    if (!this.isBalanced()) return;
    if (this.journalForm.invalid) {
      this.journalForm.markAllAsTouched();
      this.linesArray.controls.forEach(c => c.markAllAsTouched());
      return;
    }

    this.submitting.set(true);
    this.formError.set(null);

    const v = this.journalForm.getRawValue();
    const payload = {
      description: v.description,
      entry_date:  v.entry_date,
      reference:   v.reference || undefined,
      lines: v.lines.map(l => ({
        direction:   l.direction,
        account_id:  l.account_id,
        amount:      parseFloat(l.amount).toFixed(2),
        description: l.line_description || undefined,
      })),
    };

    this.http.post<JournalEntry>('/api/v1/accounting/journal-entries', payload).subscribe({
      next: (created) => {
        this.entries.update(list => [created, ...list]);
        this.submitting.set(false);
        this.closeForm();
        this.successToast.set(`Journal ${created.entry_number} posted successfully.`);
        setTimeout(() => this.successToast.set(null), 5000);
      },
      error: (err: unknown) => {
        this.submitting.set(false);
        let msg = 'Could not post journal entry. Please try again.';
        if (isApiError(err) && typeof err.error?.detail === 'string') {
          msg = err.error.detail;
        } else {
          msg = userMessageForError(err, 'Journal Entry');
        }
        this.formError.set(msg);
      },
    });
  }

  // ── Badge helpers ─────────────────────────────────────────────────────
  typeBadgeClass(type: string): string {
    switch (type) {
      case 'manual':  return 'bg-purple-500/20 text-purple-300';
      case 'auto':    return 'bg-slate-500/20 text-slate-300';
      case 'invoice': return 'bg-blue-500/20 text-blue-300';
      case 'bill':    return 'bg-amber-500/20 text-amber-300';
      case 'payment': return 'bg-emerald-500/20 text-emerald-300';
      default:        return 'bg-surface text-text-muted';
    }
  }

  closeTaskLabel(status: string): string {
    if (status === 'in_progress') return 'In progress';
    return status.charAt(0).toUpperCase() + status.slice(1);
  }

  closeTaskDotClass(status: string): string {
    switch (status) {
      case 'done': return 'bg-emerald-400';
      case 'waived': return 'bg-slate-400';
      case 'blocked': return 'bg-red-400';
      case 'in_progress': return 'bg-amber-400';
      default: return 'bg-slate-600';
    }
  }
}
