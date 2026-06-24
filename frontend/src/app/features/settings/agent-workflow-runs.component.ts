import { Component, OnInit, inject, signal } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';

interface AgentWorkflowRun {
  id: string;
  tenant_id: string;
  workflow_name: string;
  status: string;
  owner_agent_name: string | null;
  user_id: string | null;
  current_step: string | null;
  goal_snapshot: Record<string, unknown>;
  state_snapshot: Record<string, unknown>;
  trace_id: string | null;
  replay_pointer: string | null;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

interface AgentWorkflowRunListResponse {
  workflow_runs: AgentWorkflowRun[];
  total: number;
}

const WORKFLOW_STATUSES = ['', 'running', 'waiting_on_human', 'succeeded', 'failed', 'cancelled'];

@Component({
  selector: 'app-agent-workflow-runs',
  standalone: true,
  imports: [FormsModule, MatIconModule],
  template: `
    <div class="overflow-hidden rounded-lg border border-border-default bg-surface-raised">
      <div class="flex flex-col gap-4 border-b border-border-default px-6 py-4 lg:flex-row lg:items-center lg:justify-between">
        <div class="flex min-w-0 items-center gap-2">
          <mat-icon class="flex-none text-indigo-400">account_tree</mat-icon>
          <h3 class="text-base font-semibold text-text-primary">Workflow Runs</h3>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <label class="sr-only" for="workflow-name-filter">Workflow</label>
          <input
            id="workflow-name-filter"
            type="text"
            [ngModel]="workflowFilter()"
            (ngModelChange)="workflowFilter.set($event)"
            (keydown.enter)="load()"
            placeholder="Workflow"
            class="h-9 w-56 rounded border border-border-default bg-surface-base px-3 text-sm text-text-primary placeholder:text-text-disabled focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
          />

          <label class="sr-only" for="workflow-status-filter">Status</label>
          <select
            id="workflow-status-filter"
            [ngModel]="statusFilter()"
            (ngModelChange)="statusFilter.set($event); load()"
            class="h-9 rounded border border-border-default bg-surface-base px-3 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
          >
            @for (option of statusOptions; track option) {
              <option [value]="option">{{ option ? statusLabel(option) : 'All statuses' }}</option>
            }
          </select>

          <button
            type="button"
            (click)="load()"
            class="inline-flex h-9 items-center gap-1.5 rounded border border-border-default px-3 text-sm font-medium text-text-secondary transition-colors hover:border-accent/60 hover:text-text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            <mat-icon style="font-size:1rem;width:1rem;height:1rem;" aria-hidden="true">refresh</mat-icon>
            Refresh
          </button>
        </div>
      </div>

      @if (loading()) {
        <div class="divide-y divide-border-default animate-pulse" aria-busy="true" aria-label="Loading workflow runs">
          @for (i of [1, 2, 3]; track i) {
            <div class="grid grid-cols-[1fr_8rem_12rem_10rem] gap-4 px-6 py-4">
              <div class="h-4 rounded bg-surface"></div>
              <div class="h-4 rounded bg-surface"></div>
              <div class="h-4 rounded bg-surface"></div>
              <div class="h-4 rounded bg-surface"></div>
            </div>
          }
        </div>
      }

      @if (loadError() && !loading()) {
        <div class="flex items-center gap-2 px-6 py-5 text-sm text-confidence-low" role="alert">
          <mat-icon class="flex-none text-base">error_outline</mat-icon>
          Failed to load workflow runs.
          <button type="button" class="ml-1 underline hover:no-underline" (click)="load()">Retry</button>
        </div>
      }

      @if (!loading() && !loadError() && workflows().length === 0) {
        <div class="px-6 py-8 text-center">
          <mat-icon class="mb-2 block text-3xl text-text-disabled">account_tree</mat-icon>
          <p class="text-sm text-text-muted">No workflow runs found.</p>
        </div>
      }

      @if (!loading() && !loadError() && workflows().length > 0) {
        <div class="overflow-x-auto">
          <table class="w-full text-sm" aria-label="Agent workflow runs">
            <thead>
              <tr class="border-b border-border-default bg-surface-base/50 text-xs uppercase tracking-wide text-text-muted">
                <th scope="col" class="min-w-[240px] px-6 py-3 text-left">Workflow</th>
                <th scope="col" class="w-36 px-4 py-3 text-left">Status</th>
                <th scope="col" class="min-w-[180px] px-4 py-3 text-left">Step</th>
                <th scope="col" class="w-44 px-4 py-3 text-left">Owner</th>
                <th scope="col" class="w-40 px-4 py-3 text-left">Started</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border-default">
              @for (workflow of workflows(); track workflow.id) {
                <tr
                  class="cursor-pointer transition-colors hover:bg-surface-base/40"
                  [class.bg-surface-base]="selectedWorkflowId() === workflow.id"
                  (click)="selectWorkflow(workflow.id)"
                  tabindex="0"
                  (keydown.enter)="selectWorkflow(workflow.id)"
                >
                  <td class="px-6 py-4">
                    <div class="font-medium text-text-primary">{{ workflowName(workflow.workflow_name) }}</div>
                    <div class="mt-1 flex flex-wrap items-center gap-2 text-xs text-text-disabled">
                      <span class="font-mono">{{ shortId(workflow.id) }}</span>
                      @if (workflow.trace_id) {
                        <span>trace {{ shortHash(workflow.trace_id) }}</span>
                      }
                    </div>
                  </td>
                  <td class="px-4 py-4">
                    <span class="inline-flex rounded-full px-2.5 py-1 text-xs font-semibold" [class]="statusClass(workflow.status)">
                      {{ statusLabel(workflow.status) }}
                    </span>
                  </td>
                  <td class="px-4 py-4 text-text-secondary">{{ workflow.current_step || '-' }}</td>
                  <td class="px-4 py-4 text-text-secondary">{{ workflow.owner_agent_name || '-' }}</td>
                  <td class="px-4 py-4 text-xs text-text-muted">{{ formatDate(workflow.started_at) }}</td>
                </tr>
                @if (selectedWorkflowId() === workflow.id) {
                  <tr class="bg-surface-base/60">
                    <td colspan="5" class="px-6 py-4">
                      <div class="grid gap-4 text-xs lg:grid-cols-2">
                        <div>
                          <div class="mb-2 font-semibold uppercase tracking-wide text-text-disabled">Goal</div>
                          <pre class="max-h-52 overflow-auto rounded border border-border-default bg-surface-raised p-3 text-text-secondary">{{ formatJson(workflow.goal_snapshot) }}</pre>
                        </div>
                        <div>
                          <div class="mb-2 font-semibold uppercase tracking-wide text-text-disabled">State</div>
                          <pre class="max-h-52 overflow-auto rounded border border-border-default bg-surface-raised p-3 text-text-secondary">{{ formatJson(workflow.state_snapshot) }}</pre>
                        </div>
                      </div>
                      <div class="mt-3 grid gap-3 text-xs sm:grid-cols-3">
                        <div>
                          <div class="uppercase tracking-wide text-text-disabled">Replay</div>
                          <div class="mt-1 font-mono text-text-secondary">{{ workflow.replay_pointer || '-' }}</div>
                        </div>
                        <div>
                          <div class="uppercase tracking-wide text-text-disabled">Completed</div>
                          <div class="mt-1 text-text-secondary">{{ workflow.completed_at ? formatDate(workflow.completed_at) : '-' }}</div>
                        </div>
                        <div>
                          <div class="uppercase tracking-wide text-text-disabled">Updated</div>
                          <div class="mt-1 text-text-secondary">{{ formatDate(workflow.updated_at) }}</div>
                        </div>
                      </div>
                      @if (workflow.error_message) {
                        <div class="mt-3 text-sm text-confidence-low">{{ workflow.error_message }}</div>
                      }
                    </td>
                  </tr>
                }
              }
            </tbody>
          </table>
        </div>
      }
    </div>
  `,
  styles: [':host { display: block; }'],
})
export class AgentWorkflowRunsComponent implements OnInit {
  private http = inject(HttpClient);

