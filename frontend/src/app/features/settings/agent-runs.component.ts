import { Component, OnInit, inject, signal } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';

interface AgentRunSummary {
  id: string;
  agent_name: string;
  trigger_type: string;
  status: string;
  user_id: string | null;
  prompt_version: string | null;
  model_version: string | null;
  trace_id: string | null;
  replay_pointer: string | null;
  input_hash: string | null;
  output_hash: string | null;
  source_document_hash: string | null;
  usage_input_tokens: number | null;
  usage_output_tokens: number | null;
  cost_usd: string | null;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
  created_at: string;
  tool_count: number;
  failed_tool_count: number;
}

interface AgentRunListResponse {
  runs: AgentRunSummary[];
  total: number;
}

interface AgentToolInvocation {
  id: string;
  tool_name: string;
  risk_class: string;
  status: string;
  external_tool_call_id: string | null;
  input_hash: string | null;
  output_hash: string | null;
  input_snapshot: Record<string, unknown>;
  output_snapshot: Record<string, unknown>;
  duration_ms: number | null;
  error_message: string | null;
  created_at: string;
}

interface AgentRunDetail extends AgentRunSummary {
  tool_invocations: AgentToolInvocation[];
}

interface AgentReplayStep {
  index: number;
  tool_invocation_id: string;
  tool_name: string;
  risk_class: string;
  status: string;
  input_hash: string | null;
  output_hash: string | null;
  input_snapshot: Record<string, unknown>;
  output_snapshot: Record<string, unknown>;
  error_message: string | null;
  created_at: string;
}

interface AgentReplayPreview {
  run_id: string;
  agent_name: string;
  status: string;
  replay_mode: string;
  can_reexecute: boolean;
  trace_id: string | null;
  replay_pointer: string | null;
  input_hash: string | null;
  output_hash: string | null;
  prompt_version: string | null;
  model_version: string | null;
  manifest_hash: string;
  steps: AgentReplayStep[];
}

interface AgentReplayReexecutionPlan {
  action_type: string;
  approval_role: string;
  external_side_effect: boolean;
  idempotency_key: string;
  operator_action: string;
}

interface AgentReplayValidationStep {
  index: number;
  tool_invocation_id: string;
  tool_name: string;
  recorded_risk_class: string;
  current_risk_class: string;
  recorded_status: string;
  replay_status: string;
  reason: string;
  input_hash: string | null;
  recorded_output_hash: string | null;
  current_output_hash: string | null;
  input_hash_matches: boolean | null;
  output_hash_matches: boolean | null;
  duration_ms: number | null;
  current_output_snapshot: Record<string, unknown> | null;
  reexecution_plan: AgentReplayReexecutionPlan | null;
  error_message: string | null;
}

interface AgentReplayValidationResult {
  run_id: string;
  agent_name: string;
  validation_mode: string;
  overall_status: string;
  can_reexecute: boolean;
  can_request_human_reexecution: boolean;
  manifest_hash: string;
  reexecuted_step_count: number;
  planned_step_count: number;
  blocked_step_count: number;
  drift_step_count: number;
  failed_step_count: number;
  steps: AgentReplayValidationStep[];
}

const STATUS_OPTIONS = ['', 'running', 'succeeded', 'failed', 'cancelled'];

