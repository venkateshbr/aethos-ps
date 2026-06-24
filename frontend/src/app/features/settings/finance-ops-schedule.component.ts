import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';

import { AuthService } from '../../core/services/auth.service';

type FinanceOpsCadence = 'daily' | 'weekly';
type FinanceOpsPeriodMode = 'current_month' | 'previous_month';

interface FinanceOpsSchedule {
  tenant_id: string;
  is_enabled: boolean;
  cadence: FinanceOpsCadence;
  run_hour_utc: number;
  run_weekday_utc: number;
  timezone: string;
  period_mode: FinanceOpsPeriodMode;
  lookback_limit: number;
  stale_after_hours: number;
  high_risk_stale_after_hours: number;
  escalation_enabled: boolean;
  is_seeded_default: boolean;
  created_at: string | null;
  updated_at: string | null;
}

const WEEKDAYS = [
  { value: 0, label: 'Monday' },
  { value: 1, label: 'Tuesday' },
  { value: 2, label: 'Wednesday' },
  { value: 3, label: 'Thursday' },
  { value: 4, label: 'Friday' },
  { value: 5, label: 'Saturday' },
  { value: 6, label: 'Sunday' },
] as const;

const CADENCES = [
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
] as const;

const PERIOD_MODES = [
  { value: 'current_month', label: 'Current month' },
  { value: 'previous_month', label: 'Previous month' },
] as const;

