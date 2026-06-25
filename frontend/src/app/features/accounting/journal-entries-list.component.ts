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
import { DecisionTimelineComponent } from '../../shared/components/decision-timeline.component';
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
  reason?: string | null;
  entry_date: string;
  reference?: string | null;
  reference_type:
    | 'manual'
    | 'manual_reversal'
    | 'auto'
    | 'invoice'
    | 'bill'
    | 'payment'
    | 'year_end_close';
  posted_by?: string | null;
  total_dr: string;
  lines?: JournalLine[];
}

interface ManualJournalPendingApproval {
  status: 'pending_approval';
  task_id?: string | null;
  suggestion_id?: string | null;
  required_approval_role: string;
  approval_policy_reason: string;
  total_debits: string;
  threshold: string;
  message: string;
}

type ManualJournalSubmitResponse = JournalEntry | ManualJournalPendingApproval;

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

interface YearEndCloseResponse {
  year: number;
  period: string;
  entry_date: string;
  journal_entry_id: string;
  entry_number: string;
  posted_at: string;
  net_income: string;
  retained_earnings_direction: 'DR' | 'CR' | null;
  retained_earnings_amount: string;
  retained_earnings_account: {
    id: string;
    code: string;
    name: string;
  };
  revenue_closed: string;
  expenses_closed: string;
  line_count: number;
}

interface CloseVarianceComment {
  code: string;
  severity?: string;
  summary: string;
  metric?: string;
  delta?: string;
  delta_pct?: number | null;
  current?: string;
  previous?: string;
  service_line?: string;
}

interface CloseChecklistItem {
  code: string;
  label: string;
  status: string;
  blocking: boolean;
  summary: string;
  count: number;
  overridden?: boolean;
}

interface CloseOverride {
  id: string;
  period: string;
  blocker_code: string;
  reason: string;
  created_by: string;
  created_by_role?: string;
  created_at: string;
  blocker_ref?: Record<string, unknown>;
}

interface ClosePackage {
  period: string;
  generated_at: string;
  previous_period: string;
  close_status: {
    status?: string;
    ready_to_lock?: boolean;
    locked?: boolean;
    checklist?: CloseChecklistItem[];
    lock_blockers?: string[];
  };
  gl_summary: Record<string, string | number | null>;
  previous_gl_summary: Record<string, string | number | null>;
  working_capital: Record<string, string | number | null>;
  readiness_evidence?: Record<string, Record<string, unknown>>;
  close_overrides?: CloseOverride[];
  variance_commentary: CloseVarianceComment[];
}

interface CloseReadinessArea {
  key: string;
  label: string;
  status: string;
  metric: string;
}

interface CloseOverrideOption {
  code: string;
  label: string;
  summary: string;
  status: string;
}

interface RecurringJournalTemplateLine {
  id: string;
  account_id: string;
  direction: 'DR' | 'CR';
  amount: string;
  description?: string | null;
  order_index: number;
}

interface RecurringJournalTemplate {
  id: string;
  name: string;
  description?: string | null;
  schedule_day: number;
  start_period: string;
  end_period?: string | null;
  currency: string;
  is_active: boolean;
  created_by?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  lines: RecurringJournalTemplateLine[];
}

type JournalFormMode = 'journal' | 'recurring';

const CLOSE_OVERRIDE_LABELS: Record<string, string> = {
  subledger_reconciliation: 'Sub-ledger reconciliation',
  trial_balance: 'Trial balance',
  close_reviews: 'Pending close reviews',
  close_tasks: 'Close tasks',
  unposted_journals: 'Unposted journals',
};

// ─── Type guard for API error shape ───────────────────────────────────────────
type ApiErrorDetail = string | {
  code?: string;
  period?: string;
  message?: string;
  locked_periods?: string[];
  entry_number?: string;
};

function isApiError(err: unknown): err is { error?: { detail?: ApiErrorDetail } } {
  return typeof err === 'object' && err !== null;
}

function journalErrorMessage(err: unknown): string | null {
  if (!isApiError(err)) return null;
  const detail = err.error?.detail;
  if (typeof detail === 'string') return detail;
  if (detail?.code === 'period_locked') {
    const period = detail.period ? ` ${detail.period}` : '';
    return `Accounting period${period} is locked. Choose an open entry date or unlock the period before posting.`;
  }
  if (detail?.message) return detail.message;
  return null;
}

function yearEndCloseErrorMessage(err: unknown): string | null {
  if (!isApiError(err)) return null;
  const detail = err.error?.detail;
  if (typeof detail === 'string') return detail;
  if (detail?.code === 'year_end_close_period_locked') {
    const periods = detail.locked_periods?.join(', ') || 'one or more periods';
    return `Unlock ${periods} before posting year-end close.`;
  }
  if (detail?.code === 'year_end_close_already_posted') {
    const entry = detail.entry_number ? ` (${detail.entry_number})` : '';
    return `Year-end close is already posted${entry}.`;
  }
  if (detail?.message) return detail.message;
  return null;
}