@Component({
  selector: 'app-agent-runs',
  standalone: true,
  imports: [FormsModule, MatIconModule],
  template: `
    <div class="bg-surface-raised border border-border-default rounded-lg overflow-hidden">
      <div class="flex flex-col gap-4 px-6 py-4 border-b border-border-default lg:flex-row lg:items-center lg:justify-between">
        <div class="flex items-center gap-2 min-w-0">
          <mat-icon class="text-indigo-400 flex-none">monitoring</mat-icon>
          <h3 class="text-base font-semibold text-text-primary">Agent Runs</h3>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <label class="sr-only" for="agent-run-agent-filter">Agent</label>
          <input
            id="agent-run-agent-filter"
            type="text"
            [ngModel]="agentFilter()"
            (ngModelChange)="agentFilter.set($event)"
            (keydown.enter)="load()"
            placeholder="Agent"
            class="h-9 w-44 rounded border border-border-default bg-surface-base px-3 text-sm text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent"
          />

          <label class="sr-only" for="agent-run-status-filter">Status</label>
          <select
            id="agent-run-status-filter"
            [ngModel]="statusFilter()"
            (ngModelChange)="statusFilter.set($event); load()"
            class="h-9 rounded border border-border-default bg-surface-base px-3 text-sm text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent"
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
        <div class="divide-y divide-border-default animate-pulse" aria-busy="true" aria-label="Loading agent runs">
          @for (i of [1, 2, 3, 4]; track i) {
            <div class="grid grid-cols-[1fr_7rem_7rem_7rem] gap-4 px-6 py-4">
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
          <mat-icon class="text-base flex-none">error_outline</mat-icon>
          Failed to load agent runs.
          <button type="button" class="ml-1 underline hover:no-underline" (click)="load()">Retry</button>
        </div>
      }

      @if (!loading() && !loadError() && runs().length === 0) {
        <div class="px-6 py-10 text-center">
          <mat-icon class="mb-2 block text-3xl text-text-disabled">monitoring</mat-icon>
          <p class="text-sm text-text-muted">No agent runs found.</p>
        </div>
      }

      @if (!loading() && !loadError() && runs().length > 0) {
        <div class="overflow-x-auto">
          <table class="w-full text-sm" aria-label="Agent runs">
            <thead>
              <tr class="border-b border-border-default bg-surface-base/50 text-xs uppercase tracking-wide text-text-muted">
                <th scope="col" class="min-w-[220px] px-6 py-3 text-left">Run</th>
                <th scope="col" class="w-32 px-4 py-3 text-left">Status</th>
                <th scope="col" class="w-28 px-4 py-3 text-left">Tools</th>
                <th scope="col" class="w-36 px-4 py-3 text-left">Model</th>
                <th scope="col" class="w-40 px-4 py-3 text-left">Started</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border-default">
              @for (run of runs(); track run.id) {
                <tr
                  class="cursor-pointer transition-colors hover:bg-surface-base/40"
                  [class.bg-surface-base]="selectedRunId() === run.id"
                  (click)="selectRun(run.id)"
                  tabindex="0"
                  (keydown.enter)="selectRun(run.id)"
                >
                  <td class="px-6 py-4">
                    <div class="font-medium text-text-primary">{{ displayAgent(run.agent_name) }}</div>
                    <div class="mt-1 flex flex-wrap items-center gap-2 text-xs text-text-disabled">
                      <span class="font-mono">{{ shortId(run.id) }}</span>
                      <span>{{ run.trigger_type }}</span>
                      @if (run.trace_id) {
                        <span>trace {{ shortHash(run.trace_id) }}</span>
                      }
                    </div>
                  </td>
                  <td class="px-4 py-4">
                    <span class="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold" [class]="statusClass(run.status)">
                      {{ statusLabel(run.status) }}
                    </span>
                  </td>
                  <td class="px-4 py-4 tabular-nums">
                    <span class="text-text-secondary">{{ run.tool_count }}</span>
                    @if (run.failed_tool_count > 0) {
                      <span class="ml-1 text-confidence-low">({{ run.failed_tool_count }} failed)</span>
                    }
                  </td>
                  <td class="max-w-[13rem] truncate px-4 py-4 text-xs text-text-muted" [title]="run.model_version || ''">
                    {{ run.model_version || '-' }}
                  </td>
                  <td class="px-4 py-4 text-xs text-text-muted">{{ formatDate(run.started_at) }}</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }

      @if (selectedRunId()) {
        <div class="border-t border-border-default bg-surface-base/30">
          @if (detailLoading()) {
            <div class="flex items-center gap-2 px-6 py-4 text-sm text-text-muted">
              <mat-icon class="animate-spin" style="font-size:1rem;width:1rem;height:1rem;">progress_activity</mat-icon>
              Loading run detail...
            </div>
          } @else if (detailError()) {
            <div class="flex items-center gap-2 px-6 py-4 text-sm text-confidence-low" role="alert">
              <mat-icon class="text-base">error_outline</mat-icon>
              Failed to load run detail.
            </div>
          } @else if (selectedRun()) {
            <div class="space-y-4 px-6 py-5">
              <div class="grid gap-3 text-xs sm:grid-cols-2 lg:grid-cols-4">
                <div>
                  <div class="uppercase tracking-wide text-text-disabled">Prompt</div>
                  <div class="mt-1 font-mono text-text-secondary">{{ selectedRun()!.prompt_version || '-' }}</div>
                </div>
                <div>
                  <div class="uppercase tracking-wide text-text-disabled">Input Hash</div>
                  <div class="mt-1 font-mono text-text-secondary">{{ shortHash(selectedRun()!.input_hash) }}</div>
                </div>
                <div>
                  <div class="uppercase tracking-wide text-text-disabled">Output Hash</div>
                  <div class="mt-1 font-mono text-text-secondary">{{ shortHash(selectedRun()!.output_hash) }}</div>
                </div>
                <div>
                  <div class="uppercase tracking-wide text-text-disabled">Replay</div>
                  <div class="mt-1 truncate font-mono text-text-secondary" [title]="selectedRun()!.replay_pointer || ''">
                    {{ selectedRun()!.replay_pointer || '-' }}
                  </div>
                </div>
              </div>

              @if (selectedRun()!.error_message) {
                <div class="rounded border border-confidence-low/30 bg-confidence-low/10 px-3 py-2 text-sm text-confidence-low">
                  {{ selectedRun()!.error_message }}
                </div>
              }

              <div class="rounded border border-border-default bg-surface-raised px-4 py-3">
                <div class="flex flex-wrap items-center justify-between gap-3">
                  <div class="min-w-0">
                    <div class="text-xs uppercase tracking-wide text-text-disabled">Replay Manifest</div>
                    <div class="mt-1 truncate font-mono text-xs text-text-secondary">
                      {{ replayPreview()?.manifest_hash ? shortHash(replayPreview()!.manifest_hash) : '-' }}
                    </div>
                  </div>
                  <div class="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      (click)="loadReplay(selectedRun()!.id)"
                      [disabled]="replayLoading()"
                      class="inline-flex h-9 items-center gap-1.5 rounded border border-border-default px-3 text-sm font-medium text-text-secondary transition-colors hover:border-accent/60 hover:text-text-primary disabled:cursor-wait disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                    >
                      <mat-icon style="font-size:1rem;width:1rem;height:1rem;" aria-hidden="true">
                        {{ replayLoading() ? 'progress_activity' : 'replay' }}
                      </mat-icon>
                      Replay
                    </button>
                    <button
                      type="button"
                      (click)="validateReplay(selectedRun()!.id)"
                      [disabled]="validationLoading()"
                      class="inline-flex h-9 items-center gap-1.5 rounded border border-border-default px-3 text-sm font-medium text-text-secondary transition-colors hover:border-accent/60 hover:text-text-primary disabled:cursor-wait disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                    >
                      <mat-icon style="font-size:1rem;width:1rem;height:1rem;" aria-hidden="true">
                        {{ validationLoading() ? 'progress_activity' : 'rule' }}
                      </mat-icon>
                      Validate
                    </button>
                  </div>
                </div>

                @if (replayError()) {
                  <div class="mt-3 flex items-center gap-2 text-sm text-confidence-low" role="alert">
                    <mat-icon class="text-base">error_outline</mat-icon>
                    Replay failed.
                  </div>
                }

                @if (replayPreview()) {
                  <div class="mt-3 grid gap-3 text-xs sm:grid-cols-3">
                    <div>
                      <div class="uppercase tracking-wide text-text-disabled">Mode</div>
                      <div class="mt-1 font-mono text-text-secondary">{{ replayPreview()!.replay_mode }}</div>
                    </div>
                    <div>
                      <div class="uppercase tracking-wide text-text-disabled">Steps</div>
                      <div class="mt-1 font-mono text-text-secondary">{{ replayPreview()!.steps.length }}</div>
                    </div>
                    <div>
                      <div class="uppercase tracking-wide text-text-disabled">Re-execute</div>
                      <div class="mt-1 font-mono text-text-secondary">{{ replayPreview()!.can_reexecute ? 'yes' : 'no' }}</div>
                    </div>
                  </div>
                }

                @if (validationError()) {
                  <div class="mt-3 flex items-center gap-2 text-sm text-confidence-low" role="alert">
                    <mat-icon class="text-base">error_outline</mat-icon>
                    Validation failed.
                  </div>
                }

                @if (validationResult()) {
                  <div class="mt-3 grid gap-3 text-xs sm:grid-cols-5">
                    <div>
                      <div class="uppercase tracking-wide text-text-disabled">Validation</div>
                      <div class="mt-1 font-mono text-text-secondary">{{ statusLabel(validationResult()!.overall_status) }}</div>
                    </div>
                    <div>
                      <div class="uppercase tracking-wide text-text-disabled">Re-executed</div>
                      <div class="mt-1 font-mono text-text-secondary">{{ validationResult()!.reexecuted_step_count }}</div>
                    </div>
                    <div>
                      <div class="uppercase tracking-wide text-text-disabled">Planned</div>
                      <div class="mt-1 font-mono text-text-secondary">{{ validationResult()!.planned_step_count }}</div>
                    </div>
                    <div>
                      <div class="uppercase tracking-wide text-text-disabled">Blocked</div>
                      <div class="mt-1 font-mono text-text-secondary">{{ validationResult()!.blocked_step_count }}</div>
                    </div>
                    <div>
                      <div class="uppercase tracking-wide text-text-disabled">Drift</div>
                      <div class="mt-1 font-mono text-text-secondary">{{ validationResult()!.drift_step_count }}</div>
                    </div>
                  </div>
                  <div class="mt-3 overflow-x-auto rounded border border-border-default">
                    <table class="w-full text-xs" aria-label="Agent replay validation steps">
                      <thead>
                        <tr class="border-b border-border-default bg-surface-base text-text-muted">
                          <th scope="col" class="px-3 py-2 text-left">Tool</th>
                          <th scope="col" class="px-3 py-2 text-left">Status</th>
                          <th scope="col" class="px-3 py-2 text-left">Risk</th>
                          <th scope="col" class="px-3 py-2 text-left">Hashes</th>
                        </tr>
                      </thead>
                      <tbody class="divide-y divide-border-default">
                        @for (step of validationResult()!.steps; track step.tool_invocation_id) {
                          <tr>
                            <td class="px-3 py-2 font-medium text-text-primary">{{ step.tool_name }}</td>
                            <td class="px-3 py-2">
                              <span class="inline-flex rounded-full px-2 py-0.5 font-semibold" [class]="statusClass(step.replay_status)">
                                {{ statusLabel(step.replay_status) }}
                              </span>
                              <div class="mt-1 max-w-sm text-text-muted">{{ step.reason }}</div>
                              @if (step.reexecution_plan) {
                                <div class="mt-1 max-w-sm text-text-secondary">
                                  {{ step.reexecution_plan.approval_role }} approval /
                                  {{ step.reexecution_plan.external_side_effect ? 'external' : 'internal' }} /
                                  {{ step.reexecution_plan.action_type }}
                                </div>
                                <div class="mt-1 font-mono text-text-disabled">
                                  key {{ shortHash(step.reexecution_plan.idempotency_key) }}
                                </div>
                              }
                            </td>
                            <td class="px-3 py-2 text-text-secondary">{{ riskLabel(step.current_risk_class) }}</td>
                            <td class="px-3 py-2 font-mono text-text-disabled">
                              <div>in {{ matchLabel(step.input_hash_matches) }}</div>
                              <div>out {{ matchLabel(step.output_hash_matches) }}</div>
                            </td>
                          </tr>
                        }
                      </tbody>
                    </table>
                  </div>
                }
              </div>

              <div class="overflow-x-auto rounded border border-border-default">
                <table class="w-full text-sm" aria-label="Agent run tool invocations">
                  <thead>
                    <tr class="border-b border-border-default bg-surface-base text-xs uppercase tracking-wide text-text-muted">
                      <th scope="col" class="px-4 py-3 text-left">Tool</th>
                      <th scope="col" class="px-4 py-3 text-left">Risk</th>
                      <th scope="col" class="px-4 py-3 text-left">Status</th>
                      <th scope="col" class="px-4 py-3 text-left">Duration</th>
                      <th scope="col" class="px-4 py-3 text-left">Hashes</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-border-default">
                    @for (tool of selectedRun()!.tool_invocations; track tool.id) {
                      <tr>
                        <td class="px-4 py-3">
                          <div class="font-medium text-text-primary">{{ tool.tool_name }}</div>
                          @if (tool.error_message) {
                            <div class="mt-1 max-w-md text-xs text-confidence-low">{{ tool.error_message }}</div>
                          }
                        </td>
                        <td class="px-4 py-3">
                          <span class="rounded bg-indigo-500/10 px-2 py-0.5 text-xs text-indigo-300">{{ riskLabel(tool.risk_class) }}</span>
                        </td>
                        <td class="px-4 py-3">
                          <span class="inline-flex rounded-full px-2 py-0.5 text-xs font-semibold" [class]="statusClass(tool.status)">
                            {{ statusLabel(tool.status) }}
                          </span>
                        </td>
                        <td class="px-4 py-3 font-mono text-xs text-text-muted">
                          {{ tool.duration_ms === null ? '-' : tool.duration_ms + ' ms' }}
                        </td>
                        <td class="px-4 py-3 font-mono text-xs text-text-disabled">
                          <div>in {{ shortHash(tool.input_hash) }}</div>
                          <div>out {{ shortHash(tool.output_hash) }}</div>
                        </td>
                      </tr>
                    } @empty {
                      <tr>
                        <td colspan="5" class="px-4 py-5 text-center text-sm text-text-muted">No tool calls.</td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            </div>
          }
        </div>
      }
    </div>
  `,
  styles: [':host { display: block; }'],
})
export class AgentRunsComponent implements OnInit {
  private http = inject(HttpClient);

