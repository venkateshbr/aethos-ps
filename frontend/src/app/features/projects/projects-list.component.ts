import { Component, inject, input, signal, OnInit } from '@angular/core';
import { TitleCasePipe } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatIconModule } from '@angular/material/icon';

import { EngagementService, ProjectSummary } from '../../core/services/engagement.service';
import { MoneyPipe } from '../../shared/pipes/money.pipe';
import { userMessageForError } from '../../core/utils/error-message';

@Component({
  selector: 'app-projects-list',
  standalone: true,
  imports: [
    TitleCasePipe,
    MatTableModule,
    MatIconModule,
    MoneyPipe,
  ],
  template: `
    <!-- Loading skeleton -->
    @if (loading()) {
      <div class="rounded-lg overflow-hidden border border-border-default animate-pulse" aria-busy="true" aria-label="Loading projects">
        @for (row of [1, 2]; track row) {
          <div class="flex gap-4 px-4 py-3 border-b border-border-subtle last:border-0">
            <div class="h-4 bg-surface-raised rounded w-1/3"></div>
            <div class="h-4 bg-surface-raised rounded w-1/6"></div>
            <div class="h-4 bg-surface-raised rounded w-1/6"></div>
            <div class="h-4 bg-surface-raised rounded w-1/12"></div>
          </div>
        }
      </div>
    }

    <!-- Error state -->
    @if (error() && !loading()) {
      <div class="rounded-lg border border-confidence-low/30 bg-confidence-low/10 px-4 py-3 text-sm text-confidence-low" role="alert">
        <mat-icon class="text-base align-middle mr-1">error_outline</mat-icon>
        {{ error() }}
      </div>
    }

    <!-- Empty state -->
    @if (!loading() && !error() && projects().length === 0) {
      <div class="rounded-lg border border-border-default bg-surface-raised px-4 py-8 text-center">
        <mat-icon class="text-3xl text-text-disabled mb-2 block">folder_open</mat-icon>
        <p class="text-text-muted text-sm">No projects on this engagement yet.</p>
      </div>
    }

    <!-- Table -->
    @if (!loading() && !error() && projects().length > 0) {
      <div class="rounded-lg overflow-hidden border border-border-default">
        <table
          mat-table
          [dataSource]="projects()"
          class="w-full bg-surface-base"
          aria-label="Projects"
        >
          <!-- Name column -->
          <ng-container matColumnDef="name">
            <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
              Project
            </th>
            <td mat-cell *matCellDef="let row" class="text-text-primary text-sm font-medium px-4 py-3 border-b border-border-subtle">
              {{ row.name }}
            </td>
          </ng-container>

          <!-- Currency column -->
          <ng-container matColumnDef="currency">
            <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
              Currency
            </th>
            <td mat-cell *matCellDef="let row" class="text-text-muted text-sm font-mono px-4 py-3 border-b border-border-subtle">
              {{ row.currency }}
            </td>
          </ng-container>

          <!-- Budget column -->
          <ng-container matColumnDef="budget">
            <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3 text-right">
              Budget
            </th>
            <td mat-cell *matCellDef="let row" class="text-text-primary text-sm font-mono px-4 py-3 border-b border-border-subtle text-right tabular-nums">
              {{ row.budget | money: row.currency }}
            </td>
          </ng-container>

          <!-- Status column -->
          <ng-container matColumnDef="status">
            <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
              Status
            </th>
            <td mat-cell *matCellDef="let row" class="px-4 py-3 border-b border-border-subtle">
              <span
                class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium"
                [class]="statusClass(row.status)"
                [attr.aria-label]="'Project status: ' + row.status"
              >
                {{ row.status | titlecase }}
              </span>
            </td>
          </ng-container>

          <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
          <tr mat-row *matRowDef="let row; columns: displayedColumns" class="hover:bg-surface-raised transition-colors"></tr>
        </table>
      </div>
    }
  `,
  styles: [`
    :host { display: block; }
    ::ng-deep .mat-mdc-table { background: transparent !important; }
    ::ng-deep .mat-mdc-header-row, ::ng-deep .mat-mdc-row { background: transparent !important; }
    ::ng-deep .mat-mdc-cell, ::ng-deep .mat-mdc-header-cell { border-bottom: none !important; }
  `],
})
export class ProjectsListComponent implements OnInit {
  /** Pass an engagement ID to filter projects by engagement. */
  engagementId = input<string | undefined>(undefined);

  private engagementService = inject(EngagementService);

  loading = signal(true);
  error = signal<string | null>(null);
  projects = signal<ProjectSummary[]>([]);

  displayedColumns = ['name', 'currency', 'budget', 'status'];

  ngOnInit(): void {
    this.loadProjects();
  }

  private loadProjects(): void {
    this.loading.set(true);
    this.error.set(null);
    const id = this.engagementId();
    this.engagementService.getProjects(id ? { engagement_id: id } : undefined).subscribe({
      next: (res) => {
        this.projects.set(res);
        this.loading.set(false);
      },
      error: (err: unknown) => {
        // #113: per-status-code copy.
        this.error.set(userMessageForError(err, 'Projects'));
        this.loading.set(false);
      },
    });
  }

  statusClass(status: string): string {
    switch (status) {
      case 'active':    return 'bg-accent/15 text-accent-light';
      case 'planning':  return 'bg-indigo-950 text-indigo-400';
      case 'completed': return 'bg-surface-raised text-text-muted';
      case 'on_hold':   return 'bg-confidence-med/10 text-confidence-med';
      case 'cancelled': return 'bg-confidence-low/10 text-confidence-low';
      default:          return 'bg-surface-raised text-text-muted';
    }
  }
}
