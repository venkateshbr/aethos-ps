/**
 * PeopleListComponent — employee master CRUD (issue #134, Phase 1).
 *
 * Previously a placeholder. Now lists employees and provides a slide-in panel
 * to create / edit, plus soft-delete. Backed by /api/v1/employees, which
 * returns { items, total }. Mirrors the clients-list create-panel pattern.
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';

interface Employee {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  title?: string | null;
  department?: string | null;
  employment_type: string;
  default_bill_rate?: string | null;
  default_bill_rate_currency?: string | null;
  cost_rate?: string | null;
  manager_id?: string | null;
  skills: string[];
  has_login: boolean;
  status: string;
  created_at: string;
}

interface EmployeeListResponse {
  items: Employee[];
  total: number;
}

interface InviteResult {
  email: string;
  set_password_url?: string | null;
  temp_password?: string | null;
}

const EMPLOYMENT_LABELS: Record<string, string> = {
  full_time: 'Full-time',
  part_time: 'Part-time',
  contractor: 'Contractor',
  consultant: 'Consultant',
};

@Component({
  selector: 'app-people-list',
  standalone: true,
  imports: [ReactiveFormsModule, MatIconModule],
  template: `
    <section class="h-full flex flex-col bg-surface-base text-text-primary">
      <header class="px-6 py-4 border-b border-border-default flex items-center justify-between flex-none">
        <div>
          <h1 class="text-2xl font-bold text-text-primary">People</h1>
          <p class="text-sm text-text-muted mt-0.5">Your team and contractors — the people who log billable time.</p>
        </div>
        <button type="button"
          class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          aria-label="Add new employee" (click)="openCreate()">
          <mat-icon class="text-base leading-none">add</mat-icon>
          New employee
        </button>
      </header>

      @if (loading()) {
        <div class="flex items-center justify-center py-16">
          <div class="w-6 h-6 rounded-full border-2 border-accent border-t-transparent animate-spin" aria-label="Loading employees"></div>
        </div>
      }

      @if (error() && !loading()) {
        <div class="mx-6 mt-4 rounded-lg border border-confidence-low/30 bg-confidence-low/10 px-4 py-3 text-sm text-confidence-low" role="alert">
          <mat-icon class="text-base align-middle mr-1">error_outline</mat-icon>
          {{ error() }}
        </div>
      }

      @if (!loading() && !error() && employees().length === 0) {
        <div class="flex-1 flex flex-col items-center justify-center text-center px-6">
          <mat-icon class="text-text-disabled mb-3" style="font-size:2.5rem;width:2.5rem;height:2.5rem;" aria-hidden="true">badge</mat-icon>
          <p class="text-text-secondary font-medium">No people yet</p>
          <p class="text-text-disabled text-sm mt-1 max-w-md">Add your team members and contractors so they can be assigned to projects and log time.</p>
          <button type="button"
            class="mt-5 inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            (click)="openCreate()">
            <mat-icon class="text-base leading-none">add</mat-icon>
            Add first employee
          </button>
        </div>
      }

      @if (!loading() && !error() && employees().length > 0) {
        <div class="flex-1 overflow-y-auto p-6">
          <div class="space-y-2">
            @for (e of employees(); track e.id) {
              <div class="flex items-center gap-4 bg-surface border border-border-default rounded-lg px-4 py-3 hover:border-border-strong transition-colors">
                <div class="w-9 h-9 rounded-full bg-accent/15 flex items-center justify-center flex-none">
                  <span class="text-accent-light text-xs font-semibold">{{ initials(e) }}</span>
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-text-primary truncate">
                    {{ e.first_name }} {{ e.last_name }}
                    @if (e.has_login) {
                      <span class="ml-2 text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-confidence-high/15 text-confidence-high align-middle">portal</span>
                    }
                  </p>
                  <p class="text-xs text-text-muted mt-0.5 truncate">
                    {{ e.title || employmentLabel(e.employment_type) }} · {{ e.email }}
                  </p>
                </div>
                <div class="text-right flex-none hidden sm:block">
                  <p class="text-xs text-text-muted">{{ employmentLabel(e.employment_type) }}</p>
                  @if (e.default_bill_rate) {
                    <p class="text-xs text-text-secondary mt-0.5">{{ e.default_bill_rate_currency || '' }} {{ e.default_bill_rate }}/h</p>
                  }
                </div>
                @if (!e.has_login) {
                  <button type="button"
                    class="text-text-muted hover:text-accent-light transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded p-1"
                    aria-label="Invite to timesheet portal" title="Invite to timesheet portal" (click)="invite(e)">
                    <mat-icon class="text-base leading-none">person_add</mat-icon>
                  </button>
                }
                <button type="button"
                  class="text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded p-1"
                  aria-label="Edit employee" (click)="openEdit(e)">
                  <mat-icon class="text-base leading-none">edit</mat-icon>
                </button>
                <button type="button"
                  class="text-text-muted hover:text-confidence-low transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-confidence-low rounded p-1"
                  aria-label="Remove employee" (click)="remove(e)">
                  <mat-icon class="text-base leading-none">delete_outline</mat-icon>
                </button>
              </div>
            }
          </div>
        </div>
      }
    </section>

    @if (showPanel()) {
      <div class="fixed inset-0 bg-black/50 z-40" (click)="closePanel()" aria-hidden="true"></div>
      <aside class="fixed right-0 top-0 h-full w-full max-w-md bg-surface border-l border-border-default z-50 flex flex-col shadow-2xl"
        role="dialog" aria-modal="true" aria-labelledby="emp-panel-title">
        <div class="flex items-center justify-between px-6 py-4 border-b border-border-default flex-none">
          <h2 id="emp-panel-title" class="text-base font-semibold text-text-primary">{{ editingId() ? 'Edit employee' : 'New employee' }}</h2>
          <button class="text-text-muted hover:text-text-primary transition-colors rounded" (click)="closePanel()" aria-label="Close panel">
            <mat-icon>close</mat-icon>
          </button>
        </div>
        <form [formGroup]="form" class="flex-1 overflow-y-auto px-6 py-5 space-y-5" novalidate>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-xs uppercase tracking-wide text-text-muted mb-2">First name *</label>
              <input type="text" formControlName="first_name" class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary text-sm focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent" />
            </div>
            <div>
              <label class="block text-xs uppercase tracking-wide text-text-muted mb-2">Last name *</label>
              <input type="text" formControlName="last_name" class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary text-sm focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent" />
            </div>
          </div>
          <div>
            <label class="block text-xs uppercase tracking-wide text-text-muted mb-2">Email *</label>
            <input type="email" formControlName="email" placeholder="name@firm.com" class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary text-sm focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent" />
            @if (form.controls.email.touched && form.controls.email.errors) {
              <p class="text-xs text-confidence-low mt-1">A valid email is required.</p>
            }
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-xs uppercase tracking-wide text-text-muted mb-2">Title</label>
              <input type="text" formControlName="title" placeholder="e.g. Senior Consultant" class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary text-sm focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent" />
            </div>
            <div>
              <label class="block text-xs uppercase tracking-wide text-text-muted mb-2">Department</label>
              <input type="text" formControlName="department" class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary text-sm focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent" />
            </div>
          </div>
          <div>
            <label class="block text-xs uppercase tracking-wide text-text-muted mb-2">Employment type *</label>
            <select formControlName="employment_type" class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary text-sm focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent">
              <option value="full_time">Full-time</option>
              <option value="part_time">Part-time</option>
              <option value="contractor">Contractor</option>
              <option value="consultant">Consultant</option>
            </select>
          </div>
          <div class="grid grid-cols-3 gap-3">
            <div class="col-span-2">
              <label class="block text-xs uppercase tracking-wide text-text-muted mb-2">Bill rate / hr</label>
              <input type="number" min="0" step="0.01" formControlName="default_bill_rate" class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary text-sm focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent" />
            </div>
            <div>
              <label class="block text-xs uppercase tracking-wide text-text-muted mb-2">Currency</label>
              <input type="text" maxlength="3" formControlName="default_bill_rate_currency" placeholder="USD" class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary text-sm uppercase focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent" />
            </div>
          </div>
          <div>
            <label class="block text-xs uppercase tracking-wide text-text-muted mb-2">Cost rate / hr</label>
            <input type="number" min="0" step="0.01" formControlName="cost_rate" class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary text-sm focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent" />
          </div>
          @if (editingId()) {
            <div>
              <label class="block text-xs uppercase tracking-wide text-text-muted mb-2">Status</label>
              <select formControlName="status" class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary text-sm focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent">
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
          }
          @if (panelError()) {
            <div role="alert" class="text-sm text-confidence-low bg-confidence-low/10 border border-confidence-low/30 rounded px-3 py-2">{{ panelError() }}</div>
          }
        </form>
        <div class="flex-none px-6 py-4 border-t border-border-default flex items-center justify-end gap-3">
          <button type="button" class="px-4 py-2 text-sm text-text-muted hover:text-text-primary transition-colors rounded" (click)="closePanel()">Cancel</button>
          <button type="button"
            class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            [disabled]="form.invalid || saving()" (click)="save()">
            @if (saving()) { Saving… } @else { {{ editingId() ? 'Save changes' : 'Create employee' }} }
          </button>
        </div>
      </aside>
    }

    <!-- Invite result modal -->
    @if (inviteResult(); as inv) {
      <div class="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" (click)="dismissInvite()" aria-hidden="true"></div>
      <div class="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
        <div class="w-full max-w-md bg-surface border border-border-default rounded-xl shadow-2xl pointer-events-auto" role="dialog" aria-modal="true" aria-labelledby="invite-title">
          <div class="px-6 py-4 border-b border-border-default flex items-center gap-2">
            <mat-icon class="text-confidence-high">check_circle</mat-icon>
            <h2 id="invite-title" class="text-base font-semibold text-text-primary">Portal access granted</h2>
          </div>
          <div class="px-6 py-5 space-y-4 text-sm">
            <p class="text-text-secondary">
              <span class="font-medium text-text-primary">{{ inv.email }}</span> can now sign in to the
              Timesheet Portal. Share the link below so they can set their own password.
            </p>
            @if (inv.set_password_url) {
              <div>
                <label class="block text-xs uppercase tracking-wide text-text-muted mb-1">Set-password link</label>
                <div class="flex gap-2">
                  <input readonly [value]="inv.set_password_url" class="flex-1 px-3 py-2 bg-surface-base border border-border-default rounded text-text-secondary text-xs font-mono truncate" />
                  <button type="button" class="px-3 py-2 bg-surface-raised hover:bg-surface-base border border-border-default rounded text-xs text-text-primary" (click)="copy(inv.set_password_url!)">Copy</button>
                </div>
              </div>
            }
            @if (inv.temp_password) {
              <div>
                <label class="block text-xs uppercase tracking-wide text-text-muted mb-1">Temporary password (shown once)</label>
                <div class="flex gap-2">
                  <input readonly [value]="inv.temp_password" class="flex-1 px-3 py-2 bg-surface-base border border-border-default rounded text-text-secondary text-xs font-mono" />
                  <button type="button" class="px-3 py-2 bg-surface-raised hover:bg-surface-base border border-border-default rounded text-xs text-text-primary" (click)="copy(inv.temp_password!)">Copy</button>
                </div>
                <p class="text-xs text-text-muted mt-1">Pilot only — email delivery is not yet enabled.</p>
              </div>
            }
          </div>
          <div class="px-6 py-4 border-t border-border-default flex justify-end">
            <button type="button" class="px-4 py-2 text-sm bg-accent hover:bg-accent-hover text-accent-on rounded font-medium" (click)="dismissInvite()">Done</button>
          </div>
        </div>
      </div>
    }
  `,
})
export class PeopleListComponent implements OnInit {
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);

  loading = signal(true);
  error = signal<string | null>(null);
  employees = signal<Employee[]>([]);

  showPanel = signal(false);
  editingId = signal<string | null>(null);
  saving = signal(false);
  panelError = signal<string | null>(null);

  form = this.fb.nonNullable.group({
    first_name: ['', [Validators.required]],
    last_name: ['', [Validators.required]],
    email: ['', [Validators.required, Validators.email]],
    title: [''],
    department: [''],
    employment_type: ['full_time' as string, [Validators.required]],
    default_bill_rate: [null as number | null],
    default_bill_rate_currency: ['' as string],
    cost_rate: [null as number | null],
    status: ['active' as string],
  });

  ngOnInit(): void {
    this.load();
  }

  private load(): void {
    this.loading.set(true);
    this.http.get<EmployeeListResponse>('/api/v1/employees').subscribe({
      next: (res) => {
        this.employees.set(res.items ?? []);
        this.loading.set(false);
      },
      error: (err: { status?: number }) => {
        if (err.status === 404) this.employees.set([]);
        else this.error.set('Could not load people. Please refresh to try again.');
        this.loading.set(false);
      },
    });
  }

  initials(e: Employee): string {
    return `${e.first_name?.[0] ?? ''}${e.last_name?.[0] ?? ''}`.toUpperCase();
  }

  employmentLabel(t: string): string {
    return EMPLOYMENT_LABELS[t] ?? t;
  }

  openCreate(): void {
    this.editingId.set(null);
    this.panelError.set(null);
    this.form.reset({
      first_name: '', last_name: '', email: '', title: '', department: '',
      employment_type: 'full_time', default_bill_rate: null,
      default_bill_rate_currency: '', cost_rate: null, status: 'active',
    });
    this.showPanel.set(true);
  }

  openEdit(e: Employee): void {
    this.editingId.set(e.id);
    this.panelError.set(null);
    this.form.reset({
      first_name: e.first_name,
      last_name: e.last_name,
      email: e.email,
      title: e.title ?? '',
      department: e.department ?? '',
      employment_type: e.employment_type,
      default_bill_rate: e.default_bill_rate != null ? Number(e.default_bill_rate) : null,
      default_bill_rate_currency: e.default_bill_rate_currency ?? '',
      cost_rate: e.cost_rate != null ? Number(e.cost_rate) : null,
      status: e.status,
    });
    this.showPanel.set(true);
  }

  closePanel(): void {
    this.showPanel.set(false);
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.panelError.set(null);
    const v = this.form.getRawValue();
    const body: Record<string, unknown> = {
      first_name: v.first_name,
      last_name: v.last_name,
      email: v.email,
      title: v.title || null,
      department: v.department || null,
      employment_type: v.employment_type,
      default_bill_rate: v.default_bill_rate != null ? String(v.default_bill_rate) : null,
      default_bill_rate_currency: v.default_bill_rate_currency
        ? v.default_bill_rate_currency.toUpperCase()
        : null,
      cost_rate: v.cost_rate != null ? String(v.cost_rate) : null,
    };

    const id = this.editingId();
    if (id) {
      body['status'] = v.status;
      this.http.patch<Employee>(`/api/v1/employees/${id}`, body).subscribe({
        next: (updated) => {
          this.employees.update((list) => list.map((e) => (e.id === id ? updated : e)));
          this.saving.set(false);
          this.closePanel();
        },
        error: (err) => this.onSaveError(err),
      });
    } else {
      this.http.post<Employee>('/api/v1/employees', body).subscribe({
        next: (created) => {
          this.employees.update((list) => [created, ...list]);
          this.saving.set(false);
          this.closePanel();
        },
        error: (err) => this.onSaveError(err),
      });
    }
  }

  private onSaveError(err: { error?: { detail?: unknown } }): void {
    this.saving.set(false);
    const detail = err?.error?.detail;
    this.panelError.set(
      typeof detail === 'string' ? detail : 'Could not save. Please check the fields and try again.'
    );
  }

  // -------------------------------------------------------------------------
  // Invite to portal (issue #134, Phase 3)
  // -------------------------------------------------------------------------
  inviteResult = signal<InviteResult | null>(null);

  invite(e: Employee): void {
    if (!confirm(`Grant ${e.first_name} ${e.last_name} access to the Timesheet Portal?`)) return;
    this.http.post<InviteResult>(`/api/v1/employees/${e.id}/invite`, {}).subscribe({
      next: (res) => {
        this.inviteResult.set(res);
        this.employees.update((list) => list.map((x) => (x.id === e.id ? { ...x, has_login: true } : x)));
      },
      error: (err: { error?: { detail?: unknown } }) => {
        const detail = err?.error?.detail;
        this.error.set(typeof detail === 'string' ? detail : 'Could not grant portal access.');
      },
    });
  }

  dismissInvite(): void {
    this.inviteResult.set(null);
  }

  copy(text: string): void {
    navigator.clipboard?.writeText(text).catch(() => { /* clipboard may be blocked */ });
  }

  remove(e: Employee): void {
    if (!confirm(`Remove ${e.first_name} ${e.last_name}? Their past time entries are preserved.`)) return;
    this.http.delete<void>(`/api/v1/employees/${e.id}`).subscribe({
      next: () => this.employees.update((list) => list.filter((x) => x.id !== e.id)),
      error: () => this.error.set('Could not remove employee. Please try again.'),
    });
  }
}
