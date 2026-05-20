import { Component, inject, signal, OnInit } from '@angular/core';
import { SlicePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
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

@Component({
  selector: 'app-time-entries-list',
  standalone: true,
  imports: [
    SlicePipe,
    FormsModule,
    MatTableModule,
    MatIconModule,
    MatButtonModule,
    MatChipsModule,
    MatTooltipModule,
  ],
  template: `
    <div class="p-6 bg-slate-900 min-h-full">
      <!-- Page header -->
      <div class="mb-6">
        <h1 class="text-2xl font-bold text-slate-50">Time Entries</h1>
        <p class="text-sm text-slate-400 mt-1">Log and review billable hours across your projects.</p>
      </div>

      <!-- Quick-add row -->
      <div class="bg-slate-800 border border-slate-700 rounded-lg p-4 mb-6" role="region" aria-label="Add time entry">
        <h2 class="text-xs font-medium text-slate-400 uppercase tracking-wide mb-3">Quick Add</h2>
        <form
          (ngSubmit)="submitEntry()"
          class="flex flex-wrap gap-3 items-end"
          aria-label="New time entry form"
        >
          <div class="flex flex-col gap-1">
            <label for="entry-date" class="text-xs text-slate-400">Date</label>
            <input
              id="entry-date"
              type="date"
              [(ngModel)]="newDate"
              name="entry-date"
              required
              class="bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-sm text-slate-50
                     focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
                     placeholder:text-slate-500"
            />
          </div>

          <div class="flex flex-col gap-1">
            <label for="entry-hours" class="text-xs text-slate-400">Hours</label>
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
              class="w-24 bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-sm text-slate-50
                     focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
                     placeholder:text-slate-500"
            />
          </div>

          <div class="flex flex-col gap-1 flex-1 min-w-40">
            <label for="entry-description" class="text-xs text-slate-400">Description</label>
            <input
              id="entry-description"
              type="text"
              [(ngModel)]="newDescription"
              name="entry-description"
              placeholder="What did you work on?"
              required
              (keydown.enter)="submitEntry()"
              class="bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-sm text-slate-50
                     focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
                     placeholder:text-slate-500"
            />
          </div>

          <div class="flex flex-col gap-1">
            <label class="text-xs text-slate-400">Billable</label>
            <label class="flex items-center gap-2 cursor-pointer h-[34px]">
              <input
                type="checkbox"
                [(ngModel)]="newBillable"
                name="entry-billable"
                class="w-4 h-4 rounded border-slate-600 bg-slate-700 text-emerald-500
                       focus:ring-emerald-500 focus:ring-offset-slate-900"
              />
              <span class="text-sm text-slate-300">Yes</span>
            </label>
          </div>

          <button
            type="submit"
            [disabled]="addingEntry()"
            mat-flat-button
            class="bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-1.5 rounded
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
          <p class="mt-2 text-xs text-red-400" role="alert">{{ addError() }}</p>
        }
      </div>

      <!-- Loading skeleton -->
      @if (loading()) {
        <div class="rounded-lg overflow-hidden border border-slate-700 animate-pulse" aria-busy="true" aria-label="Loading time entries">
          @for (row of [1, 2, 3, 4]; track row) {
            <div class="flex gap-4 px-4 py-3 border-b border-slate-800 last:border-0 bg-slate-800">
              <div class="h-4 bg-slate-700 rounded w-24"></div>
              <div class="h-4 bg-slate-700 rounded w-32"></div>
              <div class="h-4 bg-slate-700 rounded w-12"></div>
              <div class="h-4 bg-slate-700 rounded flex-1"></div>
              <div class="h-4 bg-slate-700 rounded w-16"></div>
              <div class="h-4 bg-slate-700 rounded w-20"></div>
            </div>
          }
        </div>
      }

      <!-- Error state -->
      @if (error() && !loading()) {
        <div class="rounded-lg border border-red-900 bg-red-950 px-4 py-3 text-sm text-red-400" role="alert">
          <mat-icon class="text-base align-middle mr-1">error_outline</mat-icon>
          Something went wrong loading time entries. Please try again.
        </div>
      }

      <!-- Empty state -->
      @if (!loading() && !error() && entries().length === 0) {
        <div class="rounded-lg border border-slate-700 bg-slate-800 px-4 py-12 text-center">
          <mat-icon class="text-4xl text-slate-500 mb-3 block">schedule</mat-icon>
          <p class="text-slate-300 font-medium mb-1">No time entries yet</p>
          <p class="text-slate-500 text-sm">Use the quick-add form above to log your first hours.</p>
        </div>
      }

      <!-- Table -->
      @if (!loading() && !error() && entries().length > 0) {
        <div class="rounded-lg overflow-hidden border border-slate-700">
          <table
            mat-table
            [dataSource]="entries()"
            class="w-full bg-slate-900"
            aria-label="Time entries"
          >
            <!-- Date column -->
            <ng-container matColumnDef="date">
              <th mat-header-cell *matHeaderCellDef
                  class="text-slate-400 text-xs font-medium uppercase tracking-wide bg-slate-800 border-b border-slate-700 px-4 py-3">
                Date
              </th>
              <td mat-cell *matCellDef="let row"
                  class="text-slate-300 text-sm px-4 py-3 border-b border-slate-800 tabular-nums">
                {{ row.date }}
              </td>
            </ng-container>

            <!-- Employee column (placeholder — employee lookup not wired yet) -->
            <ng-container matColumnDef="employee">
              <th mat-header-cell *matHeaderCellDef
                  class="text-slate-400 text-xs font-medium uppercase tracking-wide bg-slate-800 border-b border-slate-700 px-4 py-3">
                Employee
              </th>
              <td mat-cell *matCellDef="let row"
                  class="text-slate-400 text-sm px-4 py-3 border-b border-slate-800 font-mono">
                {{ row.employee_id | slice:0:8 }}…
              </td>
            </ng-container>

            <!-- Hours column -->
            <ng-container matColumnDef="hours">
              <th mat-header-cell *matHeaderCellDef
                  class="text-slate-400 text-xs font-medium uppercase tracking-wide bg-slate-800 border-b border-slate-700 px-4 py-3 text-right">
                Hours
              </th>
              <td mat-cell *matCellDef="let row"
                  class="text-slate-50 text-sm font-mono px-4 py-3 border-b border-slate-800 text-right tabular-nums">
                {{ row.hours }}
              </td>
            </ng-container>

            <!-- Description column -->
            <ng-container matColumnDef="description">
              <th mat-header-cell *matHeaderCellDef
                  class="text-slate-400 text-xs font-medium uppercase tracking-wide bg-slate-800 border-b border-slate-700 px-4 py-3">
                Description
              </th>
              <td mat-cell *matCellDef="let row"
                  class="text-slate-50 text-sm px-4 py-3 border-b border-slate-800 max-w-xs truncate">
                {{ row.description }}
              </td>
            </ng-container>

            <!-- Billable column -->
            <ng-container matColumnDef="billable">
              <th mat-header-cell *matHeaderCellDef
                  class="text-slate-400 text-xs font-medium uppercase tracking-wide bg-slate-800 border-b border-slate-700 px-4 py-3">
                Billable
              </th>
              <td mat-cell *matCellDef="let row" class="px-4 py-3 border-b border-slate-800">
                <span
                  class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium"
                  [class]="row.billable ? 'bg-emerald-900 text-emerald-400' : 'bg-slate-700 text-slate-400'"
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
                  class="text-slate-400 text-xs font-medium uppercase tracking-wide bg-slate-800 border-b border-slate-700 px-4 py-3">
                Status
              </th>
              <td mat-cell *matCellDef="let row" class="px-4 py-3 border-b border-slate-800">
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
                class="hover:bg-slate-800 transition-colors"></tr>
          </table>
        </div>

        <!-- Row count summary -->
        <p class="text-xs text-slate-500 mt-3 text-right">
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

  loading    = signal(true);
  error      = signal<string | null>(null);
  entries    = signal<TimeEntry[]>([]);
  addingEntry = signal(false);
  addError   = signal<string | null>(null);

  // Quick-add form state
  newDate        = new Date().toISOString().split('T')[0];
  newHours       = '';
  newDescription = '';
  newBillable    = true;

  displayedColumns = ['date', 'employee', 'hours', 'description', 'billable', 'billing_status'];

  ngOnInit(): void {
    this.loadEntries();
  }

  private loadEntries(): void {
    this.loading.set(true);
    this.error.set(null);
    this.timeEntriesService.getEntries().subscribe({
      next: (res) => {
        this.entries.set(res.items);
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
    if (!this.newDate || !hours || !description) return;

    this.addingEntry.set(true);
    this.addError.set(null);

    const payload: TimeEntryCreate = {
      date: this.newDate,
      hours,
      description,
      billable: this.newBillable,
    };

    // Optimistic update — prepend a placeholder immediately
    const optimisticEntry: TimeEntry = {
      id: `optimistic-${Date.now()}`,
      project_id: '',
      employee_id: '',
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
      error: () => {
        // Roll back the optimistic update
        this.entries.set(this.entries().filter(e => e.id !== optimisticEntry.id));
        this.addingEntry.set(false);
        this.addError.set('Could not save the entry. Please try again.');
      },
    });
  }

  billingStatusClass(status: string): string {
    switch (status) {
      case 'unbilled':     return 'bg-amber-950 text-amber-400';
      case 'billed':       return 'bg-emerald-900 text-emerald-400';
      case 'non_billable': return 'bg-slate-700 text-slate-400';
      default:             return 'bg-slate-700 text-slate-400';
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
