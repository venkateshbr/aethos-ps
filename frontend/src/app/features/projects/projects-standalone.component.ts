import { Component, inject, signal, OnInit, computed } from '@angular/core';
import { TitleCasePipe } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Router } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';

import { EngagementService, ProjectSummary, EngagementSummary } from '../../core/services/engagement.service';
import { userMessageForError } from '../../core/utils/error-message';

type ProjectStatus = 'all' | 'active' | 'on_hold' | 'completed' | 'cancelled';

interface ProjectRow extends ProjectSummary {
  engagement_name?: string;
  budget_hours?: number | null;
  hours_logged?: number | null;
}

const STATUS_CHIPS: { value: ProjectStatus; label: string }[] = [
  { value: 'all',       label: 'All' },
  { value: 'active',    label: 'Active' },
  { value: 'on_hold',   label: 'On Hold' },
  { value: 'completed', label: 'Completed' },
  { value: 'cancelled', label: 'Cancelled' },
];

@Component({
  selector: 'app-projects-standalone',
  standalone: true,
  imports: [
    TitleCasePipe,
    FormsModule,
    ReactiveFormsModule,
    MatIconModule,
    MatButtonModule,
    MatTableModule,
    MatTooltipModule,
  ],
  template: `
    <div class="p-6 bg-surface-base min-h-full">

      <!-- Page header -->
      <div class="flex items-center justify-between mb-6">
        <div>
          <h1 class="text-2xl font-bold text-text-primary">Projects</h1>
          <p class="text-sm text-text-muted mt-1">All projects across your firm</p>
        </div>
        <button
          type="button"
          class="inline-flex items-center gap-1.5 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          aria-label="Create new project"
          (click)="openCreateForm()"
        >
          <mat-icon class="text-base leading-none" style="font-size:1rem;width:1rem;height:1rem;">add</mat-icon>
          New Project
        </button>
      </div>

      <!-- Filters row -->
      <div class="flex flex-wrap items-center gap-3 mb-6">
        <!-- Status chips -->
        <div class="flex gap-1" role="group" aria-label="Filter by status">
          @for (chip of statusChips; track chip.value) {
            <button
              type="button"
              (click)="setStatus(chip.value)"
              class="px-3 py-1.5 rounded-full text-xs font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              [class]="statusFilter() === chip.value
                ? 'bg-accent text-accent-on'
                : 'bg-surface-raised text-text-secondary hover:bg-surface hover:text-text-primary'"
              [attr.aria-pressed]="statusFilter() === chip.value"
            >
              {{ chip.label }}
            </button>
          }
        </div>

        <!-- Engagement dropdown filter -->
        <select
          [(ngModel)]="engagementFilter"
          (ngModelChange)="onEngagementChange($event)"
          class="px-3 py-1.5 bg-surface-raised border border-border-default rounded text-sm text-text-secondary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent"
          aria-label="Filter by engagement"
        >
          <option value="">All Engagements</option>
          @for (eng of engagements(); track eng.id) {
            <option [value]="eng.id">{{ eng.name }}</option>
          }
        </select>
      </div>

      <!-- Loading skeleton -->
      @if (loading()) {
        <div class="rounded-lg overflow-hidden border border-border-default animate-pulse" aria-busy="true" aria-label="Loading projects">
          <div class="h-10 bg-surface-raised border-b border-border-default"></div>
          @for (row of [1, 2, 3, 4, 5]; track row) {
            <div class="flex gap-4 px-4 py-3 border-b border-border-subtle last:border-0">
              <div class="h-4 bg-surface-raised rounded w-16"></div>
              <div class="h-4 bg-surface-raised rounded w-1/3"></div>
              <div class="h-4 bg-surface-raised rounded w-1/4"></div>
              <div class="h-4 bg-surface-raised rounded w-16"></div>
              <div class="h-4 bg-surface-raised rounded w-24"></div>
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
      @if (!loading() && !error() && filteredProjects().length === 0) {
        <div class="rounded-lg border border-border-default bg-surface-raised px-6 py-16 text-center">
          <mat-icon class="text-4xl text-text-disabled mb-4 block">folder_open</mat-icon>
          <p class="text-text-secondary text-sm leading-relaxed mb-4">
            @if (statusFilter() === 'all' && !engagementFilter) {
              No projects yet. Create your first project to get started.
            } @else {
              No projects match the current filters.
            }
          </p>
          @if (statusFilter() === 'all' && !engagementFilter) {
            <button
              type="button"
              class="inline-flex items-center gap-1.5 text-sm text-accent-light hover:text-accent transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
              (click)="openCreateForm()"
            >
              <mat-icon class="text-base leading-none">add</mat-icon>
              Create project
            </button>
          }
        </div>
      }

      <!-- Table -->
      @if (!loading() && !error() && filteredProjects().length > 0) {
        <div class="rounded-lg overflow-hidden border border-border-default">
          <table
            mat-table
            [dataSource]="filteredProjects()"
            class="w-full bg-surface-base"
            aria-label="Projects"
          >
            <!-- Code column -->
            <ng-container matColumnDef="code">
              <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3 w-24">
                Code
              </th>
              <td mat-cell *matCellDef="let row" class="text-text-secondary text-sm font-mono px-4 py-3 border-b border-border-subtle">
                {{ row.code || '—' }}
              </td>
            </ng-container>

            <!-- Name column -->
            <ng-container matColumnDef="name">
              <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Project
              </th>
              <td mat-cell *matCellDef="let row" class="text-text-primary text-sm font-medium px-4 py-3 border-b border-border-subtle">
                {{ row.name }}
              </td>
            </ng-container>

            <!-- Engagement column -->
            <ng-container matColumnDef="engagement">
              <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Engagement
              </th>
              <td mat-cell *matCellDef="let row" class="text-text-secondary text-sm px-4 py-3 border-b border-border-subtle">
                {{ engagementNameMap()[row.engagement_id] || '—' }}
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
                  [class]="statusBadgeClass(row.status)"
                  [attr.aria-label]="'Status: ' + row.status"
                >
                  <span class="w-1.5 h-1.5 rounded-full" [class]="statusDotClass(row.status)" aria-hidden="true"></span>
                  {{ row.status === 'on_hold' ? 'On Hold' : (row.status | titlecase) }}
                </span>
              </td>
            </ng-container>

            <!-- Budget Hours column -->
            <ng-container matColumnDef="budget_hours">
              <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3 text-right">
                Budget Hrs
              </th>
              <td mat-cell *matCellDef="let row" class="text-text-secondary text-sm font-mono px-4 py-3 border-b border-border-subtle text-right tabular-nums">
                {{ row.budget_hours != null ? row.budget_hours : '—' }}
              </td>
            </ng-container>

            <!-- Hours Logged column -->
            <ng-container matColumnDef="hours_logged">
              <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3 text-right">
                Logged Hrs
              </th>
              <td mat-cell *matCellDef="let row" class="text-text-secondary text-sm font-mono px-4 py-3 border-b border-border-subtle text-right tabular-nums">
                {{ row.hours_logged != null ? row.hours_logged : '—' }}
              </td>
            </ng-container>

            <!-- % Used column with progress bar -->
            <ng-container matColumnDef="pct_used">
              <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3 w-36">
                % Used
              </th>
              <td mat-cell *matCellDef="let row" class="px-4 py-3 border-b border-border-subtle">
                @if (row.budget_hours != null && row.budget_hours > 0) {
                  @let pct = calcPct(row.hours_logged, row.budget_hours);
                  <div class="flex items-center gap-2">
                    <div class="flex-1 h-1.5 rounded-full bg-surface overflow-hidden" aria-hidden="true">
                      <div
                        class="h-full rounded-full transition-all"
                        [class]="progressBarClass(pct)"
                        [style.width.%]="Math.min(pct, 100)"
                      ></div>
                    </div>
                    <span class="text-xs font-mono tabular-nums text-text-muted w-10 text-right" [attr.aria-label]="pct.toFixed(0) + '% of budget hours used'">
                      {{ pct.toFixed(0) }}%
                    </span>
                  </div>
                } @else {
                  <span class="text-text-disabled text-xs">—</span>
                }
              </td>
            </ng-container>

            <!-- Team column -->
            <ng-container matColumnDef="team">
              <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3 text-right">
                Team
              </th>
              <td mat-cell *matCellDef="let row" class="px-4 py-3 border-b border-border-subtle text-right">
                <button
                  type="button"
                  class="inline-flex items-center gap-1 text-xs text-accent-light hover:text-accent transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded px-1.5 py-1"
                  [attr.aria-label]="'Manage team for ' + row.name"
                  (click)="openTeam(row, $event)"
                >
                  <mat-icon class="text-sm leading-none" style="font-size:1rem;width:1rem;height:1rem;">group</mat-icon>
                  Manage
                </button>
              </td>
            </ng-container>

            <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
            <tr
              mat-row
              *matRowDef="let row; columns: displayedColumns"
              class="hover:bg-surface-raised transition-colors cursor-pointer"
              (click)="openEngagement(row.engagement_id)"
              [attr.aria-label]="'Open engagement for project ' + row.name"
              [matTooltip]="'Open engagement'"
            ></tr>
          </table>
        </div>

        <p class="text-xs text-text-disabled mt-3">
          {{ filteredProjects().length }} project{{ filteredProjects().length !== 1 ? 's' : '' }}
        </p>
      }
    </div>

    <!-- Create project slide-in panel -->
    @if (showCreateForm()) {
      <!-- Backdrop -->
      <div
        class="fixed inset-0 bg-black/50 z-40"
        (click)="closeCreateForm()"
        aria-hidden="true"
      ></div>
      <!-- Panel -->
      <aside
        class="fixed right-0 top-0 h-full w-full max-w-md bg-surface border-l border-border-default z-50 flex flex-col shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-project-title"
      >
        <div class="flex items-center justify-between px-6 py-4 border-b border-border-default flex-none">
          <h2 id="create-project-title" class="text-base font-semibold text-text-primary">New Project</h2>
          <button
            type="button"
            (click)="closeCreateForm()"
            class="text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
            aria-label="Close panel"
          >
            <mat-icon>close</mat-icon>
          </button>
        </div>

        <form
          [formGroup]="createForm"
          (ngSubmit)="submitCreate()"
          class="flex-1 overflow-y-auto px-6 py-5 space-y-5"
          novalidate
        >
          <!-- Name -->
          <div>
            <label for="proj-name" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Name *</label>
            <input
              id="proj-name"
              type="text"
              formControlName="name"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
              placeholder="e.g. Phase 1 Discovery"
            />
            @if (createForm.controls.name.touched && createForm.controls.name.errors) {
              <p class="text-xs text-confidence-low mt-1">Name is required.</p>
            }
          </div>

          <!-- Engagement -->
          <div>
            <label for="proj-engagement" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Engagement *</label>
            <select
              id="proj-engagement"
              formControlName="engagement_id"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
            >
              <option value="">Select engagement…</option>
              @for (eng of engagements(); track eng.id) {
                <option [value]="eng.id">{{ eng.name }}</option>
              }
            </select>
            @if (createForm.controls.engagement_id.touched && createForm.controls.engagement_id.errors) {
              <p class="text-xs text-confidence-low mt-1">Engagement is required.</p>
            }
          </div>

          <!-- Status -->
          <div>
            <label for="ps-status" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Status</label>
            <select
              id="ps-status"
              formControlName="status"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
            >
              <option value="active">Active</option>
              <option value="on_hold">On Hold</option>
              <option value="completed">Completed</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>

          @if (createError()) {
            <div role="alert" class="text-sm text-confidence-low bg-confidence-low/10 border border-confidence-low/30 rounded px-3 py-2">
              {{ createError() }}
            </div>
          }
        </form>

        <div class="flex-none px-6 py-4 border-t border-border-default flex items-center justify-end gap-3">
          <button
            type="button"
            class="px-4 py-2 text-sm text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
            (click)="closeCreateForm()"
          >
            Cancel
          </button>
          <button
            type="button"
            class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            [disabled]="createForm.invalid || creating()"
            (click)="submitCreate()"
          >
            @if (creating()) { Creating… } @else { Create Project }
          </button>
        </div>
      </aside>
    }

    <!-- Team / assignments slide-in panel -->
    @if (showTeam()) {
      <div class="fixed inset-0 bg-black/50 z-40" (click)="closeTeam()" aria-hidden="true"></div>
      <aside
        class="fixed right-0 top-0 h-full w-full max-w-md bg-surface border-l border-border-default z-50 flex flex-col shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="team-title"
      >
        <div class="flex items-center justify-between px-6 py-4 border-b border-border-default flex-none">
          <div>
            <h2 id="team-title" class="text-base font-semibold text-text-primary">Project team</h2>
            <p class="text-xs text-text-muted mt-0.5">{{ teamProject()?.code }} · {{ teamProject()?.name }}</p>
          </div>
          <button
            type="button"
            class="text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
            (click)="closeTeam()"
            aria-label="Close panel"
          >
            <mat-icon>close</mat-icon>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto px-6 py-5 space-y-5">
          @if (teamLoading()) {
            <div class="flex items-center justify-center py-8">
              <div class="w-5 h-5 rounded-full border-2 border-accent border-t-transparent animate-spin" aria-label="Loading team"></div>
            </div>
          } @else {
            @if (assignments().length === 0) {
              <p class="text-sm text-text-muted">No one is assigned yet. Add a team member below.</p>
            } @else {
              <div class="space-y-2">
                @for (a of assignments(); track a.id) {
                  <div class="flex items-center gap-3 bg-surface-base border border-border-default rounded-lg px-3 py-2">
                    <div class="flex-1 min-w-0">
                      <p class="text-sm font-medium text-text-primary truncate">{{ a.employee_name || a.employee_email || a.employee_id }}</p>
                      <p class="text-xs text-text-muted mt-0.5">
                        {{ a.role || 'Team member' }}@if (a.override_rate) { · rate {{ a.override_rate }}/h }
                      </p>
                    </div>
                    <button
                      type="button"
                      class="text-text-muted hover:text-confidence-low transition-colors rounded p-1"
                      aria-label="Remove from project"
                      (click)="removeAssignment(a)"
                    >
                      <mat-icon class="text-base leading-none">close</mat-icon>
                    </button>
                  </div>
                }
              </div>
            }
          }

          <form [formGroup]="assignForm" class="border-t border-border-default pt-5 space-y-3" novalidate>
            <p class="text-xs uppercase tracking-wide text-text-muted">Assign someone</p>
            <select
              formControlName="employee_id"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary text-sm focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent"
            >
              <option value="">Select employee…</option>
              @for (e of teamEmployees(); track e.id) {
                <option [value]="e.id">{{ e.first_name }} {{ e.last_name }}</option>
              }
            </select>
            <div class="grid grid-cols-2 gap-3">
              <input
                type="text"
                formControlName="role"
                placeholder="Role (e.g. Lead)"
                class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary text-sm focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent"
              />
              <input
                type="number"
                min="0"
                step="0.01"
                formControlName="override_rate"
                placeholder="Override rate/h"
                class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary text-sm focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent"
              />
            </div>
            @if (teamError()) {
              <div role="alert" class="text-sm text-confidence-low bg-confidence-low/10 border border-confidence-low/30 rounded px-3 py-2">{{ teamError() }}</div>
            }
            <button
              type="button"
              class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              [disabled]="assignForm.controls.employee_id.invalid || addingAssignment()"
              (click)="addAssignment()"
            >
              <mat-icon class="text-base leading-none">person_add</mat-icon>
              @if (addingAssignment()) { Adding… } @else { Add to project }
            </button>
          </form>
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
export class ProjectsStandaloneComponent implements OnInit {
  private engagementService = inject(EngagementService);
  private http = inject(HttpClient);
  private router = inject(Router);
  private fb = inject(FormBuilder);

  // Expose Math for template
  readonly Math = Math;

  loading = signal(true);
  error = signal<string | null>(null);
  projects = signal<ProjectRow[]>([]);
  engagements = signal<EngagementSummary[]>([]);

  // Filters
  statusFilter = signal<ProjectStatus>('all');
  engagementFilter = '';

  readonly statusChips = STATUS_CHIPS;
  readonly displayedColumns = ['code', 'name', 'engagement', 'status', 'budget_hours', 'hours_logged', 'pct_used', 'team'];

  // Computed engagement name lookup map
  engagementNameMap = computed<Record<string, string>>(() => {
    const map: Record<string, string> = {};
    for (const eng of this.engagements()) {
      map[eng.id] = eng.name;
    }
    return map;
  });

  // Filtered projects derived from all projects + active filters
  filteredProjects = computed<ProjectRow[]>(() => {
    let list = this.projects();
    const status = this.statusFilter();
    if (status !== 'all') {
      list = list.filter(p => p.status === status);
    }
    return list;
  });

  // Create form state
  showCreateForm = signal(false);
  creating = signal(false);
  createError = signal<string | null>(null);

  createForm = this.fb.nonNullable.group({
    name:          ['', [Validators.required]],
    engagement_id: ['', [Validators.required]],
    status:        ['active'],
  });

  // Team / assignments panel state
  showTeam = signal(false);
  teamProject = signal<ProjectRow | null>(null);
  teamLoading = signal(false);
  assignments = signal<Assignment[]>([]);
  teamEmployees = signal<EmployeeOption[]>([]);
  addingAssignment = signal(false);
  teamError = signal<string | null>(null);
  assignForm = this.fb.nonNullable.group({
    employee_id: ['', [Validators.required]],
    role: [''],
    override_rate: [null as number | null],
  });

  ngOnInit(): void {
    this.loadEngagements();
    this.loadProjects();
  }

  private loadEngagements(): void {
    this.engagementService.getEngagements().subscribe({
      next: (list) => this.engagements.set(list),
      error: () => this.engagements.set([]),
    });
  }

  loadProjects(): void {
    this.loading.set(true);
    this.error.set(null);

    let params = new HttpParams();
    if (this.engagementFilter) {
      params = params.set('engagement_id', this.engagementFilter);
    }

    this.http.get<ProjectRow[]>('/api/v1/projects', { params }).subscribe({
      next: (res) => {
        this.projects.set(res);
        this.loading.set(false);
      },
      error: (err: unknown) => {
        this.error.set(userMessageForError(err, 'Projects'));
        this.loading.set(false);
      },
    });
  }

  setStatus(status: ProjectStatus): void {
    this.statusFilter.set(status);
  }

  onEngagementChange(_engId: string): void {
    this.loadProjects();
  }

  openEngagement(engagementId: string): void {
    this.router.navigate(['/app/engagements', engagementId]);
  }

  calcPct(logged: number | null | undefined, budget: number | null | undefined): number {
    if (budget == null || budget === 0 || logged == null) return 0;
    return (logged / budget) * 100;
  }

  progressBarClass(pct: number): string {
    if (pct > 90) return 'bg-red-500';
    if (pct >= 80) return 'bg-amber-400';
    return 'bg-emerald-400';
  }

  statusBadgeClass(status: string): string {
    switch (status) {
      case 'active':    return 'bg-accent/15 text-accent-light';
      case 'on_hold':   return 'bg-amber-500/15 text-amber-300';
      case 'completed': return 'bg-surface-raised text-text-muted';
      case 'cancelled': return 'bg-confidence-low/10 text-confidence-low';
      default:          return 'bg-surface-raised text-text-muted';
    }
  }

  statusDotClass(status: string): string {
    switch (status) {
      case 'active':    return 'bg-emerald-400';
      case 'on_hold':   return 'bg-amber-400';
      case 'completed': return 'bg-slate-400';
      case 'cancelled': return 'bg-red-400';
      default:          return 'bg-slate-400';
    }
  }

  openCreateForm(): void {
    this.createForm.reset({ name: '', engagement_id: '', status: 'active' });
    this.createError.set(null);
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
    this.http.post<ProjectRow>('/api/v1/projects', {
      name:          v.name,
      engagement_id: v.engagement_id,
      status:        v.status,
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

  openTeam(project: ProjectRow, event?: Event): void {
    event?.stopPropagation();
    this.teamProject.set(project);
    this.teamError.set(null);
    this.assignForm.reset({ employee_id: '', role: '', override_rate: null });
    this.showTeam.set(true);
    this.teamLoading.set(true);
    this.http.get<{ items: Assignment[] }>(`/api/v1/projects/${project.id}/assignments`).subscribe({
      next: (res) => {
        this.assignments.set(res.items ?? []);
        this.teamLoading.set(false);
      },
      error: () => {
        this.teamError.set('Could not load the project team.');
        this.teamLoading.set(false);
      },
    });
    this.http.get<{ items: EmployeeOption[] }>('/api/v1/employees').subscribe({
      next: (res) => this.teamEmployees.set(res.items ?? []),
      error: () => this.teamEmployees.set([]),
    });
  }

  closeTeam(): void {
    this.showTeam.set(false);
  }

  addAssignment(): void {
    const project = this.teamProject();
    if (!project || this.assignForm.controls.employee_id.invalid) {
      this.assignForm.markAllAsTouched();
      return;
    }
    this.addingAssignment.set(true);
    this.teamError.set(null);
    const v = this.assignForm.getRawValue();
    this.http.post<Assignment>(`/api/v1/projects/${project.id}/assignments`, {
      employee_id: v.employee_id,
      role: v.role || null,
      override_rate: v.override_rate != null ? String(v.override_rate) : null,
    }).subscribe({
      next: (created) => {
        this.assignments.update((list) => [...list, created]);
        this.assignForm.reset({ employee_id: '', role: '', override_rate: null });
        this.addingAssignment.set(false);
      },
      error: (err: { error?: { detail?: string } }) => {
        this.addingAssignment.set(false);
        const detail = err?.error?.detail;
        this.teamError.set(typeof detail === 'string' ? detail : 'Could not add team member.');
      },
    });
  }

  removeAssignment(a: Assignment): void {
    const project = this.teamProject();
    if (!project) return;
    this.http.delete<void>(`/api/v1/projects/${project.id}/assignments/${a.id}`).subscribe({
      next: () => this.assignments.update((list) => list.filter((x) => x.id !== a.id)),
      error: () => this.teamError.set('Could not remove team member.'),
    });
  }
}

interface Assignment {
  id: string;
  project_id: string;
  employee_id: string;
  role?: string | null;
  override_rate?: string | null;
  employee_name?: string | null;
  employee_email?: string | null;
}

interface EmployeeOption {
  id: string;
  first_name: string;
  last_name: string;
}
