import { Component, computed, inject, signal, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { MatTableModule } from '@angular/material/table';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';

import {
  TimeEntriesService,
  TimeEntry,
  TimeEntryCreate,
} from '../../core/services/time-entries.service';
import { EmptyStateComponent } from '../../shared/components/empty-state.component';
import { SkeletonRowsComponent } from '../../shared/components/skeleton-rows.component';

@Component({
  selector: 'app-time-entries-list',
  standalone: true,
  imports: [
    FormsModule,
    MatTableModule,
    MatIconModule,
    MatButtonModule,
    MatChipsModule,
    MatTooltipModule,
    EmptyStateComponent,
    SkeletonRowsComponent,
    RouterLink,
  ],
  template: `
    <div class="p-6 bg-surface-base min-h-full">
      <!-- Page header -->
      <div class="mb-6">
        <h1 class="text-2xl font-bold text-text-primary">Time Entries</h1>
        <p class="text-sm text-text-muted mt-1">Log and review billable hours across your projects.</p>
      </div>

      <!-- Quick-add row -->
      <div class="bg-surface-raised border border-border-default rounded-lg p-4 mb-6" role="region" aria-label="Add time entry">
        <h2 class="text-xs font-medium text-text-muted uppercase tracking-wide mb-3">Quick Add</h2>

        <!-- Prerequisites banner — without a project or employee the form is unusable. -->
        @if (!loadingPrereqs() && missingPrereqs().length > 0) {
          <div class="mb-3 rounded-md border border-confidence-med/30 bg-confidence-med/10 px-4 py-3 text-sm text-confidence-med" role="status">
            <p class="font-medium mb-1">You can't log time yet.</p>
            <p class="text-text-secondary mb-2">
              You need at least one
              @for (p of missingPrereqs(); track p.route; let last = $last) {
                <a [routerLink]="p.route" class="text-accent-light underline hover:text-accent">{{ p.label }}</a>@if (!last) { <span> and one </span> }
              }
              before adding entries.
            </p>
          </div>
        }

        <form
          (ngSubmit)="submitEntry()"
          class="flex flex-wrap gap-3 items-end"
          aria-label="New time entry form"
        >
          <div class="flex flex-col gap-1 min-w-44">
            <label for="entry-project" class="text-xs text-text-muted">Project</label>
            <select
              id="entry-project"
              [(ngModel)]="newProjectId"
              name="entry-project"
              required
              class="bg-surface border border-border-strong rounded px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            >
              <option value="">Select project…</option>
              @for (p of projects(); track p.id) {
                <option [value]="p.id">{{ p.code ? p.code + ' · ' : '' }}{{ p.name }}</option>
              }
            </select>
          </div>

          <div class="flex flex-col gap-1 min-w-44">
            <label for="entry-employee" class="text-xs text-text-muted">Employee</label>
            <select
              id="entry-employee"
              [(ngModel)]="newEmployeeId"
              name="entry-employee"
              required
              class="bg-surface border border-border-strong rounded px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            >
              <option value="">Select employee…</option>
              @for (e of employees(); track e.id) {
                <option [value]="e.id">{{ e.first_name }} {{ e.last_name }}</option>
              }
            </select>
          </div>

          <div class="flex flex-col gap-1">
            <label for="entry-date" class="text-xs text-text-muted">Date</label>
            <input
              id="entry-date"
              type="date"
              [(ngModel)]="newDate"
              name="entry-date"
              required
              class="bg-surface border border-border-strong rounded px-3 py-1.5 text-sm text-text-primary
                     focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
                     placeholder:text-text-disabled"
            />
          </div>

          <div class="flex flex-col gap-1">
            <label for="entry-hours" class="text-xs text-text-muted">Hours</label>
            <input
              id="entry-hours"
              type="number"
              [(ngModel)]="newHours"
              name="entry-hours"
              min="0.25"
              max="24"
              step="0.25"
              placeholder="0.00"
              required
              class="w-24 bg-surface border border-border-strong rounded px-3 py-1.5 text-sm text-text-primary
                     focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
                     placeholder:text-text-disabled"
            />
          </div>

          <div class="flex flex-col gap-1 flex-1 min-w-40">
            <label for="entry-description" class="text-xs text-text-muted">Description</label>
            <input
              id="entry-description"
              type="text"
              [(ngModel)]="newDescription"
              name="entry-description"
              placeholder="What did you work on?"
              required
              (keydown.enter)="submitEntry()"
              class="bg-surface border border-border-strong rounded px-3 py-1.5 text-sm text-text-primary
                     focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
                     placeholder:text-text-disabled"
            />
          </div>

          <div class="flex flex-col gap-1">
            <label class="text-xs text-text-muted">Billable</label>
            <label class="flex items-center gap-2 cursor-pointer h-[34px]">
              <input
                type="checkbox"
                [(ngModel)]="newBillable"
                name="entry-billable"
                class="w-4 h-4 rounded border-border-strong bg-surface text-accent
                       focus:ring-emerald-500 focus:ring-offset-slate-900"
              />
              <span class="text-sm text-text-secondary">Yes</span>
            </label>
          </div>

          <button
            type="submit"
            [disabled]="addingEntry() || missingPrereqs().length > 0"
            mat-flat-button
            class="bg-indigo-600 hover:bg-indigo-500 text-text-primary text-sm font-medium px-4 py-1.5 rounded
                   disabled:opacity-50 disabled:cursor-not-allowed transition-colors
                   focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-400"
            aria-label="Add time entry"
          >
            @if (addingEntry()) {
              <mat-icon class="animate-spin text-base">refresh</mat-icon>
            } @else {
              <mat-icon class="text-base">add</mat-icon>
            }
            Add
          </button>
        </form>

        @if (addError()) {
          <p class="mt-2 text-xs text-confidence-low" role="alert">{{ addError() }}</p>
        }
      </div>

      <!-- Loading skeleton -->
      @if (loading()) {
        <app-skeleton-rows [count]="4" ariaLabel="Loading time entries" />
      }

      <!-- Error state -->
      @if (error() && !loading()) {
        <div class="rounded-lg border border-confidence-low/30 bg-confidence-low/10 px-4 py-3 text-sm text-confidence-low" role="alert">
          <mat-icon class="text-base align-middle mr-1">error_outline</mat-icon>
          Something went wrong loading time entries. Please try again.
        </div>
      }

      <!-- Empty state -->
      @if (!loading() && !error() && entries().length === 0) {
        <app-empty-state
          icon="schedule"
          heading="No time entries yet"
          message="Use the quick-add form above to log your first hours."
        />
      }

      <!-- Table -->
      @if (!loading() && !error() && entries().length > 0) {
        <div class="rounded-lg overflow-hidden border border-border-default">
          <table
            mat-table
            [dataSource]="entries()"
            class="w-full bg-surface-base"
            aria-label="Time entries"
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

            <!-- Project column -->
            <ng-container matColumnDef="project">
              <th mat-header-cell *matHeaderCellDef
                  class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Project
              </th>
              <td mat-cell *matCellDef="let row"
                  class="text-text-secondary text-sm px-4 py-3 border-b border-border-subtle">
                {{ projectLabel(row.project_id) }}
              </td>
            </ng-container>

            <!-- Employee column -->
            <ng-container matColumnDef="employee">
              <th mat-header-cell *matHeaderCellDef
                  class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Employee
              </th>
              <td mat-cell *matCellDef="let row"
                  class="text-text-secondary text-sm px-4 py-3 border-b border-border-subtle">
                {{ employeeLabel(row.employee_id) }}
              </td>
            </ng-container>

            <!-- Hours column -->
            <ng-container matColumnDef="hours">
              <th mat-header-cell *matHeaderCellDef
                  class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3 text-right">
                Hours
              </th>
              <td mat-cell *matCellDef="let row"
                  class="text-text-primary text-sm font-mono px-4 py-3 border-b border-border-subtle text-right tabular-nums">
                {{ row.hours }}
              </td>
            </ng-container>

            <!-- Description column -->
            <ng-container matColumnDef="description">
              <th mat-header-cell *matHeaderCellDef
                  class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Description
              </th>
              <td mat-cell *matCellDef="let row"
                  class="text-text-primary text-sm px-4 py-3 border-b border-border-subtle max-w-xs truncate">
                {{ row.description }}
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

            <!-- Billing status column -->
            <ng-container matColumnDef="billing_status">
              <th mat-header-cell *matHeaderCellDef
                  class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Status
              </th>
              <td mat-cell *matCellDef="let row" class="px-4 py-3 border-b border-border-subtle">
                <span
                  class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                  [class]="billingStatusClass(row.billing_status)"
                >
                  {{ billingStatusLabel(row.billing_status) }}
                </span>
              </td>
            </ng-container>

            <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
            <tr mat-row *matRowDef="let row; columns: displayedColumns"
                class="hover:bg-surface-raised transition-colors"></tr>
          </table>
        </div>

        <!-- Row count summary -->
        <p class="text-xs text-text-disabled mt-3 text-right">
          {{ entries().length }} {{ entries().length === 1 ? 'entry' : 'entries' }}
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
export class TimeEntriesListComponent implements OnInit {
  private timeEntriesService = inject(TimeEntriesService);
  private http = inject(HttpClient);

  loading    = signal(true);
  error      = signal<string | null>(null);
  entries    = signal<TimeEntry[]>([]);
  addingEntry = signal(false);
  addError   = signal<string | null>(null);
  projects   = signal<{ id: string; name: string; code?: string | null }[]>([]);
  employees  = signal<{ id: string; first_name: string; last_name: string }[]>([]);

  /** True until both /projects and /employees have responded; lets the banner avoid flickering on first paint. */
  loadingPrereqs = signal(true);

  /** Surfaces what's missing so the form isn't silently unusable. */
  missingPrereqs = computed<{ label: string; route: string }[]>(() => {
    const out: { label: string; route: string }[] = [];
    if (this.projects().length === 0) out.push({ label: 'project', route: '/app/projects' });
    if (this.employees().length === 0) out.push({ label: 'employee', route: '/app/people' });
    return out;
  });

  // Quick-add form state
  newProjectId   = '';
  newEmployeeId  = '';
  newDate        = new Date().toISOString().split('T')[0];
  newHours       = '';
  newDescription = '';
  newBillable    = true;

  displayedColumns = ['date', 'project', 'employee', 'hours', 'description', 'billable', 'billing_status'];

  ngOnInit(): void {
    this.loadEntries();
    let pending = 2;
    const settle = () => {
      pending -= 1;
      if (pending <= 0) this.loadingPrereqs.set(false);
    };
    this.http.get<{ id: string; name: string; code?: string | null }[]>('/api/v1/projects')
      .subscribe({
        next: (list) => { this.projects.set(list ?? []); settle(); },
        error: () => settle(),
      });
    this.http.get<{ items: { id: string; first_name: string; last_name: string }[] }>('/api/v1/employees')
      .subscribe({
        next: (res) => { this.employees.set(res.items ?? []); settle(); },
        error: () => settle(),
      });
  }

  projectLabel(id: string): string {
    const p = this.projects().find((x) => x.id === id);
    return p ? `${p.code ? p.code + ' · ' : ''}${p.name}` : '—';
  }

  employeeLabel(id: string): string {
    const e = this.employees().find((x) => x.id === id);
    return e ? `${e.first_name} ${e.last_name}` : '—';
  }

  private loadEntries(): void {
    this.loading.set(true);
    this.error.set(null);
    this.timeEntriesService.getEntries().subscribe({
      next: (res) => {
        this.entries.set(res);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Failed to load');
        this.loading.set(false);
      },
    });
  }

  submitEntry(): void {
    const hours = this.newHours.trim();
    const description = this.newDescription.trim();
    if (!this.newProjectId || !this.newEmployeeId || !this.newDate || !hours || !description) {
      this.addError.set('Project, employee, date, hours and description are all required.');
      return;
    }

    this.addingEntry.set(true);
    this.addError.set(null);

    const payload: TimeEntryCreate = {
      project_id: this.newProjectId,
      employee_id: this.newEmployeeId,
      date: this.newDate,
      hours,
      description,
      billable: this.newBillable,
    };

    // Optimistic update — prepend a placeholder immediately
    const optimisticEntry: TimeEntry = {
      id: `optimistic-${Date.now()}`,
      project_id: this.newProjectId,
      employee_id: this.newEmployeeId,
      date: this.newDate,
      hours,
      description,
      billable: this.newBillable,
      billing_status: this.newBillable ? 'unbilled' : 'non_billable',
    };
    this.entries.set([optimisticEntry, ...this.entries()]);

    this.timeEntriesService.createEntry(payload).subscribe({
      next: (created) => {
        // Replace the optimistic placeholder with the real record
        this.entries.set([
          created,
          ...this.entries().filter(e => e.id !== optimisticEntry.id),
        ]);
        this.addingEntry.set(false);
        this.newHours = '';
        this.newDescription = '';
      },
      error: (err: { error?: { detail?: unknown } }) => {
        // Roll back the optimistic update
        this.entries.set(this.entries().filter(e => e.id !== optimisticEntry.id));
        this.addingEntry.set(false);
        const detail = err?.error?.detail;
        this.addError.set(
          typeof detail === 'string' ? detail : 'Could not save the entry. Please try again.'
        );
      },
    });
  }

  billingStatusClass(status: string): string {
    switch (status) {
      case 'unbilled':     return 'bg-confidence-med/10 text-confidence-med';
      case 'billed':       return 'bg-accent/15 text-accent-light';
      case 'non_billable': return 'bg-surface text-text-muted';
      default:             return 'bg-surface text-text-muted';
    }
  }

  billingStatusLabel(status: string): string {
    switch (status) {
      case 'unbilled':     return 'Unbilled';
      case 'billed':       return 'Billed';
      case 'non_billable': return 'Non-billable';
      default:             return status;
    }
  }
}
