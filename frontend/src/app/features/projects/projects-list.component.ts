import { Component, inject, input, signal, OnInit } from '@angular/core';
import { TitleCasePipe } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';

import { EngagementService, ProjectSummary, EngagementSummary } from '../../core/services/engagement.service';
import { MoneyPipe } from '../../shared/pipes/money.pipe';
import { userMessageForError } from '../../core/utils/error-message';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-projects-list',
  standalone: true,
  imports: [
    TitleCasePipe,
    ReactiveFormsModule,
    MatTableModule,
    MatIconModule,
    MatButtonModule,
    MoneyPipe,
  ],
  template: `
    <!-- New project button (only shown when not embedded in engagement detail) -->
    <div class="flex justify-end mb-3">
      <button
        type="button"
        class="inline-flex items-center gap-1.5 bg-accent hover:bg-accent-hover text-accent-on font-medium px-3 py-1.5 rounded text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        aria-label="Create new project"
        (click)="openCreateForm()"
      >
        <mat-icon class="text-base leading-none">add</mat-icon>
        New project
      </button>
    </div>

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

    <!-- Create project slide-in panel -->
    @if (showCreateForm()) {
      <div class="fixed inset-0 bg-black/50 z-40" (click)="closeCreateForm()" aria-hidden="true"></div>
      <aside
        class="fixed right-0 top-0 h-full w-full max-w-md bg-surface border-l border-border-default z-50 flex flex-col shadow-2xl"
        role="dialog" aria-modal="true" aria-labelledby="create-project-title"
      >
        <div class="flex items-center justify-between px-6 py-4 border-b border-border-default flex-none">
          <h2 id="create-project-title" class="text-base font-semibold text-text-primary">New project</h2>
          <button class="text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded" (click)="closeCreateForm()" aria-label="Close panel">
            <mat-icon>close</mat-icon>
          </button>
        </div>
        <form [formGroup]="createForm" (ngSubmit)="submitCreate()" class="flex-1 overflow-y-auto px-6 py-5 space-y-5" novalidate>
          <!-- Name -->
          <div>
            <label for="proj-name" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Name *</label>
            <input id="proj-name" type="text" formControlName="name"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
              placeholder="e.g. Phase 1 Discovery" />
            @if (createForm.controls.name.touched && createForm.controls.name.errors) {
              <p class="text-xs text-confidence-low mt-1">Name is required.</p>
            }
          </div>
          <!-- Engagement -->
          <div>
            <label for="proj-engagement" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Engagement *</label>
            <select id="proj-engagement" formControlName="engagement_id"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm">
              <option value="">Select engagement…</option>
              @for (eng of availableEngagements(); track eng.id) {
                <option [value]="eng.id">{{ eng.name }}</option>
              }
            </select>
            @if (createForm.controls.engagement_id.touched && createForm.controls.engagement_id.errors) {
              <p class="text-xs text-confidence-low mt-1">Engagement is required.</p>
            }
          </div>
          @if (createError()) {
            <div role="alert" class="text-sm text-confidence-low bg-confidence-low/10 border border-confidence-low/30 rounded px-3 py-2">{{ createError() }}</div>
          }
        </form>
        <div class="flex-none px-6 py-4 border-t border-border-default flex items-center justify-end gap-3">
          <button type="button" class="px-4 py-2 text-sm text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded" (click)="closeCreateForm()">Cancel</button>
          <button type="button" class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            [disabled]="createForm.invalid || creating()" (click)="submitCreate()">
            @if (creating()) { Creating… } @else { Create project }
          </button>
        </div>
      </aside>
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
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);

  loading = signal(true);
  error = signal<string | null>(null);
  projects = signal<ProjectSummary[]>([]);

  // Create form state
  showCreateForm = signal(false);
  creating = signal(false);
  createError = signal<string | null>(null);
  availableEngagements = signal<EngagementSummary[]>([]);
  createForm = this.fb.nonNullable.group({
    name:          ['', [Validators.required]],
    engagement_id: ['', [Validators.required]],
  });

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
      case 'planning':  return 'bg-surface-raised text-text-muted';
      case 'completed': return 'bg-surface-raised text-text-muted';
      case 'on_hold':   return 'bg-confidence-med/10 text-confidence-med';
      case 'cancelled': return 'bg-confidence-low/10 text-confidence-low';
      default:          return 'bg-surface-raised text-text-muted';
    }
  }

  openCreateForm(): void {
    // Pre-fill engagement_id if one is active
    const preselected = this.engagementId() ?? '';
    this.createForm.reset({ name: '', engagement_id: preselected });
    this.createError.set(null);
    // Load engagements for dropdown
    this.engagementService.getEngagements().subscribe({
      next: (list) => this.availableEngagements.set(list),
      error: () => this.availableEngagements.set([]),
    });
    this.showCreateForm.set(true);
  }

  closeCreateForm(): void {
    this.showCreateForm.set(false);
  }

  submitCreate(): void {
    if (this.createForm.invalid) {
      this.createForm.markAllAsTouched();
      return;
    }
    this.creating.set(true);
    this.createError.set(null);
    const v = this.createForm.getRawValue();
    this.http.post<ProjectSummary>('/api/v1/projects', {
      name:          v.name,
      engagement_id: v.engagement_id,
    }).subscribe({
      next: (newProj) => {
        this.projects.update(list => [newProj, ...list]);
        this.creating.set(false);
        this.closeCreateForm();
      },
      error: (err: { error?: { detail?: string } }) => {
        this.creating.set(false);
        const detail = err?.error?.detail;
        this.createError.set(
          typeof detail === 'string' ? detail : 'Could not create project. Please try again.'
        );
      },
    });
  }
}