  readonly statusOptions = WORKFLOW_STATUSES;
  loading = signal(true);
  loadError = signal(false);
  workflows = signal<AgentWorkflowRun[]>([]);
  workflowFilter = signal('');
  statusFilter = signal('');
  selectedWorkflowId = signal<string | null>(null);

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.loadError.set(false);
    let params = new HttpParams().set('limit', '25');
    const workflow = this.workflowFilter().trim();
    const status = this.statusFilter();
    if (workflow) params = params.set('workflow_name', workflow);
    if (status) params = params.set('status', status);

    this.http.get<AgentWorkflowRunListResponse>('/api/v1/agents/workflow-runs', { params }).subscribe({
      next: (res) => {
        this.workflows.set(res.workflow_runs ?? []);
        this.loading.set(false);
        const selected = this.selectedWorkflowId();
        if (selected && !this.workflows().some(run => run.id === selected)) {
          this.selectedWorkflowId.set(null);
        }
      },
      error: () => {
        this.loading.set(false);
        this.loadError.set(true);
      },
    });
  }

  selectWorkflow(workflowId: string): void {
    this.selectedWorkflowId.set(this.selectedWorkflowId() === workflowId ? null : workflowId);
  }

  workflowName(value: string): string {
    return value
      .split('_')
      .filter(Boolean)
      .map(part => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' ');
  }

  statusLabel(status: string): string {
    return this.workflowName(status);
  }

  statusClass(status: string): string {
    if (status === 'succeeded') return 'bg-emerald-500/15 text-emerald-300';
    if (status === 'failed') return 'bg-confidence-low/15 text-confidence-low';
    if (status === 'running') return 'bg-blue-500/15 text-blue-300';
    if (status === 'waiting_on_human') return 'bg-amber-500/15 text-amber-300';
    if (status === 'cancelled') return 'bg-slate-500/15 text-slate-300';
    return 'bg-surface text-text-muted';
  }

  shortId(value: string): string {
    return value.length > 8 ? value.slice(0, 8) : value;
  }

  shortHash(value: string | null): string {
    if (!value) return '-';
    return value.length > 12 ? value.slice(0, 12) : value;
  }

  formatDate(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat(undefined, {
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  }

  formatJson(value: Record<string, unknown>): string {
    return JSON.stringify(value ?? {}, null, 2);
  }
}
