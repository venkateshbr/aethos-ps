import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';

import { AuthService } from '../../core/services/auth.service';

interface SecurityPrivilege {
  code: string;
  label: string;
  category: string;
  description: string;
}

interface SecurityDuty {
  code: string;
  label: string;
  description: string;
  privileges: SecurityPrivilege[];
}

interface SecurityRole {
  id: string;
  code: string;
  label: string;
  description: string;
  legacy_role: string;
  is_system: boolean;
  is_assignable: boolean;
  rank: number;
  duties: SecurityDuty[];
  privilege_codes: string[];
}

@Component({
  selector: 'app-security-roles',
  standalone: true,
  imports: [ReactiveFormsModule, MatIconModule],
  template: `
    <div class="overflow-hidden rounded-lg border border-border-default bg-surface-raised">
      <div class="flex flex-col gap-3 border-b border-border-default px-6 py-4 lg:flex-row lg:items-center lg:justify-between">
        <div class="flex min-w-0 items-center gap-2">
          <mat-icon class="flex-none text-accent-light">admin_panel_settings</mat-icon>
          <div class="min-w-0">
            <h3 class="truncate text-base font-semibold text-text-primary">Security Roles</h3>
            <p class="mt-1 text-xs text-text-muted">Roles, duties, and privileges for enterprise access control.</p>
          </div>
        </div>
        <button
          type="button"
          (click)="load()"
          class="inline-flex h-9 items-center gap-1.5 self-start rounded border border-border-default px-3 text-sm font-medium text-text-secondary transition-colors hover:border-accent/60 hover:text-text-primary lg:self-auto"
        >
          <mat-icon style="font-size:1rem;width:1rem;height:1rem;" aria-hidden="true">refresh</mat-icon>
          Refresh
        </button>
      </div>

      <div class="grid gap-5 px-6 py-5 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div class="min-w-0">
          @if (loading()) {
            <div class="space-y-3" aria-busy="true" aria-label="Loading security roles">
              @for (row of [1, 2, 3]; track row) {
                <div class="h-20 rounded bg-surface"></div>
              }
            </div>
          } @else if (error()) {
            <div class="rounded border border-confidence-low/30 bg-confidence-low/10 px-3 py-2 text-sm text-confidence-low" role="alert">
              {{ error() }}
            </div>
          } @else {
            <div class="divide-y divide-border-default rounded border border-border-subtle">
              @for (role of roles(); track role.id) {
                <article class="px-4 py-3">
                  <div class="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                    <div class="min-w-0">
                      <div class="flex flex-wrap items-center gap-2">
                        <h4 class="text-sm font-medium text-text-primary">{{ role.label }}</h4>
                        <span class="rounded bg-surface px-2 py-0.5 text-[11px] uppercase text-text-muted">{{ role.legacy_role }}</span>
                        @if (role.is_system) {
                          <span class="rounded bg-accent/10 px-2 py-0.5 text-[11px] text-accent-light">System</span>
                        }
                      </div>
                      <p class="mt-1 text-xs text-text-muted">{{ role.description }}</p>
                      <div class="mt-2 flex flex-wrap gap-1.5">
                        @for (duty of role.duties; track duty.code) {
                          <span class="rounded border border-border-default px-2 py-0.5 text-[11px] text-text-secondary">{{ duty.label }}</span>
                        }
                      </div>
                    </div>
                    <div class="text-xs text-text-muted md:text-right">{{ role.privilege_codes.length }} privileges</div>
                  </div>
                </article>
              } @empty {
                <div class="px-4 py-6 text-center text-sm text-text-muted">No security roles found.</div>
              }
            </div>
          }
        </div>

        <form [formGroup]="form" (ngSubmit)="createRole()" class="rounded border border-border-subtle bg-surface-base px-4 py-4" novalidate>
          <div class="mb-4 flex items-center gap-2">
            <mat-icon class="text-accent-light" style="font-size:1rem;width:1rem;height:1rem;">add_moderator</mat-icon>
            <h4 class="text-sm font-semibold text-text-primary">Create role</h4>
          </div>

          <label class="mb-3 block">
            <span class="mb-2 block text-xs uppercase tracking-wide text-text-muted">Role name</span>
            <input
              type="text"
              formControlName="label"
              class="w-full rounded border border-border-default bg-surface-raised px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </label>

          <label class="mb-3 block">
            <span class="mb-2 block text-xs uppercase tracking-wide text-text-muted">Legacy projection</span>
            <select
              formControlName="legacy_role"
              class="w-full rounded border border-border-default bg-surface-raised px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            >
              <option value="admin">Admin-level</option>
              <option value="manager">Manager-level</option>
              <option value="approver">Approver-only</option>
              <option value="member">Operator-level</option>
              <option value="auditor">Auditor read-only</option>
              <option value="viewer">Executive read-only</option>
            </select>
          </label>

          <label class="mb-4 block">
            <span class="mb-2 block text-xs uppercase tracking-wide text-text-muted">Description</span>
            <textarea
              formControlName="description"
              rows="3"
              class="w-full rounded border border-border-default bg-surface-raised px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            ></textarea>
          </label>

          <div class="mb-4">
            <span class="mb-2 block text-xs uppercase tracking-wide text-text-muted">Duties</span>
            <div class="max-h-60 space-y-2 overflow-auto rounded border border-border-default bg-surface-raised p-2">
              @for (duty of availableDuties(); track duty.code) {
                <label class="flex gap-2 rounded px-2 py-1.5 text-sm text-text-secondary hover:bg-surface-base">
                  <input type="checkbox" [checked]="selectedDuties().has(duty.code)" (change)="toggleDuty(duty.code)" />
                  <span>
                    <span class="block text-text-primary">{{ duty.label }}</span>
                    <span class="block text-xs text-text-muted">{{ duty.privileges.length }} privileges</span>
                  </span>
                </label>
              }
            </div>
          </div>

          @if (!canEdit()) {
            <div class="mb-3 rounded border border-border-default bg-surface-raised px-3 py-2 text-sm text-text-muted" role="status">
              Security role changes require Tenant Admin or Owner.
            </div>
          }

          @if (saveError()) {
            <div class="mb-3 rounded border border-confidence-low/30 bg-confidence-low/10 px-3 py-2 text-sm text-confidence-low" role="alert">
              {{ saveError() }}
            </div>
          }

          @if (saved()) {
            <div class="mb-3 rounded border border-accent/30 bg-accent/10 px-3 py-2 text-sm text-accent-light" role="status">
              Role created.
            </div>
          }

          <button
            type="submit"
            [disabled]="!canEdit() || form.invalid || !selectedDuties().size || saving()"
            class="inline-flex w-full items-center justify-center gap-2 rounded bg-accent px-4 py-2 text-sm font-medium text-accent-on transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-60"
          >
            @if (saving()) { <span>Creating...</span> } @else {
              <mat-icon style="font-size:1rem;width:1rem;height:1rem;" aria-hidden="true">add_moderator</mat-icon>
              <span>Create Role</span>
            }
          </button>
        </form>
      </div>
    </div>
  `,
})
export class SecurityRolesComponent implements OnInit {
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);

  roles = signal<SecurityRole[]>([]);
  loading = signal(true);
  error = signal<string | null>(null);
  saveError = signal<string | null>(null);
  saved = signal(false);
  saving = signal(false);
  selectedDuties = signal<Set<string>>(new Set());
  canEdit = computed(() => ['owner', 'admin'].includes(this.auth.role() ?? ''));

  form = this.fb.nonNullable.group({
    label: ['', [Validators.required, Validators.minLength(2)]],
    description: [''],
    legacy_role: ['member', [Validators.required]],
  });

  availableDuties = computed(() => {
    const byCode = new Map<string, SecurityDuty>();
    for (const role of this.roles()) {
      for (const duty of role.duties ?? []) byCode.set(duty.code, duty);
    }
    return [...byCode.values()].sort((a, b) => a.label.localeCompare(b.label));
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.http.get<{ items: SecurityRole[] }>('/api/v1/security/roles').subscribe({
      next: (res) => {
        this.roles.set(res.items ?? []);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Could not load security roles.');
        this.loading.set(false);
      },
    });
  }

  toggleDuty(code: string): void {
    this.selectedDuties.update(current => {
      const next = new Set(current);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  }

  createRole(): void {
    this.saveError.set(null);
    this.saved.set(false);
    if (!this.canEdit() || this.form.invalid || !this.selectedDuties().size) return;
    const raw = this.form.getRawValue();
    this.saving.set(true);
    this.http.post<SecurityRole>('/api/v1/security/roles', {
      label: raw.label,
      description: raw.description || null,
      legacy_role: raw.legacy_role,
      duty_codes: [...this.selectedDuties()],
    }).subscribe({
      next: (role) => {
        this.roles.update(items => [...items, role].sort((a, b) => b.rank - a.rank));
        this.selectedDuties.set(new Set());
        this.form.reset({ label: '', description: '', legacy_role: 'member' });
        this.saved.set(true);
        this.saving.set(false);
      },
      error: (err) => {
        this.saveError.set(err?.error?.detail || 'Could not create role.');
        this.saving.set(false);
      },
    });
  }
}
