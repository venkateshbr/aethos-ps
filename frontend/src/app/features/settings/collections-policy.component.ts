import { Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';

interface CollectionsPolicy {
  id: string | null;
  client_id: string | null;
  policy_source: 'system_default' | 'tenant_default' | 'client_override';
  is_enabled: boolean;
  gentle_after_days: number;
  firm_after_days: number;
  final_after_days: number;
  cooldown_days: number;
  max_reminders_per_invoice: number;
  max_auto_send_tone: 'none' | 'gentle' | 'firm' | 'final';
}

const AUTO_SEND_TONE_OPTIONS = [
  { value: 'none', label: 'None' },
  { value: 'gentle', label: 'Gentle' },
  { value: 'firm', label: 'Firm' },
  { value: 'final', label: 'Final' },
] as const;

@Component({
  selector: 'app-collections-policy',
  standalone: true,
  imports: [ReactiveFormsModule, MatIconModule],
  template: `
    <div class="bg-surface-raised border border-border-default rounded-lg overflow-hidden">
      <div class="flex items-center justify-between gap-4 px-6 py-4 border-b border-border-default">
        <div class="flex items-center gap-2 min-w-0">
          <mat-icon class="text-emerald-400">mark_email_read</mat-icon>
          <h3 class="text-base font-semibold text-text-primary truncate">Collections Policy</h3>
        </div>
        @if (policySource()) {
          <span class="text-xs text-text-muted whitespace-nowrap">
            {{ policySourceLabel(policySource()!) }}
          </span>
        }
      </div>

      @if (loading()) {
        <div class="px-6 py-5 animate-pulse" aria-busy="true" aria-label="Loading collections policy">
          <div class="h-4 w-48 bg-surface rounded mb-4"></div>
          <div class="grid gap-3 sm:grid-cols-3">
            @for (i of [1, 2, 3]; track i) {
              <div class="h-16 bg-surface rounded"></div>
            }
          </div>
        </div>
      } @else {
        <form [formGroup]="form" (ngSubmit)="save()" class="px-6 py-5 space-y-5" novalidate>
          <div class="flex items-center justify-between gap-4">
            <label for="collections-enabled" class="text-sm font-medium text-text-primary">
              Enable reminders
            </label>
            <input
              id="collections-enabled"
              type="checkbox"
              formControlName="is_enabled"
              class="h-4 w-4 rounded border-border-default bg-surface-base text-accent focus:ring-accent"
            />
          </div>

          <div class="grid gap-3 sm:grid-cols-3">
            <label class="block">
              <span class="block text-xs uppercase tracking-wide text-text-muted mb-2">Gentle after</span>
              <input
                type="number"
                min="1"
                max="365"
                formControlName="gentle_after_days"
                class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
              />
            </label>

            <label class="block">
              <span class="block text-xs uppercase tracking-wide text-text-muted mb-2">Firm after</span>
              <input
                type="number"
                min="1"
                max="365"
                formControlName="firm_after_days"
                class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
              />
            </label>

            <label class="block">
              <span class="block text-xs uppercase tracking-wide text-text-muted mb-2">Final after</span>
              <input
                type="number"
                min="1"
                max="365"
                formControlName="final_after_days"
                class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
              />
            </label>
          </div>

          <div class="grid gap-3 sm:grid-cols-3">
            <label class="block">
              <span class="block text-xs uppercase tracking-wide text-text-muted mb-2">Cooldown days</span>
              <input
                type="number"
                min="1"
                max="365"
                formControlName="cooldown_days"
                class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
              />
            </label>

            <label class="block">
              <span class="block text-xs uppercase tracking-wide text-text-muted mb-2">Max reminders</span>
              <input
                type="number"
                min="1"
                max="20"
                formControlName="max_reminders_per_invoice"
                class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
              />
            </label>

            <label class="block">
              <span class="block text-xs uppercase tracking-wide text-text-muted mb-2">Auto-send up to</span>
              <select
                formControlName="max_auto_send_tone"
                class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
              >
                @for (option of autoSendToneOptions; track option.value) {
                  <option [value]="option.value">{{ option.label }}</option>
                }
              </select>
            </label>
          </div>

          @if (stageOrderInvalid()) {
            <div class="text-sm text-confidence-low bg-confidence-low/10 border border-confidence-low/30 rounded px-3 py-2" role="alert">
              Reminder stages must stay in ascending day order.
            </div>
          }

          @if (loadError()) {
            <div class="text-sm text-confidence-low bg-confidence-low/10 border border-confidence-low/30 rounded px-3 py-2" role="alert">
              Failed to load collections policy.
            </div>
          }

          @if (saveError()) {
            <div class="text-sm text-confidence-low bg-confidence-low/10 border border-confidence-low/30 rounded px-3 py-2" role="alert">
              Failed to save collections policy.
            </div>
          }

          @if (saved()) {
            <div class="text-sm text-accent-light bg-accent/10 border border-accent/30 rounded px-3 py-2" role="status">
              Collections policy saved.
            </div>
          }

          <div class="flex justify-end">
            <button
              type="submit"
              [disabled]="form.invalid || stageOrderInvalid() || saving()"
              class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              @if (saving()) {
                <span>Saving...</span>
              } @else {
                <mat-icon style="font-size:1rem;width:1rem;height:1rem;">save</mat-icon>
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
export class CollectionsPolicyComponent implements OnInit {
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);

  loading = signal(true);
  saving = signal(false);
  loadError = signal(false);
  saveError = signal(false);
  saved = signal(false);
  policySource = signal<CollectionsPolicy['policy_source'] | null>(null);

  readonly autoSendToneOptions = AUTO_SEND_TONE_OPTIONS;

  form = this.fb.nonNullable.group({
    is_enabled: [true],
    gentle_after_days: [1, [Validators.required, Validators.min(1), Validators.max(365)]],
    firm_after_days: [8, [Validators.required, Validators.min(1), Validators.max(365)]],
    final_after_days: [31, [Validators.required, Validators.min(1), Validators.max(365)]],
    cooldown_days: [7, [Validators.required, Validators.min(1), Validators.max(365)]],
    max_reminders_per_invoice: [3, [Validators.required, Validators.min(1), Validators.max(20)]],
    max_auto_send_tone: ['final' as CollectionsPolicy['max_auto_send_tone'], [Validators.required]],
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.loadError.set(false);
    this.http.get<CollectionsPolicy>('/api/v1/collections/policies/effective').subscribe({
      next: (policy) => {
        this.policySource.set(policy.policy_source);
        this.form.patchValue({
          is_enabled: policy.is_enabled,
          gentle_after_days: policy.gentle_after_days,
          firm_after_days: policy.firm_after_days,
          final_after_days: policy.final_after_days,
          cooldown_days: policy.cooldown_days,
          max_reminders_per_invoice: policy.max_reminders_per_invoice,
          max_auto_send_tone: policy.max_auto_send_tone,
        });
        this.loading.set(false);
      },
      error: () => {
        this.loadError.set(true);
        this.loading.set(false);
      },
    });
  }

  save(): void {
    if (this.form.invalid || this.stageOrderInvalid()) return;
    this.saving.set(true);
    this.saveError.set(false);
    this.saved.set(false);
    const value = this.form.getRawValue();
    this.http.put<CollectionsPolicy>('/api/v1/collections/policies/default', {
      is_enabled: value.is_enabled,
      gentle_after_days: Number(value.gentle_after_days),
      firm_after_days: Number(value.firm_after_days),
      final_after_days: Number(value.final_after_days),
      cooldown_days: Number(value.cooldown_days),
      max_reminders_per_invoice: Number(value.max_reminders_per_invoice),
      max_auto_send_tone: value.max_auto_send_tone,
    }).subscribe({
      next: (policy) => {
        this.policySource.set(policy.policy_source);
        this.saving.set(false);
        this.saved.set(true);
      },
      error: () => {
        this.saving.set(false);
        this.saveError.set(true);
      },
    });
  }

  stageOrderInvalid(): boolean {
    const value = this.form.getRawValue();
    return Number(value.firm_after_days) < Number(value.gentle_after_days)
      || Number(value.final_after_days) < Number(value.firm_after_days);
  }

  policySourceLabel(source: CollectionsPolicy['policy_source']): string {
    if (source === 'tenant_default') return 'Tenant default';
    if (source === 'client_override') return 'Client override';
    return 'System default';
  }
}
