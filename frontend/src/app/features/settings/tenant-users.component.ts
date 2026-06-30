import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';

import { AuthService } from '../../core/services/auth.service';

type TenantUserRole = string;

interface SecurityRoleOption {
  code: string;
  label: string;
  legacy_role: string;
  is_system: boolean;
  is_assignable: boolean;
  description: string;
}

interface TenantUser {
  id: string;
  tenant_id: string;
  user_id: string;
  email: string | null;
  display_name: string | null;
  role: string;
  role_codes: string[];
  role_labels: string[];
  status: string;
  must_change_password: boolean;
  invited_at: string | null;
  joined_at: string | null;
  created_at: string;
  updated_at: string;
  deactivated_at: string | null;
}

interface TenantUserInviteResponse extends TenantUser {
  set_password_url: string | null;
  temp_password: string | null;
}

const FALLBACK_ROLE_OPTIONS: SecurityRoleOption[] = [
  { code: 'tenant_owner', label: 'Tenant Owner', legacy_role: 'owner', is_system: true, is_assignable: true, description: '' },
  { code: 'tenant_admin', label: 'Tenant Admin', legacy_role: 'admin', is_system: true, is_assignable: true, description: '' },
  { code: 'finance_controller', label: 'Finance Controller', legacy_role: 'admin', is_system: true, is_assignable: true, description: '' },
  { code: 'finance_ops_manager', label: 'Finance Ops Manager', legacy_role: 'manager', is_system: true, is_assignable: true, description: '' },
  { code: 'finance_approver', label: 'Finance Approver', legacy_role: 'approver', is_system: true, is_assignable: true, description: '' },
  { code: 'finance_operator', label: 'Finance Operator', legacy_role: 'member', is_system: true, is_assignable: true, description: '' },
  { code: 'auditor', label: 'Auditor', legacy_role: 'auditor', is_system: true, is_assignable: true, description: '' },
  { code: 'executive_viewer', label: 'Executive Viewer', legacy_role: 'viewer', is_system: true, is_assignable: true, description: '' },
];