@Component({
  selector: 'app-finance-ops-schedule',
  standalone: true,
  imports: [ReactiveFormsModule, MatIconModule],
  template: `
    <div class="overflow-hidden rounded-lg border border-border-default bg-surface-raised">
      <div class="flex flex-col gap-3 border-b border-border-default px-6 py-4 lg:flex-row lg:items-center lg:justify-between">
        <div class="flex min-w-0 items-center gap-2">
          <mat-icon class="flex-none text-indigo-400">event_repeat</mat-icon>
          <div class="min-w-0">
            <h3 class="truncate text-base font-semibold text-text-primary">Finance Ops Manager Schedule</h3>
            @if (schedule()) {
              <div class="mt-1 flex flex-wrap items-center gap-2 text-xs text-text-muted">
                <span>{{ schedule()!.is_seeded_default ? 'Default schedule' : 'Tenant schedule' }}</span>
                <span aria-hidden="true">/</span>
                <span>{{ schedule()!.is_enabled ? 'Enabled' : 'Paused' }}</span>
                @if (schedule()!.updated_at; as updatedAt) {
                  <span aria-hidden="true">/</span>
                  <span>Updated {{ formatDate(updatedAt) }}</span>
                }
              </div>
            }
          </div>
        </div>

        <button
          type="button"
          (click)="load()"
          class="inline-flex h-9 items-center gap-1.5 self-start rounded border border-border-default px-3 text-sm font-medium text-text-secondary transition-colors hover:border-accent/60 hover:text-text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent lg:self-auto"
        >
          <mat-icon style="font-size:1rem;width:1rem;height:1rem;" aria-hidden="true">refresh</mat-icon>
          Refresh
        </button>
      </div>

      @if (loading()) {
        <div class="px-6 py-5 animate-pulse" aria-busy="true" aria-label="Loading Finance Ops Manager schedule">
          <div class="mb-4 h-4 w-56 rounded bg-surface"></div>
          <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            @for (i of [1, 2, 3, 4]; track i) {
              <div class="h-16 rounded bg-surface"></div>
            }
          </div>
        </div>
      } @else {
        <form [formGroup]="form" (ngSubmit)="save()" class="space-y-5 px-6 py-5" novalidate>
          <div class="grid gap-4 lg:grid-cols-2">
            <label class="flex items-center justify-between gap-4 rounded border border-border-default bg-surface-base px-4 py-3">
              <span class="text-sm font-medium text-text-primary">Enable scheduled run</span>
              <input
                type="checkbox"
                formControlName="is_enabled"
                class="h-4 w-4 rounded border-border-default bg-surface-base text-accent focus:ring-accent"
              />
            </label>

            <label class="flex items-center justify-between gap-4 rounded border border-border-default bg-surface-base px-4 py-3">
              <span class="text-sm font-medium text-text-primary">Escalate stale approvals</span>
              <input
                type="checkbox"
                formControlName="escalation_enabled"
                class="h-4 w-4 rounded border-border-default bg-surface-base text-accent focus:ring-accent"
              />
            </label>
          </div>

          <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <label class="block">
              <span class="mb-2 block text-xs uppercase tracking-wide text-text-muted">Cadence</span>
              <select
                formControlName="cadence"
                class="w-full rounded border border-border-default bg-surface-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              >
                @for (option of cadenceOptions; track option.value) {
                  <option [value]="option.value">{{ option.label }}</option>
                }
              </select>
            </label>

            @if (form.controls.cadence.value === 'weekly') {
              <label class="block">
                <span class="mb-2 block text-xs uppercase tracking-wide text-text-muted">Run day</span>
                <select
                  formControlName="run_weekday_utc"
                  class="w-full rounded border border-border-default bg-surface-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
                >
                  @for (day of weekdayOptions; track day.value) {
                    <option [ngValue]="day.value">{{ day.label }}</option>
                  }
                </select>
              </label>
            }

            <label class="block">
              <span class="mb-2 block text-xs uppercase tracking-wide text-text-muted">Run hour UTC</span>
              <input
                type="number"
                min="0"
                max="23"
                formControlName="run_hour_utc"
                class="w-full rounded border border-border-default bg-surface-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </label>

            <label class="block">
              <span class="mb-2 block text-xs uppercase tracking-wide text-text-muted">Timezone</span>
              <input
                type="text"
                maxlength="64"
                formControlName="timezone"
                class="w-full rounded border border-border-default bg-surface-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </label>

            <label class="block">
              <span class="mb-2 block text-xs uppercase tracking-wide text-text-muted">Period</span>
              <select
                formControlName="period_mode"
                class="w-full rounded border border-border-default bg-surface-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              >
                @for (option of periodOptions; track option.value) {
                  <option [value]="option.value">{{ option.label }}</option>
                }
              </select>
            </label>

            <label class="block">
              <span class="mb-2 block text-xs uppercase tracking-wide text-text-muted">Work item limit</span>
              <input
                type="number"
                min="1"
                max="25"
                formControlName="lookback_limit"
                class="w-full rounded border border-border-default bg-surface-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </label>

            <label class="block">
              <span class="mb-2 block text-xs uppercase tracking-wide text-text-muted">High-risk stale hours</span>
              <input
                type="number"
                min="1"
                max="720"
                formControlName="high_risk_stale_after_hours"
                class="w-full rounded border border-border-default bg-surface-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </label>

            <label class="block">
              <span class="mb-2 block text-xs uppercase tracking-wide text-text-muted">Stale hours</span>
              <input
                type="number"
                min="1"
                max="720"
                formControlName="stale_after_hours"
                class="w-full rounded border border-border-default bg-surface-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </label>
          </div>

          @if (schedule()) {
            <div class="grid gap-3 rounded border border-border-default bg-surface-base px-4 py-3 text-xs text-text-muted md:grid-cols-3">
              <div>
                <div class="uppercase tracking-wide text-text-disabled">Next cadence</div>
                <div class="mt-1 text-text-secondary">{{ cadenceLabel(form.controls.cadence.value) }} at {{ formatHour(form.controls.run_hour_utc.value) }}</div>
              </div>
              <div>
                <div class="uppercase tracking-wide text-text-disabled">Review period</div>
                <div class="mt-1 text-text-secondary">{{ periodLabel(form.controls.period_mode.value) }}</div>
              </div>
              <div>
                <div class="uppercase tracking-wide text-text-disabled">Approval escalation</div>
                <div class="mt-1 text-text-secondary">{{ form.controls.escalation_enabled.value ? 'Enabled' : 'Paused' }}</div>
              </div>
            </div>
          }

          @if (!canEdit()) {
            <div class="rounded border border-border-default bg-surface-base px-3 py-2 text-sm text-text-muted" role="status">
              Schedule changes require Admin or Owner.
            </div>
          }

          @if (staleWindowInvalid()) {
            <div class="rounded border border-confidence-low/30 bg-confidence-low/10 px-3 py-2 text-sm text-confidence-low" role="alert">
              High-risk stale hours must be less than or equal to stale hours.
            </div>
          }

          @if (loadError()) {
            <div class="rounded border border-confidence-low/30 bg-confidence-low/10 px-3 py-2 text-sm text-confidence-low" role="alert">
              Failed to load Finance Ops Manager schedule.
            </div>
          }

          @if (saveError()) {
            <div class="rounded border border-confidence-low/30 bg-confidence-low/10 px-3 py-2 text-sm text-confidence-low" role="alert">
              Failed to save Finance Ops Manager schedule.
            </div>
          }

          @if (saved()) {
            <div class="rounded border border-accent/30 bg-accent/10 px-3 py-2 text-sm text-accent-light" role="status">
              Finance Ops Manager schedule saved.
            </div>
          }

          <div class="flex justify-end">
            <button
              type="submit"
              [disabled]="!canEdit() || form.invalid || staleWindowInvalid() || saving()"
              class="inline-flex items-center gap-2 rounded bg-accent px-4 py-2 text-sm font-medium text-accent-on transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              @if (saving()) {
                <span>Saving...</span>
              } @else {
                <mat-icon style="font-size:1rem;width:1rem;height:1rem;" aria-hidden="true">save</mat-icon>
                <span>Save Schedule</span>
              }
            </button>
          </div>
        </form>
      }
    </div>
  `,
  styles: [':host { display: block; }'],
})
export class FinanceOpsScheduleComponent implements OnInit {
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);

  readonly cadenceOptions = CADENCES;
  readonly weekdayOptions = WEEKDAYS;
  readonly periodOptions = PERIOD_MODES;

  loading = signal(true);
  saving = signal(false);
  loadError = signal(false);
  saveError = signal(false);
  saved = signal(false);
  schedule = signal<FinanceOpsSchedule | null>(null);

  canEdit = computed(() => {
    const role = this.auth.role();
    return role === 'admin' || role === 'owner';
  });

  form = this.fb.nonNullable.group({
    is_enabled: [true],
    cadence: ['daily' as FinanceOpsCadence, [Validators.required]],
    run_hour_utc: [7, [Validators.required, Validators.min(0), Validators.max(23)]],
    run_weekday_utc: [0, [Validators.required, Validators.min(0), Validators.max(6)]],
    timezone: ['UTC', [Validators.required, Validators.maxLength(64)]],
    period_mode: ['current_month' as FinanceOpsPeriodMode, [Validators.required]],
    lookback_limit: [10, [Validators.required, Validators.min(1), Validators.max(25)]],
    stale_after_hours: [24, [Validators.required, Validators.min(1), Validators.max(720)]],
    high_risk_stale_after_hours: [4, [Validators.required, Validators.min(1), Validators.max(720)]],
    escalation_enabled: [true],
  });

  ngOnInit(): void {
    this.applyEditState();
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.loadError.set(false);
    this.saved.set(false);
    this.http.get<FinanceOpsSchedule>('/api/v1/agents/finance-ops/schedule').subscribe({
      next: (schedule) => {
        this.applySchedule(schedule);
        this.loading.set(false);
      },
      error: () => {
        this.loadError.set(true);
        this.loading.set(false);
      },
    });
  }

  save(): void {
    if (!this.canEdit() || this.form.invalid || this.staleWindowInvalid()) return;
    this.saving.set(true);
    this.saveError.set(false);
    this.saved.set(false);
    const value = this.form.getRawValue();
    this.http.put<FinanceOpsSchedule>('/api/v1/agents/finance-ops/schedule', {
      is_enabled: value.is_enabled,
      cadence: value.cadence,
      run_hour_utc: Number(value.run_hour_utc),
      run_weekday_utc: Number(value.run_weekday_utc),
      timezone: value.timezone.trim(),
      period_mode: value.period_mode,
      lookback_limit: Number(value.lookback_limit),
      stale_after_hours: Number(value.stale_after_hours),
      high_risk_stale_after_hours: Number(value.high_risk_stale_after_hours),
      escalation_enabled: value.escalation_enabled,
    }).subscribe({
      next: (schedule) => {
        this.applySchedule(schedule);
        this.saving.set(false);
        this.saved.set(true);
      },
      error: () => {
        this.saving.set(false);
        this.saveError.set(true);
      },
    });
  }

  staleWindowInvalid(): boolean {
    const value = this.form.getRawValue();
    return Number(value.high_risk_stale_after_hours) > Number(value.stale_after_hours);
  }

  cadenceLabel(value: FinanceOpsCadence | string): string {
    return this.cadenceOptions.find(option => option.value === value)?.label ?? String(value);
  }

  periodLabel(value: FinanceOpsPeriodMode | string): string {
    return this.periodOptions.find(option => option.value === value)?.label ?? String(value);
  }

  formatHour(value: number): string {
    const hour = Math.max(0, Math.min(23, Number(value) || 0));
    return `${String(hour).padStart(2, '0')}:00 UTC`;
  }

  formatDate(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  private applySchedule(schedule: FinanceOpsSchedule): void {
    this.schedule.set(schedule);
    this.form.patchValue({
      is_enabled: schedule.is_enabled,
      cadence: schedule.cadence,
      run_hour_utc: schedule.run_hour_utc,
      run_weekday_utc: schedule.run_weekday_utc,
      timezone: schedule.timezone,
      period_mode: schedule.period_mode,
      lookback_limit: schedule.lookback_limit,
      stale_after_hours: schedule.stale_after_hours,
      high_risk_stale_after_hours: schedule.high_risk_stale_after_hours,
      escalation_enabled: schedule.escalation_enabled,
    });
    this.applyEditState();
  }

  private applyEditState(): void {
    if (this.canEdit()) {
      this.form.enable({ emitEvent: false });
    } else {
      this.form.disable({ emitEvent: false });
    }
  }
}