  readonly statusOptions = STATUS_OPTIONS;
  loading = signal(true);
  loadError = signal(false);
  runs = signal<AgentRunSummary[]>([]);
  agentFilter = signal('');
  statusFilter = signal('');
  selectedRunId = signal<string | null>(null);
  selectedRun = signal<AgentRunDetail | null>(null);
  detailLoading = signal(false);
  detailError = signal(false);
  replayLoading = signal(false);
  replayError = signal(false);
  replayPreview = signal<AgentReplayPreview | null>(null);
  validationLoading = signal(false);
  validationError = signal(false);
  validationResult = signal<AgentReplayValidationResult | null>(null);

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.loadError.set(false);
    let params = new HttpParams().set('limit', '25');
    const agent = this.agentFilter().trim();
    const status = this.statusFilter();
    if (agent) params = params.set('agent_name', agent);
    if (status) params = params.set('status', status);

    this.http.get<AgentRunListResponse>('/api/v1/agents/runs', { params }).subscribe({
      next: (res) => {
        this.runs.set(res.runs ?? []);
        this.loading.set(false);
        const selected = this.selectedRunId();
        if (selected && !this.runs().some(run => run.id === selected)) {
          this.selectedRunId.set(null);
          this.selectedRun.set(null);
        }
      },
      error: () => {
        this.loading.set(false);
        this.loadError.set(true);
      },
    });
  }

  selectRun(runId: string): void {
    if (this.selectedRunId() === runId) {
      this.selectedRunId.set(null);
      this.selectedRun.set(null);
      this.replayPreview.set(null);
      this.validationResult.set(null);
      return;
    }
    this.selectedRunId.set(runId);
    this.detailLoading.set(true);
    this.detailError.set(false);
    this.selectedRun.set(null);
    this.replayPreview.set(null);
    this.validationResult.set(null);
    this.replayError.set(false);
    this.validationError.set(false);

    this.http.get<AgentRunDetail>(`/api/v1/agents/runs/${runId}`).subscribe({
      next: (run) => {
        this.selectedRun.set(run);
        this.detailLoading.set(false);
      },
      error: () => {
        this.detailLoading.set(false);
        this.detailError.set(true);
      },
    });
  }

  loadReplay(runId: string): void {
    this.replayLoading.set(true);
    this.replayError.set(false);
    this.http.post<AgentReplayPreview>(`/api/v1/agents/runs/${runId}/replay`, {}).subscribe({
      next: (preview) => {
        this.replayPreview.set(preview);
        this.replayLoading.set(false);
      },
      error: () => {
        this.replayLoading.set(false);
        this.replayError.set(true);
      },
    });
  }

  validateReplay(runId: string): void {
    this.validationLoading.set(true);
    this.validationError.set(false);
    this.http.post<AgentReplayValidationResult>(`/api/v1/agents/runs/${runId}/replay/validate`, {}).subscribe({
      next: (result) => {
        this.validationResult.set(result);
        this.validationLoading.set(false);
      },
      error: () => {
        this.validationLoading.set(false);
        this.validationError.set(true);
      },
    });
  }

  displayAgent(agentName: string): string {
    return agentName
      .split('_')
      .filter(Boolean)
      .map(part => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' ');
  }

  statusLabel(status: string): string {
    return status
      .split('_')
      .filter(Boolean)
      .map(part => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' ');
  }

  riskLabel(risk: string): string {
    return risk.replaceAll('_', ' ');
  }

  statusClass(status: string): string {
    if (status === 'succeeded' || status === 'matched') return 'bg-emerald-500/15 text-emerald-300';
    if (status === 'failed' || status === 'drift_detected') return 'bg-confidence-low/15 text-confidence-low';
    if (status === 'running') return 'bg-blue-500/15 text-blue-300';
    if (status === 'skipped' || status === 'blocked_by_risk' || status === 'unsupported_executor' || status === 'planned_for_human_reexecution') return 'bg-amber-500/15 text-amber-300';
    if (status === 'cancelled') return 'bg-slate-500/15 text-slate-300';
    if (status === 'partially_reexecuted' || status === 'executed_no_baseline' || status === 'planned' || status === 'partially_planned') return 'bg-blue-500/15 text-blue-300';
    return 'bg-surface text-text-muted';
  }

  matchLabel(value: boolean | null): string {
    if (value === true) return 'match';
    if (value === false) return 'diff';
    return '-';
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
}