@Component({
  selector: 'app-tenant-users',
  standalone: true,
  imports: [ReactiveFormsModule, MatIconModule],
  template: `
    <div class="overflow-hidden rounded-lg border border-border-default bg-surface-raised">
      <div class="flex flex-col gap-3 border-b border-border-default px-6 py-4 lg:flex-row lg:items-center lg:justify-between">
        <div class="flex min-w-0 items-center gap-2">
          <mat-icon class="flex-none text-accent-light">group</mat-icon>
          <div class="min-w-0">
            <h3 class="truncate text-base font-semibold text-text-primary">Tenant Users</h3>
            <p class="mt-1 text-xs text-text-muted">ERP access, role assignment, and audit-controlled deactivation.</p>
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

      <div class="grid gap-5 px-6 py-5 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div class="min-w-0">
          @if (loading()) {
            <div class="space-y-3" aria-busy="true" aria-label="Loading tenant users">
              @for (row of [1, 2, 3]; track row) {
                <div class="h-14 rounded bg-surface"></div>
              }
            </div>
          } @else if (loadError()) {
            <div class="rounded border border-confidence-low/30 bg-confidence-low/10 px-3 py-2 text-sm text-confidence-low" role="alert">
              Failed to load tenant users.
            </div>
          } @else {
            <div class="overflow-x-auto rounded border border-border-subtle">
              <table class="w-full text-sm" aria-label="Tenant users">
                <thead>
                  <tr class="border-b border-border-default bg-surface-base text-xs uppercase text-text-muted">
                    <th scope="col" class="px-3 py-2 text-left">User</th>
                    <th scope="col" class="px-3 py-2 text-left">Roles</th>
                    <th scope="col" class="px-3 py-2 text-left">Status</th>
                    <th scope="col" class="px-3 py-2 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-border-default">
                  @for (user of users(); track user.id) {
                    <tr>
                      <td class="px-3 py-2">
                        <div class="font-medium text-text-primary">{{ user.display_name || user.email || user.user_id }}</div>
                        <div class="mt-0.5 font-mono text-xs text-text-muted">{{ user.email || user.user_id }}</div>
                      </td>
                      <td class="px-3 py-2">
                        <select
                          [value]="primaryRoleCode(user)"
                          [disabled]="!canEdit() || savingUserId() === user.id"
                          (change)="changeRole(user, $event)"
                          class="w-48 rounded border border-border-default bg-surface-base px-2 py-1.5 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          @for (option of roleOptions(); track option.value) {
                            <option [value]="option.value">{{ option.label }}</option>
                          }
                        </select>
                        <div class="mt-1 text-xs text-text-muted">
                          {{ user.role_labels.join(', ') || roleLabel(user.role) }}
                        </div>
                        @if (user.must_change_password) {
                          <div class="mt-1 text-[11px] text-accent-light">Initial password change required</div>
                        }
                      </td>
                      <td class="px-3 py-2">
                        <span class="rounded-full px-2 py-0.5 text-xs font-semibold" [class]="statusClass(user.status)">
                          {{ user.status }}
                        </span>
                      </td>
                      <td class="px-3 py-2 text-right">
                        <button
                          type="button"
                          (click)="deactivate(user)"
                          [disabled]="!canEdit() || savingUserId() === user.id"
                          class="inline-flex h-8 w-8 items-center justify-center rounded border border-border-default text-text-muted transition-colors hover:border-confidence-low/60 hover:text-confidence-low disabled:cursor-not-allowed disabled:opacity-50"
                          [attr.aria-label]="'Deactivate ' + (user.email || user.user_id)"
                          title="Deactivate user"
                        >
                          <mat-icon style="font-size:1rem;width:1rem;height:1rem;" aria-hidden="true">person_remove</mat-icon>
                        </button>
                      </td>
                    </tr>
                  } @empty {
                    <tr>
                      <td colspan="4" class="px-3 py-6 text-center text-sm text-text-muted">No tenant users found.</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          }
        </div>

        <form [formGroup]="inviteForm" (ngSubmit)="invite()" class="rounded border border-border-subtle bg-surface-base px-4 py-4" novalidate>
          <div class="mb-4 flex items-center gap-2">
            <mat-icon class="text-accent-light" style="font-size:1rem;width:1rem;height:1rem;">person_add</mat-icon>
            <h4 class="text-sm font-semibold text-text-primary">Invite user</h4>
          </div>

          <label class="mb-3 block">
            <span class="mb-2 block text-xs uppercase tracking-wide text-text-muted">Email</span>
            <input
              type="email"
              formControlName="email"
              autocomplete="email"
              class="w-full rounded border border-border-default bg-surface-raised px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </label>

          <label class="mb-3 block">
            <span class="mb-2 block text-xs uppercase tracking-wide text-text-muted">Display name</span>
            <input
              type="text"
              formControlName="display_name"
              autocomplete="name"
              class="w-full rounded border border-border-default bg-surface-raised px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </label>

          <label class="mb-3 block">
            <span class="mb-2 block text-xs uppercase tracking-wide text-text-muted">Role</span>
            <select
              formControlName="role_code"
              class="w-full rounded border border-border-default bg-surface-raised px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            >
              @for (option of inviteRoleOptions(); track option.value) {
                <option [value]="option.value">{{ option.label }}</option>
              }
            </select>
          </label>

          <label class="mb-4 block">
            <span class="mb-2 block text-xs uppercase tracking-wide text-text-muted">Temporary password</span>
            <input
              type="password"
              formControlName="password"
              autocomplete="new-password"
              placeholder="Auto-generate"
              class="w-full rounded border border-border-default bg-surface-raised px-3 py-2 text-sm text-text-primary placeholder:text-text-disabled focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </label>

          @if (!canEdit()) {
            <div class="mb-3 rounded border border-border-default bg-surface-raised px-3 py-2 text-sm text-text-muted" role="status">
              Tenant user changes require Admin or Owner.
            </div>
          }

          @if (error()) {
            <div class="mb-3 rounded border border-confidence-low/30 bg-confidence-low/10 px-3 py-2 text-sm text-confidence-low" role="alert">
              {{ error() }}
            </div>
          }

          @if (lastInvite(); as inviteResult) {
            <div class="mb-3 space-y-1 rounded border border-accent/30 bg-accent/10 px-3 py-2 text-xs text-accent-light" role="status">
              <div>User invited: {{ inviteResult.email }}</div>
              @if (inviteResult.temp_password) {
                <div class="font-mono">Temp password: {{ inviteResult.temp_password }}</div>
              }
              @if (inviteResult.set_password_url) {
                <a [href]="inviteResult.set_password_url" target="_blank" rel="noreferrer" class="underline">Set password link</a>
              }
            </div>
          }

          <button
            type="submit"
            [disabled]="!canEdit() || inviteForm.invalid || inviting()"
            class="inline-flex w-full items-center justify-center gap-2 rounded bg-accent px-4 py-2 text-sm font-medium text-accent-on transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            @if (inviting()) {
              <span>Inviting...</span>
            } @else {
              <mat-icon style="font-size:1rem;width:1rem;height:1rem;" aria-hidden="true">person_add</mat-icon>
              <span>Create User</span>
            }
          </button>
        </form>
      </div>
    </div>
  `,
  styles: [':host { display: block; }'],
})
export class TenantUsersComponent implements OnInit {
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);

  users = signal<TenantUser[]>([]);
  loading = signal(true);
  inviting = signal(false);
  savingUserId = signal<string | null>(null);
  loadError = signal(false);
  error = signal<string | null>(null);
  lastInvite = signal<TenantUserInviteResponse | null>(null);
  roles = signal<SecurityRoleOption[]>(FALLBACK_ROLE_OPTIONS);
  roleOptions = computed(() =>
    this.roles()
      .filter(role => role.is_assignable)
      .map(role => ({ value: role.code, label: role.label, legacyRole: role.legacy_role })),
  );
  canEdit = computed(() => ['owner', 'admin'].includes(this.auth.role() ?? ''));
  inviteRoleOptions = computed(() => {
    const options = this.roleOptions();
    if (this.auth.role() === 'owner') return options;
    return options.filter(option => option.legacyRole !== 'owner');
  });

  inviteForm = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    display_name: [''],
    role_code: ['finance_operator' as TenantUserRole, [Validators.required]],
    password: ['', [Validators.minLength(8)]],
  });

  ngOnInit(): void {
    this.loadRoles();
    this.load();
  }

  loadRoles(): void {
    this.http.get<{ items: SecurityRoleOption[] }>('/api/v1/security/roles').subscribe({
      next: (res) => {
        const roles = (res.items ?? []).filter(role => role.is_assignable);
        if (roles.length) this.roles.set(roles);
      },
      error: () => {
        this.roles.set(FALLBACK_ROLE_OPTIONS);
      },
    });
  }

  load(): void {
    this.loading.set(true);
    this.loadError.set(false);
    this.http.get<{ items: TenantUser[] }>('/api/v1/tenant-users').subscribe({
      next: (res) => {
        this.users.set(res.items ?? []);
        this.loading.set(false);
      },
      error: () => {
        this.loadError.set(true);
        this.loading.set(false);
      },
    });
  }

  invite(): void {
    this.error.set(null);
    this.lastInvite.set(null);
    if (this.inviteForm.invalid) {
      this.inviteForm.markAllAsTouched();
      return;
    }
    const raw = this.inviteForm.getRawValue();
    const payload = {
      email: raw.email,
      role_codes: [raw.role_code],
      display_name: raw.display_name || null,
      password: raw.password || null,
    };
    this.inviting.set(true);
    this.http.post<TenantUserInviteResponse>('/api/v1/tenant-users', payload).subscribe({
      next: (res) => {
        this.lastInvite.set(res);
        this.inviteForm.reset({ email: '', display_name: '', role_code: 'finance_operator', password: '' });
        this.load();
        this.inviting.set(false);
      },
      error: (err) => {
        this.error.set(err?.error?.detail || 'Could not invite user.');
        this.inviting.set(false);
      },
    });
  }

  changeRole(user: TenantUser, event: Event): void {
    const role = (event.target as HTMLSelectElement).value as TenantUserRole;
    if (role === this.primaryRoleCode(user)) return;
    this.error.set(null);
    this.savingUserId.set(user.id);
    this.http.patch<TenantUser>(`/api/v1/tenant-users/${user.id}`, { role_codes: [role] }).subscribe({
      next: (updated) => {
        this.users.update(items => items.map(item => item.id === updated.id ? updated : item));
        this.savingUserId.set(null);
      },
      error: (err) => {
        this.error.set(err?.error?.detail || 'Could not update role.');
        this.load();
        this.savingUserId.set(null);
      },
    });
  }

  deactivate(user: TenantUser): void {
    this.error.set(null);
    this.savingUserId.set(user.id);
    this.http.delete(`/api/v1/tenant-users/${user.id}`).subscribe({
      next: () => {
        this.users.update(items => items.filter(item => item.id !== user.id));
        this.savingUserId.set(null);
      },
      error: (err) => {
        this.error.set(err?.error?.detail || 'Could not deactivate user.');
        this.savingUserId.set(null);
      },
    });
  }

  statusClass(status: string): string {
    return status === 'active'
      ? 'bg-accent/10 text-accent-light'
      : 'bg-surface text-text-muted';
  }

  primaryRoleCode(user: TenantUser): string {
    return user.role_codes?.[0] ?? legacyRoleToCatalogRole(user.role);
  }

  roleLabel(role: string): string {
    return this.roles().find(option => option.legacy_role === role || option.code === role)?.label ?? role;
  }
}

function legacyRoleToCatalogRole(role: string): string {
  switch (role) {
    case 'owner': return 'tenant_owner';
    case 'admin': return 'tenant_admin';
    case 'manager': return 'finance_ops_manager';
    case 'approver': return 'finance_approver';
    case 'auditor': return 'auditor';
    case 'viewer': return 'executive_viewer';
    default: return 'finance_operator';
  }
}