function isManualJournalPendingApproval(
  response: ManualJournalSubmitResponse,
): response is ManualJournalPendingApproval {
  return 'status' in response && response.status === 'pending_approval';
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
    DecisionTimelineComponent,
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
        <!-- New Entry button: manager+; backend enforces the same hierarchy. -->
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
          <div class="flex items-center gap-2">
            @if (canClose()) {
              <button
                type="button"
                class="inline-flex items-center gap-1.5 border border-border-default bg-surface hover:bg-surface-raised text-text-primary px-3 py-1.5 rounded text-xs transition-colors disabled:opacity-60"
                [disabled]="closePackageLoading()"
                (click)="loadClosePackage()"
              >
                <mat-icon class="text-sm leading-none" style="font-size:1rem;width:1rem;height:1rem;">summarize</mat-icon>
                Close package
              </button>
            }
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
        </div>
        @if (closePackageError()) {
          <div class="px-4 py-3 text-sm text-confidence-low border-b border-border-default" role="alert">{{ closePackageError() }}</div>
        }
        @if (closePackage()) {
          <div class="px-4 py-3 border-b border-border-default bg-surface-base/40">
            <div class="grid gap-3 md:grid-cols-3 mb-3">
              <div>
                <p class="text-xs uppercase tracking-wide text-text-muted">Net income</p>
                <p class="text-sm font-mono text-text-primary">{{ closePackageValue('gl_summary', 'net_income') | money }}</p>
                <p class="text-xs text-text-disabled">Prior {{ closePackageValue('previous_gl_summary', 'net_income') | money }}</p>
              </div>
              <div>
                <p class="text-xs uppercase tracking-wide text-text-muted">Open AR/AP</p>
                <p class="text-sm font-mono text-text-primary">
                  {{ closePackageValue('working_capital', 'ar_open_total') | money }}
                  /
                  {{ closePackageValue('working_capital', 'ap_open_total') | money }}
                </p>
                <p class="text-xs text-text-disabled">AR / AP exposure</p>
              </div>
              <div>
                <p class="text-xs uppercase tracking-wide text-text-muted">WIP</p>
                <p class="text-sm font-mono text-text-primary">{{ closePackageValue('working_capital', 'wip_total') | money }}</p>
                <p class="text-xs text-text-disabled">Generated {{ closePackage()!.generated_at.slice(0, 10) }}</p>
              </div>
            </div>
            @if (closeReadinessAreas().length) {
              <div class="grid gap-2 md:grid-cols-3 xl:grid-cols-6 mb-3">
                @for (area of closeReadinessAreas(); track area.key) {
                  <div class="border-l-2 border-border-subtle bg-surface px-3 py-2">
                    <div class="flex items-center justify-between gap-2">
                      <p class="text-xs uppercase tracking-wide text-text-muted">{{ area.label }}</p>
                      <span class="rounded px-1.5 py-0.5 text-[11px]" [class]="readinessStatusClass(area.status)">
                        {{ area.status }}
                      </span>
                    </div>
                    <p class="text-xs text-text-primary mt-1 truncate">{{ area.metric }}</p>
                  </div>
                }
              </div>
            }
            @if (canClose()) {
              <div class="mb-3 rounded border border-border-subtle bg-surface px-3 py-3">
                <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div class="min-w-0">
                    <h3 class="text-xs font-semibold uppercase tracking-wide text-text-primary">Close override</h3>
                    <p class="mt-1 text-xs text-text-muted">
                      Record a named blocker override with a controller reason before attempting period lock.
                    </p>
                  </div>
                  <form [formGroup]="closeOverrideForm" (ngSubmit)="createCloseOverride()" class="grid flex-1 gap-2 lg:max-w-2xl lg:grid-cols-[minmax(12rem,16rem)_1fr_auto]" novalidate>
                    <select
                      formControlName="blocker_code"
                      class="rounded border border-border-default bg-surface-base px-3 py-2 text-xs text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
                      aria-label="Close blocker to override"
                    >
                      @for (option of closeOverrideOptions(); track option.code) {
                        <option [value]="option.code">{{ option.label }}</option>
                      }
                    </select>
                    <input
                      type="text"
                      formControlName="reason"
                      maxlength="2000"
                      placeholder="Reason and evidence reviewed"
                      class="rounded border border-border-default bg-surface-base px-3 py-2 text-xs text-text-primary placeholder:text-text-disabled focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
                    />
                    <button
                      type="submit"
                      class="inline-flex items-center justify-center gap-1.5 rounded bg-accent px-3 py-2 text-xs font-medium text-accent-on transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                      [disabled]="closeOverrideForm.invalid || closeOverrideAction()"
                    >
                      <mat-icon class="text-sm leading-none" style="font-size:1rem;width:1rem;height:1rem;">verified_user</mat-icon>
                      Record
                    </button>
                  </form>
                </div>
                @if (closeOverrideError()) {
                  <p class="mt-2 text-xs text-confidence-low" role="alert">{{ closeOverrideError() }}</p>
                }
                @if (closePackage()!.close_overrides?.length) {
                  <div class="mt-3 divide-y divide-border-subtle border-t border-border-subtle pt-2">
                    @for (override of closePackage()!.close_overrides; track override.id) {
                      <div class="py-2 text-xs">
                        <div class="flex flex-wrap items-center gap-2">
                          <span class="font-medium text-text-primary">{{ blockerLabel(override.blocker_code) }}</span>
                          <span class="rounded bg-blue-500/15 px-1.5 py-0.5 text-blue-300">{{ override.created_by_role || 'unknown' }}</span>
                          <span class="text-text-disabled">{{ formatOverrideTimestamp(override.created_at) }}</span>
                        </div>
                        <p class="mt-1 text-text-muted">{{ override.reason }}</p>
                      </div>
                    }
                  </div>
                }
              </div>
            }
            <app-decision-timeline entityType="month_end_close" [entityId]="closePeriod()" title="Close approval timeline" />
            <div class="divide-y divide-border-subtle border border-border-subtle rounded bg-surface">
              @for (comment of closePackage()!.variance_commentary; track comment.code) {
                <div class="px-3 py-2">
                  <div class="flex items-start justify-between gap-3">
                    <p class="text-sm text-text-primary">{{ comment.summary }}</p>
                    <span class="rounded px-2 py-0.5 text-xs flex-none" [class]="varianceSeverityClass(comment.severity)">
                      {{ comment.severity ?? 'info' }}
                    </span>
                  </div>
                  @if (comment.delta || comment.delta_pct !== undefined && comment.delta_pct !== null) {
                    <p class="text-xs text-text-muted mt-1">
                      @if (comment.delta) { Delta {{ comment.delta | money }} }
                      @if (comment.delta_pct !== undefined && comment.delta_pct !== null) { · {{ comment.delta_pct }}% }
                    </p>
                  }
                </div>
              }
            </div>
          </div>
        }
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
              (click)="requestCloseProposal('propose-expense-accrual', 'Expense accrual')"
            >
              <mat-icon class="text-sm leading-none" style="font-size:1rem;width:1rem;height:1rem;">request_quote</mat-icon>
              Expense accrual
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
            <button
              type="button"
              class="inline-flex items-center gap-1.5 border border-border-default bg-surface hover:bg-surface-raised text-text-primary px-3 py-1.5 rounded text-xs transition-colors disabled:opacity-60"
              [disabled]="closeProposalAction() !== null"
              (click)="requestCloseProposal('propose-percentage-completion-recognition', 'Percentage completion')"
            >
              <mat-icon class="text-sm leading-none" style="font-size:1rem;width:1rem;height:1rem;">trending_up</mat-icon>
              Percentage completion
            </button>
            <button
              type="button"
              class="inline-flex items-center gap-1.5 border border-border-default bg-surface hover:bg-surface-raised text-text-primary px-3 py-1.5 rounded text-xs transition-colors disabled:opacity-60"
              [disabled]="closeProposalAction() !== null"
              (click)="requestCloseProposal('propose-prepaid-amortization', 'Prepaid amortization')"
            >
              <mat-icon class="text-sm leading-none" style="font-size:1rem;width:1rem;height:1rem;">event_repeat</mat-icon>
              Prepaid amortization
            </button>
            <button
              type="button"
              class="inline-flex items-center gap-1.5 border border-border-default bg-surface hover:bg-surface-raised text-text-primary px-3 py-1.5 rounded text-xs transition-colors disabled:opacity-60"
              [disabled]="closeProposalAction() !== null"
              (click)="requestCloseProposal('propose-recurring-journals', 'Recurring journals')"
            >
              <mat-icon class="text-sm leading-none" style="font-size:1rem;width:1rem;height:1rem;">repeat</mat-icon>
              Recurring journals
            </button>
          </div>
          <div class="px-4 py-3 border-b border-border-default bg-surface-base/40">
            <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <h3 class="text-xs font-semibold text-text-primary uppercase tracking-wide">Year-end close</h3>
                <p class="text-xs text-text-muted mt-0.5">
                  Fiscal year {{ closeYear() }} · Revenue and Expense to Retained Earnings
                </p>
              </div>
              <button
                type="button"
                class="inline-flex items-center justify-center gap-1.5 rounded bg-accent px-3 py-2 text-xs font-medium text-accent-on transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                [disabled]="yearEndCloseAction()"
                (click)="postYearEndClose()"
              >
                <mat-icon class="text-sm leading-none" style="font-size:1rem;width:1rem;height:1rem;">account_balance</mat-icon>
                {{ yearEndCloseAction() ? 'Posting close' : 'Post year-end close' }}
              </button>
            </div>
            @if (yearEndCloseError()) {
              <p class="mt-2 text-xs text-confidence-low" role="alert">{{ yearEndCloseError() }}</p>
            }
            @if (yearEndCloseResult()) {
              <div class="mt-3 grid gap-2 md:grid-cols-4">
                <div class="border-l-2 border-emerald-500 bg-surface px-3 py-2">
                  <p class="text-xs uppercase tracking-wide text-text-muted">Journal</p>
                  <p class="mt-1 text-sm font-medium text-text-primary">{{ yearEndCloseResult()!.entry_number }}</p>
                </div>
                <div class="border-l-2 border-border-subtle bg-surface px-3 py-2">
                  <p class="text-xs uppercase tracking-wide text-text-muted">Net income</p>
                  <p class="mt-1 text-sm font-mono text-text-primary">{{ yearEndCloseResult()!.net_income | money }}</p>
                </div>
                <div class="border-l-2 border-border-subtle bg-surface px-3 py-2">
                  <p class="text-xs uppercase tracking-wide text-text-muted">Retained earnings</p>
                  <p class="mt-1 text-sm font-mono text-text-primary">
                    {{ yearEndCloseResult()!.retained_earnings_direction || 'None' }}
                    {{ yearEndCloseResult()!.retained_earnings_amount | money }}
                  </p>
                </div>
                <div class="border-l-2 border-border-subtle bg-surface px-3 py-2">
                  <p class="text-xs uppercase tracking-wide text-text-muted">Closed lines</p>
                  <p class="mt-1 text-sm font-mono text-text-primary">{{ yearEndCloseResult()!.line_count }}</p>
                </div>
              </div>
            }
          </div>
          <div class="px-4 py-3 border-b border-border-default bg-surface-base/40">
            <div class="flex items-center justify-between gap-3 mb-3">
              <div>
                <h3 class="text-xs font-semibold text-text-primary uppercase tracking-wide">Recurring templates</h3>
                <p class="text-xs text-text-muted mt-0.5">Balanced journals generated during month-end close.</p>
              </div>
              <button
                type="button"
                class="inline-flex items-center gap-1.5 border border-border-default bg-surface hover:bg-surface-raised text-text-primary px-3 py-1.5 rounded text-xs transition-colors"
                (click)="openRecurringTemplateForm()"
              >
                <mat-icon class="text-sm leading-none" style="font-size:1rem;width:1rem;height:1rem;">add</mat-icon>
                Template
              </button>
            </div>
            @if (recurringTemplatesLoading()) {
              <p class="text-xs text-text-muted">Loading templates…</p>
            } @else if (recurringTemplatesError()) {
              <p class="text-xs text-confidence-low" role="alert">{{ recurringTemplatesError() }}</p>
            } @else if (recurringTemplates().length === 0) {
              <p class="text-xs text-text-muted">No recurring journal templates yet.</p>
            } @else {
              <div class="grid gap-2 md:grid-cols-2">
                @for (template of recurringTemplates(); track template.id) {
                  <div class="border border-border-subtle rounded bg-surface px-3 py-2">
                    <div class="flex items-start justify-between gap-2">
                      <div class="min-w-0">
                        <p class="text-sm font-medium text-text-primary truncate">{{ template.name }}</p>
                        <p class="text-xs text-text-muted mt-0.5">
                          Day {{ template.schedule_day }} · {{ template.start_period }}
                          @if (template.end_period) {–{{ template.end_period }}}
                          · {{ template.currency }}
                        </p>
                      </div>
                      <span
                        class="rounded px-2 py-0.5 text-xs"
                        [class]="template.is_active ? 'bg-emerald-500/15 text-emerald-300' : 'bg-slate-500/15 text-slate-300'"
                      >{{ template.is_active ? 'Active' : 'Paused' }}</span>
                    </div>
                    <p class="text-xs text-text-disabled mt-1">
                      {{ template.lines.length }} lines · {{ recurringTemplateDebitTotal(template) | money: template.currency }}
                    </p>
                  </div>
                }
              </div>
            }
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
                    @if (row.reason) {
                      <div class="mb-3 border-l-2 border-border-subtle bg-surface px-3 py-2">
                        <p class="text-xs uppercase tracking-wide text-text-muted">Business reason</p>
                        <p class="mt-1 text-sm text-text-primary">{{ row.reason }}</p>
                      </div>
                    }
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
                    <app-decision-timeline entityType="journal_entry" [entityId]="row.id" title="Journal approval timeline" />
                    @if (canPost() && row.reference_type === 'manual') {
                      <div class="mt-4 border-t border-border-subtle pt-3">
                        @if (reversalRowId() !== row.id) {
                          <button
                            type="button"
                            class="inline-flex items-center gap-1.5 rounded border border-border-default bg-surface px-3 py-1.5 text-xs font-medium text-text-primary transition-colors hover:bg-surface-base disabled:opacity-60"
                            [disabled]="reversalAction() === row.id"
                            (click)="openReversalForm(row, $event)"
                          >
                            <mat-icon style="font-size:1rem;width:1rem;height:1rem;">undo</mat-icon>
                            Reverse
                          </button>
                        } @else {
                          <form
                            [formGroup]="reversalForm"
                            (ngSubmit)="submitReversal(row, $event)"
                            class="grid gap-2 md:grid-cols-[10rem_1fr_auto]"
                            novalidate
                          >
                            <input
                              type="date"
                              formControlName="entry_date"
                              class="rounded border border-border-default bg-surface-base px-3 py-2 text-xs text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
                              aria-label="Reversal entry date"
                            />
                            <input
                              type="text"
                              formControlName="reason"
                              maxlength="500"
                              placeholder="Reversal reason"
                              class="rounded border border-border-default bg-surface-base px-3 py-2 text-xs text-text-primary placeholder:text-text-disabled focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
                            />
                            <div class="flex items-center gap-2">
                              <button
                                type="submit"
                                class="inline-flex items-center gap-1.5 rounded bg-accent px-3 py-2 text-xs font-medium text-accent-on transition-colors hover:bg-accent-hover disabled:opacity-60"
                                [disabled]="reversalForm.invalid || reversalAction() === row.id"
                              >
                                <mat-icon style="font-size:1rem;width:1rem;height:1rem;">undo</mat-icon>
                                Post
                              </button>
                              <button
                                type="button"
                                class="rounded px-2 py-2 text-xs text-text-muted transition-colors hover:text-text-primary"
                                (click)="closeReversalForm($event)"
                              >
                                Cancel
                              </button>
                            </div>
                          </form>
                          @if (reversalForm.controls.reason.touched && reversalForm.controls.reason.errors?.['minlength']) {
                            <p class="mt-1 text-xs text-confidence-low">Use at least 10 characters.</p>
                          }
                          @if (reversalError()) {
                            <p class="mt-1 text-xs text-confidence-low" role="alert">{{ reversalError() }}</p>
                          }
                        }
                      </div>
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
            {{ formMode() === 'recurring' ? 'Create Recurring Journal Template' : 'Post Manual Journal Entry' }}
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
          (ngSubmit)="formMode() === 'recurring' ? submitRecurringTemplate() : submitJournal()"
          class="flex-1 overflow-y-auto px-6 py-5 space-y-5"
          novalidate
        >
          <!-- Description -->
          <div>
            <label for="jnl-desc" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
              {{ formMode() === 'recurring' ? 'Template name' : 'Description' }} <span class="text-confidence-low">*</span>
            </label>
            <input
              id="jnl-desc"
              type="text"
              formControlName="description"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
              [placeholder]="formMode() === 'recurring' ? 'e.g. Monthly depreciation' : 'e.g. Month-end payroll accrual'"
            />
            @if (journalForm.controls.description.touched && journalForm.controls.description.errors?.['required']) {
              <p class="text-xs text-confidence-low mt-1">{{ formMode() === 'recurring' ? 'Template name' : 'Description' }} is required.</p>
            }
          </div>

          @if (formMode() === 'journal') {
            <div>
              <label for="jnl-reason" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
                Business reason <span class="text-confidence-low">*</span>
              </label>
              <textarea
                id="jnl-reason"
                formControlName="reason"
                rows="3"
                maxlength="500"
                class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm resize-y"
                placeholder="Explain the business event, evidence reviewed, and why this manual journal is needed"
              ></textarea>
              @if (journalForm.controls.reason.touched && journalForm.controls.reason.errors?.['required']) {
                <p class="text-xs text-confidence-low mt-1">Business reason is required.</p>
              }
              @if (journalForm.controls.reason.touched && journalForm.controls.reason.errors?.['minlength']) {
                <p class="text-xs text-confidence-low mt-1">Use at least 10 characters.</p>
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
          } @else {
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label for="rjt-start" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
                  Start Period <span class="text-confidence-low">*</span>
                </label>
                <input
                  id="rjt-start"
                  type="month"
                  formControlName="start_period"
                  class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
                />
              </div>
              <div>
                <label for="rjt-end" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
                  End Period
                </label>
                <input
                  id="rjt-end"
                  type="month"
                  formControlName="end_period"
                  class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
                />
              </div>
              <div>
                <label for="rjt-day" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
                  Schedule Day <span class="text-confidence-low">*</span>
                </label>
                <input
                  id="rjt-day"
                  type="number"
                  min="1"
                  max="31"
                  formControlName="schedule_day"
                  class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
                />
              </div>
              <div>
                <label for="rjt-currency" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
                  Currency
                </label>
                <input
                  id="rjt-currency"
                  type="text"
                  maxlength="3"
                  formControlName="currency"
                  class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary uppercase focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
                />
              </div>
            </div>
          }

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
              @for (ctrl of linesArray.controls; track $index; let lineIndex = $index) {
                <div [formGroupName]="lineIndex"
                     class="grid grid-cols-[1fr_64px_140px_120px_32px] gap-2 items-start">

                  <!-- Account picker -->
                  <div>
                    <input
                      type="text"
                      formControlName="account_search"
                      [attr.aria-label]="'Account for line ' + (lineIndex + 1)"
                      [attr.id]="'jnl-acct-' + lineIndex"
                      class="w-full px-2.5 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
                      placeholder="Search account…"
                      (input)="onAccountSearch(lineIndex)"
                      autocomplete="off"
                    />
                    <!-- Dropdown suggestions -->
                    @if (activeSuggestionLine() === lineIndex && filteredAccounts().length > 0) {
                      <div
                        class="absolute z-50 mt-1 w-72 bg-surface-raised border border-border-default rounded shadow-xl max-h-52 overflow-y-auto"
                        role="listbox"
                        [attr.aria-label]="'Account suggestions for line ' + (lineIndex + 1)"
                      >
                        @for (acct of filteredAccounts(); track acct.id) {
                          <button
                            type="button"
                            role="option"
                            class="w-full text-left px-3 py-2.5 text-sm hover:bg-surface transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                            (click)="selectAccount(lineIndex, acct)"
                          >
                            <span class="font-mono text-xs text-text-muted mr-2">{{ acct.code }}</span>
                            <span class="text-text-primary">{{ acct.name }}</span>
                            <span class="ml-2 text-xs text-text-disabled capitalize">{{ acct.account_type }}</span>
                          </button>
                        }
                      </div>
                    }
                    @if (getLineControl(lineIndex, 'account_id').touched && !getLineControl(lineIndex, 'account_id').value) {
                      <p class="text-xs text-confidence-low mt-0.5">Select an account.</p>
                    }
                  </div>

                  <!-- Direction (DR / CR) -->
                  <div>
                    <select
                      formControlName="direction"
                      [attr.aria-label]="'Direction for line ' + (lineIndex + 1)"
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
                      [attr.aria-label]="'Amount for line ' + (lineIndex + 1)"
                      class="w-full px-2.5 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm font-mono text-right"
                      placeholder="0.00"
                      (input)="recomputeTotals()"
                    />
                    @if (getLineControl(lineIndex, 'amount').touched && getLineControl(lineIndex, 'amount').errors?.['required']) {
                      <p class="text-xs text-confidence-low mt-0.5">Required.</p>
                    }
                    @if (getLineControl(lineIndex, 'amount').touched && getLineControl(lineIndex, 'amount').errors?.['pattern']) {
                      <p class="text-xs text-confidence-low mt-0.5">Enter a valid number.</p>
                    }
                  </div>

                  <!-- Line description -->
                  <div>
                    <input
                      type="text"
                      formControlName="line_description"
                      [attr.aria-label]="'Note for line ' + (lineIndex + 1)"
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
                      [attr.aria-label]="'Remove line ' + (lineIndex + 1)"
                      (click)="removeLine(lineIndex)"
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
            (click)="formMode() === 'recurring' ? submitRecurringTemplate() : submitJournal()"
          >
            @if (submitting()) {
              {{ formMode() === 'recurring' ? 'Creating…' : 'Posting…' }}
            } @else {
              {{ formMode() === 'recurring' ? 'Create Template' : 'Post Journal Entry' }}
            }
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
  closePackage = signal<ClosePackage | null>(null);
  closePackageLoading = signal(false);
  closePackageError = signal<string | null>(null);
  yearEndCloseAction = signal(false);
  yearEndCloseResult = signal<YearEndCloseResponse | null>(null);
  yearEndCloseError = signal<string | null>(null);
  closeOverrideAction = signal(false);
  closeOverrideError = signal<string | null>(null);
  recurringTemplates = signal<RecurringJournalTemplate[]>([]);
  recurringTemplatesLoading = signal(false);
  recurringTemplatesError = signal<string | null>(null);
  closeYear = computed(() => this.closePeriod().slice(0, 4));
  completedCloseTasks = computed(() =>
    this.closeTasks().filter(task => ['done', 'waived'].includes(task.status)).length,
  );

  // RBAC: read role from localStorage (set by login flow).
  // The backend enforces this too; this is only a UI affordance.
  canPost = computed(() => {
    try {
      const raw = localStorage.getItem('aethos_role');
      return this.roleRank(raw) >= this.roleRank('manager');
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
  formMode = signal<JournalFormMode>('journal');
  showForm  = signal(false);
  submitting = signal(false);
  formError  = signal<string | null>(null);
  successToast = signal<string | null>(null);
  reversalRowId = signal<string | null>(null);
  reversalAction = signal<string | null>(null);
  reversalError = signal<string | null>(null);

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
    reason:      [''],
    entry_date:  ['', [Validators.required]],
    reference:   [''],
    start_period: ['', [Validators.required, Validators.pattern(/^\d{4}-\d{2}$/)]],
    end_period:   [''],
    schedule_day: [31, [Validators.required, Validators.min(1), Validators.max(31)]],
    currency:     ['USD', [Validators.required, Validators.pattern(/^[A-Za-z]{3}$/)]],
    lines: this.fb.array([
      this.buildLine(),
      this.buildLine('CR'),
    ]),
  });

  closeOverrideForm = this.fb.nonNullable.group({
    blocker_code: ['close_tasks', [Validators.required]],
    reason: ['', [Validators.required, Validators.minLength(10), Validators.maxLength(2000)]],
  });

  reversalForm = this.fb.nonNullable.group({
    entry_date: [new Date().toISOString().split('T')[0], [Validators.required]],
    reason: ['', [Validators.required, Validators.minLength(10), Validators.maxLength(500)]],
  });

  get linesArray(): FormArray {
    return this.journalForm.get('lines') as FormArray;
  }

  // ── Lifecycle ────────────────────────────────────────────────────────
  ngOnInit(): void {
    this.loadEntries();
    this.loadCloseTasks();
    this.loadRecurringTemplates();
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

  loadClosePackage(): void {
    this.closePackageLoading.set(true);
    this.closePackageError.set(null);
    this.http.get<ClosePackage>(
      `/api/v1/accounting/periods/${this.closePeriod()}/close-package`,
    ).subscribe({
      next: (res) => {
        this.closePackage.set(res);
        this.syncCloseOverrideDefault(res);
        this.closePackageLoading.set(false);
      },
      error: (err: unknown) => {
        this.closePackageError.set(userMessageForError(err, 'Close Package'));
        this.closePackageLoading.set(false);
      },
    });
  }

  loadRecurringTemplates(): void {
    this.recurringTemplatesLoading.set(true);
    this.recurringTemplatesError.set(null);
    this.http.get<{ templates: RecurringJournalTemplate[] }>(
      '/api/v1/accounting/recurring-journal-templates',
    ).subscribe({
      next: (res) => {
        this.recurringTemplates.set(res.templates ?? []);
        this.recurringTemplatesLoading.set(false);
      },
      error: (err: unknown) => {
        this.recurringTemplatesError.set(userMessageForError(err, 'Recurring Templates'));
        this.recurringTemplatesLoading.set(false);
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

  createCloseOverride(): void {
    if (this.closeOverrideForm.invalid) {
      this.closeOverrideForm.markAllAsTouched();
      return;
    }
    const value = this.closeOverrideForm.getRawValue();
    const option = this.closeOverrideOptions().find(row => row.code === value.blocker_code);
    this.closeOverrideAction.set(true);
    this.closeOverrideError.set(null);
    this.http.post<CloseOverride>(
      `/api/v1/accounting/periods/${this.closePeriod()}/close-overrides`,
      {
        blocker_code: value.blocker_code,
        reason: value.reason.trim(),
        blocker_ref: {
          source: 'accounting_close_panel',
          blocker_status: option?.status,
          blocker_summary: option?.summary,
        },
      },
    ).subscribe({
      next: (override) => {
        this.closeOverrideAction.set(false);
        this.closeOverrideForm.patchValue({ reason: '' });
        this.successToast.set(`Close override recorded for ${this.blockerLabel(override.blocker_code)}.`);
        setTimeout(() => this.successToast.set(null), 5000);
        this.loadClosePackage();
        this.loadCloseTasks();
      },
      error: (err: unknown) => {
        this.closeOverrideError.set(userMessageForError(err, 'Close Override'));
        this.closeOverrideAction.set(false);
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

  postYearEndClose(): void {
    const year = this.closeYear();
    this.yearEndCloseAction.set(true);
    this.yearEndCloseError.set(null);
    this.http.post<YearEndCloseResponse>(
      `/api/v1/accounting/years/${year}/year-end-close`,
      {},
    ).subscribe({
      next: (res) => {
        this.yearEndCloseResult.set(res);
        this.yearEndCloseAction.set(false);
        this.successToast.set(`Year-end close ${res.entry_number} posted to retained earnings.`);
        setTimeout(() => this.successToast.set(null), 5000);
        this.loadEntries();
        if (this.closePackage()) this.loadClosePackage();
      },
      error: (err: unknown) => {
        this.yearEndCloseError.set(
          yearEndCloseErrorMessage(err) ?? userMessageForError(err, 'Year-end Close'),
        );
        this.yearEndCloseAction.set(false);
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
    this.formMode.set('journal');
    const today = new Date().toISOString().split('T')[0];
    // Reset to 2 lines
    this.journalForm.reset({
      description: '',
      reason: '',
      entry_date: today,
      reference: '',
      start_period: today.slice(0, 7),
      end_period: '',
      schedule_day: 31,
      currency: 'USD',
    });
    // Clear lines array and add 2 fresh lines
    while (this.linesArray.length > 0) this.linesArray.removeAt(0);
    this.linesArray.push(this.buildLine('DR'));
    this.linesArray.push(this.buildLine('CR'));
    this.journalForm.controls.reason.setValidators([
      Validators.required,
      Validators.minLength(10),
      Validators.maxLength(500),
    ]);
    this.journalForm.controls.reason.updateValueAndValidity();

    this.formError.set(null);
    this.drTotal.set('0.00');
    this.crTotal.set('0.00');
    this.activeSuggestionLine.set(null);
    this.filteredAccounts.set([]);

    // Load chart of accounts
    this.loadAccounts();
    this.showForm.set(true);
  }

  openRecurringTemplateForm(): void {
    this.formMode.set('recurring');
    const today = new Date().toISOString().split('T')[0];
    this.journalForm.reset({
      description: '',
      reason: '',
      entry_date: today,
      reference: '',
      start_period: this.closePeriod(),
      end_period: '',
      schedule_day: 31,
      currency: 'USD',
    });
    while (this.linesArray.length > 0) this.linesArray.removeAt(0);
    this.linesArray.push(this.buildLine('DR'));
    this.linesArray.push(this.buildLine('CR'));
    this.journalForm.controls.reason.clearValidators();
    this.journalForm.controls.reason.updateValueAndValidity();

    this.formError.set(null);
    this.drTotal.set('0.00');
    this.crTotal.set('0.00');
    this.activeSuggestionLine.set(null);
    this.filteredAccounts.set([]);

    this.loadAccounts();
    this.showForm.set(true);
  }

  closeForm(): void {
    this.showForm.set(false);
    this.activeSuggestionLine.set(null);
    this.filteredAccounts.set([]);
  }

  openReversalForm(row: JournalEntry, event: Event): void {
    event.stopPropagation();
    this.reversalRowId.set(row.id);
    this.reversalError.set(null);
    this.reversalForm.reset({
      entry_date: new Date().toISOString().split('T')[0],
      reason: '',
    });
  }

  closeReversalForm(event?: Event): void {
    event?.stopPropagation();
    this.reversalRowId.set(null);
    this.reversalError.set(null);
  }

  submitReversal(row: JournalEntry, event?: Event): void {
    event?.stopPropagation();
    if (this.reversalForm.invalid) {
      this.reversalForm.markAllAsTouched();
      return;
    }
    const value = this.reversalForm.getRawValue();
    this.reversalAction.set(row.id);
    this.reversalError.set(null);
    this.http.post<JournalEntry>(
      `/api/v1/accounting/journal-entries/${row.id}/reverse`,
      {
        entry_date: value.entry_date,
        reason: value.reason.trim(),
      },
    ).subscribe({
      next: (created) => {
        this.entries.update(list => [created, ...list]);
        this.reversalAction.set(null);
        this.closeReversalForm();
        this.successToast.set(`Reversal ${created.entry_number} posted.`);
        setTimeout(() => this.successToast.set(null), 5000);
      },
      error: (err: unknown) => {
        this.reversalError.set(userMessageForError(err, 'Manual Journal Reversal'));
        this.reversalAction.set(null);
      },
    });
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
      reason:      v.reason.trim(),
      entry_date:  v.entry_date,
      reference:   v.reference || undefined,
      lines: v.lines.map(l => ({
        direction:   l.direction,
        account_id:  l.account_id,
        amount:      parseFloat(l.amount).toFixed(2),
        description: l.line_description || undefined,
      })),
    };

    this.http.post<ManualJournalSubmitResponse>('/api/v1/accounting/journal-entries', payload).subscribe({
      next: (created) => {
        if (isManualJournalPendingApproval(created)) {
          this.submitting.set(false);
          this.closeForm();
          this.successToast.set(
            `Manual journal routed to Inbox for ${created.required_approval_role} approval.`,
          );
          setTimeout(() => this.successToast.set(null), 5000);
          return;
        }
        this.entries.update(list => [created, ...list]);
        this.submitting.set(false);
        this.closeForm();
        this.successToast.set(`Journal ${created.entry_number} posted successfully.`);
        setTimeout(() => this.successToast.set(null), 5000);
      },
      error: (err: unknown) => {
        this.submitting.set(false);
        const msg = journalErrorMessage(err) ?? userMessageForError(err, 'Journal Entry');
        this.formError.set(msg);
      },
    });
  }

  submitRecurringTemplate(): void {
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
      name: v.description,
      description: v.reference || undefined,
      schedule_day: Number(v.schedule_day),
      start_period: v.start_period,
      end_period: v.end_period || undefined,
      currency: v.currency.toUpperCase(),
      lines: v.lines.map(l => ({
        direction: l.direction,
        account_id: l.account_id,
        amount: parseFloat(l.amount).toFixed(2),
        description: l.line_description || undefined,
      })),
    };

    this.http.post<RecurringJournalTemplate>(
      '/api/v1/accounting/recurring-journal-templates',
      payload,
    ).subscribe({
      next: (created) => {
        this.recurringTemplates.update(list => [...list, created].sort((a, b) => a.name.localeCompare(b.name)));
        this.submitting.set(false);
        this.closeForm();
        this.successToast.set(`Recurring template ${created.name} created.`);
        setTimeout(() => this.successToast.set(null), 5000);
      },
      error: (err: unknown) => {
        this.submitting.set(false);
        let msg = 'Could not create recurring journal template. Please try again.';
        if (isApiError(err) && typeof err.error?.detail === 'string') {
          msg = err.error.detail;
        } else {
          msg = userMessageForError(err, 'Recurring Template');
        }
        this.formError.set(msg);
      },
    });
  }

  recurringTemplateDebitTotal(template: RecurringJournalTemplate): string {
    const total = template.lines
      .filter(line => line.direction === 'DR')
      .reduce((sum, line) => sum + (parseFloat(line.amount) || 0), 0);
    return total.toFixed(2);
  }

  closeOverrideOptions(): CloseOverrideOption[] {
    const checklist = this.closePackage()?.close_status?.checklist ?? [];
    const options = checklist
      .filter(item => CLOSE_OVERRIDE_LABELS[item.code])
      .filter(item => item.blocking || item.status === 'blocked' || item.status === 'overridden')
      .map(item => ({
        code: item.code,
        label: item.label || this.blockerLabel(item.code),
        summary: item.summary,
        status: item.status,
      }));
    if (options.length > 0) return options;
    return Object.entries(CLOSE_OVERRIDE_LABELS).map(([code, label]) => ({
      code,
      label,
      summary: 'Manual controller override.',
      status: 'manual',
    }));
  }

  syncCloseOverrideDefault(pkg: ClosePackage): void {
    const selected = this.closeOverrideForm.controls.blocker_code.value;
    const options = this.closeOverrideOptions();
    if (!options.some(option => option.code === selected)) {
      this.closeOverrideForm.patchValue({ blocker_code: options[0]?.code ?? 'close_tasks' });
    }
    if (pkg.close_status?.status === 'ready') {
      this.closeOverrideError.set(null);
    }
  }

  blockerLabel(code: string): string {
    return CLOSE_OVERRIDE_LABELS[code] ?? code.replace(/_/g, ' ');
  }

  formatOverrideTimestamp(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  closeReadinessAreas(): CloseReadinessArea[] {
    const evidence = this.closePackage()?.readiness_evidence;
    if (!evidence) return [];
    return [
      this.readinessArea('ar', 'AR', 'open_total', 'blocker_count'),
      this.readinessArea('ap', 'AP', 'open_total', 'blocker_count'),
      this.readinessArea('wip', 'WIP', 'open_total', 'project_count'),
      this.readinessArea('gl', 'GL', 'unposted_journal_count', 'trial_balance_balanced'),
      this.readinessArea('approvals', 'Approvals', 'pending_review_count', 'incomplete_task_count'),
      this.readinessArea('overrides', 'Overrides', 'count', 'review_path'),
    ].filter((area): area is CloseReadinessArea => area !== null);
  }

  readinessArea(
    key: string,
    label: string,
    primaryMetric: string,
    secondaryMetric: string,
  ): CloseReadinessArea | null {
    const area = this.closePackage()?.readiness_evidence?.[key];
    if (!area) return null;
    const status = String(area['status'] ?? (key === 'overrides' ? 'info' : 'ready'));
    const primary = area[primaryMetric];
    const secondary = area[secondaryMetric];
    return {
      key,
      label,
      status,
      metric: this.readinessMetric(primaryMetric, primary, secondaryMetric, secondary),
    };
  }

  readinessMetric(
    primaryLabel: string,
    primary: unknown,
    secondaryLabel: string,
    secondary: unknown,
  ): string {
    const primaryText = primary === null || primary === undefined ? '0' : String(primary);
    if (typeof secondary === 'boolean') {
      return `${primaryLabel.replace(/_/g, ' ')} ${primaryText} · ${secondary ? 'balanced' : 'unbalanced'}`;
    }
    if (secondary === null || secondary === undefined || secondaryLabel === 'review_path') {
      return `${primaryLabel.replace(/_/g, ' ')} ${primaryText}`;
    }
    return `${primaryLabel.replace(/_/g, ' ')} ${primaryText} · ${secondaryLabel.replace(/_/g, ' ')} ${String(secondary)}`;
  }

  closePackageValue(
    section: 'gl_summary' | 'previous_gl_summary' | 'working_capital',
    key: string,
  ): string {
    const pkg = this.closePackage();
    const value = pkg?.[section]?.[key];
    if (value === null || value === undefined) return '0.00';
    return String(value);
  }

  varianceSeverityClass(severity: string | undefined): string {
    switch (severity) {
      case 'blocker': return 'bg-red-500/15 text-red-300';
      case 'high': return 'bg-amber-500/15 text-amber-300';
      case 'medium': return 'bg-blue-500/15 text-blue-300';
      default: return 'bg-slate-500/15 text-slate-300';
    }
  }

  readinessStatusClass(status: string): string {
    switch (status) {
      case 'blocked': return 'bg-red-500/15 text-red-300';
      case 'attention': return 'bg-amber-500/15 text-amber-300';
      case 'overridden': return 'bg-blue-500/15 text-blue-300';
      case 'ready': return 'bg-emerald-500/15 text-emerald-300';
      default: return 'bg-slate-500/15 text-slate-300';
    }
  }

  // ── Badge helpers ─────────────────────────────────────────────────────
  typeBadgeClass(type: string): string {
    switch (type) {
      case 'manual':  return 'bg-purple-500/20 text-purple-300';
      case 'auto':    return 'bg-slate-500/20 text-slate-300';
      case 'invoice': return 'bg-blue-500/20 text-blue-300';
      case 'bill':    return 'bg-amber-500/20 text-amber-300';
      case 'payment': return 'bg-emerald-500/20 text-emerald-300';
      case 'year_end_close': return 'bg-cyan-500/20 text-cyan-300';
      default:        return 'bg-surface text-text-muted';
    }
  }

  private roleRank(role: string | null | undefined): number {
    const ranks: Record<string, number> = {
      owner: 5,
      admin: 4,
      manager: 3,
      member: 2,
      viewer: 1,
      employee: 0,
    };
    return ranks[role ?? 'viewer'] ?? 1;
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
