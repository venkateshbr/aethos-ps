import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';

import { AuthService } from '../../core/services/auth.service';

type ApprovalRole = 'approver' | 'manager' | 'admin' | 'owner';
type ApprovalPolicySource = 'system_default' | 'tenant_default';

interface ApprovalPolicy {
  tenant_id: string | null;
  policy_source: ApprovalPolicySource;
  money_out_default_role: ApprovalRole;
  money_out_owner_threshold: string;
  money_out_owner_role: ApprovalRole;
  accounting_role: ApprovalRole;
  manual_journal_approval_threshold: string;
  money_in_role: ApprovalRole;
  draft_role: ApprovalRole;
  external_send_role: ApprovalRole;
  high_risk_role: ApprovalRole;
  created_at: string | null;
  updated_at: string | null;
}

const ROLE_OPTIONS: { value: ApprovalRole; label: string }[] = [
  { value: 'approver', label: 'Finance Approver' },
  { value: 'manager', label: 'Finance Ops Manager' },
  { value: 'admin', label: 'Controller / Admin' },
  { value: 'owner', label: 'Owner / CFO' },
];

const ADMIN_OWNER_OPTIONS = ROLE_OPTIONS.filter(option => ['admin', 'owner'].includes(option.value));

@Component({
  selector: 'app-approval-policy',
  standalone: true,
  imports: [ReactiveFormsModule, MatIconModule],
  template: `
    <div class="overflow-hidden rounded-lg border border-border-default bg-surface-raised">
      <div class="flex flex-col gap-3 border-b border-border-default px-6 py-4 lg:flex-row lg:items-center lg:justify-between">
        <div class="flex min-w-0 items-center gap-2">
          <mat-icon class="flex-none text-emerald-400">verified_user</mat-icon>
          <div class="min-w-0">
            <h3 class="truncate text-base font-semibold text-text-primary">Approval Policy Matrix</h3>
            @if (policy()) {
              <div class="mt-1 flex flex-wrap items-center gap-2 text-xs text-text-muted">
                <span>{{ policySourceLabel(policy()!.policy_source) }}</span>
                @if (policy()!.updated_at; as updatedAt) {
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
        <div class="px-6 py-5 animate-pulse" aria-busy="true" aria-label="Loading approval policy">
          <div class="mb-4 h-4 w-56 rounded bg-surface"></div>
          <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            @for (i of [1, 2, 3, 4, 5, 6]; track i) {
              <div class="h-16 rounded bg-surface"></div>
            }
          </div>
        </div>
      } @else {
        <form [formGroup]="form" (ngSubmit)="save()" class="space-y-5 px-6 py-5" novalidate>
          <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            <label class="block">
              <span class="mb-2 block text-xs uppercase tracking-wide text-text-muted">Money-out default</span>
              <select
                formControlName="money_out_default_role"
                class="w-full rounded border border-border-default bg-surface-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              >
                @for (option of adminOwnerOptions; track option.value) {
                  <option [value]="option.value">{{ option.label }}</option>
                }
              </select>
            </label>

            <label class="block">
              <span class="mb-2 block text-xs uppercase tracking-wide text-text-muted">Owner threshold</span>
              <input
                type="number"
                min="0"
                step="0.01"
                formControlName="money_out_owner_threshold"
                class="w-full rounded border border-border-default bg-surface-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </label>

            <label class="block">
              <span class="mb-2 block text-xs uppercase tracking-wide text-text-muted">Accounting</span>
              <select
                formControlName="accounting_role"
                class="w-full rounded border border-border-default bg-surface-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              >
                @for (option of adminOwnerOptions; track option.value) {
                  <option [value]="option.value">{{ option.label }}</option>
                }
              </select>
            </label>

            <label class="block">
              <span class="mb-2 block text-xs uppercase tracking-wide text-text-muted">Manual journal threshold</span>
              <input
                type="number"
                min="0"
                step="0.01"
                formControlName="manual_journal_approval_threshold"
                class="w-full rounded border border-border-default bg-surface-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </label>

            <label class="block">
              <span class="mb-2 block text-xs uppercase tracking-wide text-text-muted">Money-in drafts</span>
              <select
                formControlName="money_in_role"
                class="w-full rounded border border-border-default bg-surface-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              >
                @for (option of roleOptions; track option.value) {
                  <option [value]="option.value">{{ option.label }}</option>
                }
              </select>
            </label>

            <label class="block">
              <span class="mb-2 block text-xs uppercase tracking-wide text-text-muted">Draft actions</span>
              <select
                formControlName="draft_role"
                class="w-full rounded border border-border-default bg-surface-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              >
                @for (option of roleOptions; track option.value) {
                  <option [value]="option.value">{{ option.label }}</option>
                }
              </select>
            </label>

            <label class="block">
              <span class="mb-2 block text-xs uppercase tracking-wide text-text-muted">External send</span>
              <select
                formControlName="external_send_role"
                class="w-full rounded border border-border-default bg-surface-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              >
                @for (option of roleOptions; track option.value) {
                  <option [value]="option.value">{{ option.label }}</option>
                }
              </select>
            </label>

            <label class="block">
              <span class="mb-2 block text-xs uppercase tracking-wide text-text-muted">High-risk AI</span>
              <select
                formControlName="high_risk_role"
                class="w-full rounded border border-border-default bg-surface-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              >
                @for (option of adminOwnerOptions; track option.value) {
                  <option [value]="option.value">{{ option.label }}</option>
                }
              </select>
            </label>
          </div>

          @if (!canEdit()) {
            <div class="rounded border border-border-default bg-surface-base px-3 py-2 text-sm text-text-muted" role="status">
              Approval policy changes require Admin or Owner.
            </div>
          }

          @if (loadError()) {
            <div class="rounded border border-confidence-low/30 bg-confidence-low/10 px-3 py-2 text-sm text-confidence-low" role="alert">
              Failed to load approval policy.
            </div>
          }

          @if (saveError()) {
            <div class="rounded border border-confidence-low/30 bg-confidence-low/10 px-3 py-2 text-sm text-confidence-low" role="alert">
              Failed to save approval policy.
            </div>
          }

          @if (saved()) {
            <div class="rounded border border-accent/30 bg-accent/10 px-3 py-2 text-sm text-accent-light" role="status">
              Approval policy saved.
            </div>
          }

          <div class="flex justify-end">
            <button
              type="submit"
              [disabled]="!canEdit() || form.invalid || saving()"
              class="inline-flex items-center gap-2 rounded bg-accent px-4 py-2 text-sm font-medium text-accent-on transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              @if (saving()) {
                <span>Saving...</span>
              } @else {
                <mat-icon style="font-size:1rem;width:1rem;height:1rem;" aria-hidden="true">save</mat-icon>
                <span>Save Policy</span>
              }
            </button>
          </div>
        </form>
      }
    </div>
  `,
  styles: [':host { display: block; }'],
})
export class ApprovalPolicyComponent implements OnInit {
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);

  readonly roleOptions = ROLE_OPTIONS;
  readonly adminOwnerOptions = ADMIN_OWNER_OPTIONS;

  loading = signal(true);
  saving = signal(false);
  loadError = signal(false);
  saveError = signal(false);
  saved = signal(false);
  policy = signal<ApprovalPolicy | null>(null);

  canEdit = computed(() => {
    const role = this.auth.role();
    return role === 'admin' || role === 'owner';
  });

  form = this.fb.nonNullable.group({
    money_out_default_role: ['admin' as ApprovalRole, [Validators.required]],
    money_out_owner_threshold: [50000, [Validators.required, Validators.min(0)]],
    money_out_owner_role: ['owner' as ApprovalRole, [Validators.required]],
    accounting_role: ['admin' as ApprovalRole, [Validators.required]],
    manual_journal_approval_threshold: [10000, [Validators.required, Validators.min(0)]],
    money_in_role: ['manager' as ApprovalRole, [Validators.required]],
    draft_role: ['manager' as ApprovalRole, [Validators.required]],
    external_send_role: ['manager' as ApprovalRole, [Validators.required]],
    high_risk_role: ['admin' as ApprovalRole, [Validators.required]],
  });

  ngOnInit(): void {
    this.applyEditState();
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.loadError.set(false);
    this.saved.set(false);
    this.http.get<ApprovalPolicy>('/api/v1/approval-policy/effective').subscribe({
      next: (policy) => {
        this.applyPolicy(policy);
        this.loading.set(false);
      },
      error: () => {
        this.loadError.set(true);
        this.loading.set(false);
      },
    });
  }

  save(): void {
    if (!this.canEdit() || this.form.invalid) return;
    this.saving.set(true);
    this.saveError.set(false);
    this.saved.set(false);
    const value = this.form.getRawValue();
    this.http.put<ApprovalPolicy>('/api/v1/approval-policy/default', {
      money_out_default_role: value.money_out_default_role,
      money_out_owner_threshold: String(Number(value.money_out_owner_threshold)),
      money_out_owner_role: value.money_out_owner_role,
      accounting_role: value.accounting_role,
      manual_journal_approval_threshold: String(
        Number(value.manual_journal_approval_threshold),
      ),
      money_in_role: value.money_in_role,
      draft_role: value.draft_role,
      external_send_role: value.external_send_role,
      high_risk_role: value.high_risk_role,
    }).subscribe({
      next: (policy) => {
        this.applyPolicy(policy);
        this.saving.set(false);
        this.saved.set(true);
      },
      error: () => {
        this.saving.set(false);
        this.saveError.set(true);
      },
    });
  }

  policySourceLabel(source: ApprovalPolicySource): string {
    return source === 'tenant_default' ? 'Tenant policy' : 'System default';
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

  private applyPolicy(policy: ApprovalPolicy): void {
    this.policy.set(policy);
    this.form.patchValue({
      money_out_default_role: policy.money_out_default_role,
      money_out_owner_threshold: Number(policy.money_out_owner_threshold),
      money_out_owner_role: policy.money_out_owner_role,
      accounting_role: policy.accounting_role,
      manual_journal_approval_threshold: Number(policy.manual_journal_approval_threshold),
      money_in_role: policy.money_in_role,
      draft_role: policy.draft_role,
      external_send_role: policy.external_send_role,
      high_risk_role: policy.high_risk_role,
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
