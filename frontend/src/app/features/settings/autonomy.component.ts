/**
 * AutonomyComponent — Agent Autonomy Settings UI.
 *
 * Issue #209: displays per-agent autonomy level, approval rate, eligibility
 * for promotion, and action buttons to promote/demote/disable agents.
 *
 * Fetches: GET /api/v1/agents/autonomy-status
 * Actions: POST /api/v1/agents/{agent_name}/set-level  { level: number }
 *
 * API contract (backend/app/models/agents.py):
 *   - current_level: 1=notify, 2=suggest (HITL), 3=auto-apply
 *   - sample_count_30d: count of decided suggestions in last 30 days
 *   - avg_confidence_30d: average confidence (0-1), null if no samples
 *   - approval_rate_30d: fraction approved (0-1), null if < 10 samples
 *   - set-level accepts 1-3 (not 0), returns { agent_name, level }
 *   - On set-level success we reload the full list (response lacks full status shape)
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

// ── API types aligned to backend/app/models/agents.py ────────────────────────

interface AgentAutonomyStatus {
  agent_name: string;
  display_name: string;
  description: string;
  current_level: 1 | 2 | 3;
  is_locked: boolean;
  is_enabled: boolean;
  failure_count: number;
  failure_threshold: number;
  circuit_open_until: string | null;
  circuit_open_reason: string | null;
  is_circuit_open: boolean;
  is_eligible_for_promotion: boolean;
  approval_rate_30d: number | null;   // fraction 0-1, null if < 10 samples
  sample_count_30d: number;           // count of decided suggestions (30d)
  avg_confidence_30d: number | null;  // average confidence (0-1), null if no samples
}

interface AgentAutonomyStatusResponse {
  agents: AgentAutonomyStatus[];
}

// ── Level badge helper (per spec) ─────────────────────────────────────────────

interface LevelBadge {
  label: string;
  classes: string;
}

function levelBadge(level: number, locked: boolean): LevelBadge {
  if (locked) return { label: 'L3 🔒', classes: 'bg-slate-500/20 text-slate-300' };
  const map: Record<number, LevelBadge> = {
    3: { label: 'L3 ▲', classes: 'bg-green-500/20 text-green-300' },
    2: { label: 'L2 ●', classes: 'bg-blue-500/20 text-blue-300' },
    1: { label: 'L1 ◐', classes: 'bg-yellow-500/20 text-yellow-300' },
  };
  return map[level] ?? { label: `L${level}`, classes: 'bg-slate-600/20 text-slate-400' };
}

@Component({
  selector: 'app-autonomy',
  standalone: true,
  imports: [MatIconModule, MatTooltipModule],
  template: `
    <div class="bg-surface-raised border border-border-default rounded-lg overflow-hidden">

      <!-- Header -->
      <div class="flex items-center gap-3 px-6 py-4 border-b border-border-default">
        <mat-icon class="text-indigo-400">psychology</mat-icon>
        <div>
          <h3 class="text-base font-semibold text-text-primary">Agent Autonomy</h3>
          <p class="text-xs text-text-muted mt-0.5">
            Control how independently each AI agent operates.
            L1 = notify only, L2 = suggest (HITL, default), L3 = act automatically.
          </p>
        </div>
      </div>

      <!-- Loading skeleton: 6 rows -->
      @if (loading()) {
        <div class="divide-y divide-border-default animate-pulse" aria-busy="true" aria-label="Loading agent autonomy status">
          @for (i of [1, 2, 3, 4, 5, 6]; track i) {
            <div class="flex items-center gap-4 px-6 py-4">
              <div class="h-4 bg-surface rounded w-44"></div>
              <div class="h-6 bg-surface rounded w-16 ml-4"></div>
              <div class="h-4 bg-surface rounded w-28 ml-4"></div>
              <div class="h-4 bg-surface rounded w-16 ml-4"></div>
              <div class="h-7 bg-surface rounded w-32 ml-auto"></div>
            </div>
          }
        </div>
      }

      <!-- Error state -->
      @if (loadError() && !loading()) {
        <div class="px-6 py-6 text-sm text-confidence-low flex items-center gap-2" role="alert">
          <mat-icon class="text-base flex-none">error_outline</mat-icon>
          Failed to load autonomy status.
          <button
            type="button"
            class="underline hover:no-underline ml-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
            (click)="load()"
          >Retry</button>
        </div>
      }

      <!-- Empty state -->
      @if (!loading() && !loadError() && agents().length === 0) {
        <div class="px-6 py-10 text-center">
          <mat-icon class="text-3xl text-text-disabled mb-2 block">psychology_alt</mat-icon>
          <p class="text-sm text-text-muted">No agents configured yet.</p>
        </div>
      }

      <!-- Agent table -->
      @if (!loading() && !loadError() && agents().length > 0) {
        <div class="overflow-x-auto">
          <table class="w-full text-sm" aria-label="Agent autonomy levels">
            <thead>
              <tr class="text-text-muted text-xs uppercase tracking-wide border-b border-border-default bg-surface-base/50">
                <th scope="col" class="text-left px-6 py-3 min-w-[180px]">Agent</th>
                <th scope="col" class="text-left px-6 py-3 w-28">Level</th>
                <th scope="col" class="text-left px-6 py-3 w-56">30-Day Stats</th>
                <th scope="col" class="text-left px-6 py-3 w-28">Status</th>
                <th scope="col" class="text-right px-6 py-3 min-w-[180px]">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border-default">
              @for (agent of agents(); track agent.agent_name) {
                <tr class="hover:bg-surface-base/40 transition-colors">

                  <!-- Agent name + tooltip description -->
                  <td class="px-6 py-4">
                    <div
                      class="flex items-center gap-1.5 text-text-primary font-medium"
                      [matTooltip]="agent.description"
                      matTooltipPosition="right"
                    >
                      {{ agent.display_name }}
                      <mat-icon
                        class="text-text-disabled"
                        style="font-size:0.875rem;width:0.875rem;height:0.875rem;"
                        aria-hidden="true"
                      >info_outline</mat-icon>
                    </div>
                    @if (agent.avg_confidence_30d !== null) {
                      <p class="text-xs text-text-disabled mt-0.5 tabular-nums">
                        Avg confidence: {{ (agent.avg_confidence_30d * 100).toFixed(0) }}%
                      </p>
                    }
                  </td>

                  <!-- Level badge -->
                  <td class="px-6 py-4">
                    @let badge = levelBadge(agent.current_level, agent.is_locked);
                    <span
                      class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold"
                      [class]="badge.classes"
                      [attr.aria-label]="'Level ' + agent.current_level + (agent.is_locked ? ' — locked' : '')"
                    >
                      {{ badge.label }}
                    </span>
                  </td>

                  <!-- 30-day stats: approval rate + sample count -->
                  <td class="px-6 py-4 tabular-nums">
                    @if (agent.is_locked) {
                      <span class="text-text-muted text-xs italic">Always on</span>
                    } @else if (agent.approval_rate_30d === null || agent.sample_count_30d < 5) {
                      <span class="text-text-disabled text-xs">— (&lt; 5 samples)</span>
                    } @else {
                      <span [class]="approvalRateClass(agent.approval_rate_30d)">
                        {{ (agent.approval_rate_30d * 100).toFixed(0) }}%
                      </span>
                      <span class="text-text-disabled ml-1 text-xs">
                        ({{ agent.sample_count_30d }} decisions)
                      </span>
                    }
                  </td>

                  <!-- Eligibility status -->
                  <td class="px-6 py-4">
                    @if (!agent.is_enabled) {
                      <span
                        class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-red-500/15 text-red-300"
                        aria-label="Agent paused"
                      >
                        <mat-icon
                          style="font-size:0.875rem;width:0.875rem;height:0.875rem;"
                          aria-hidden="true"
                        >pause_circle</mat-icon>
                        Paused
                      </span>
                    } @else if (agent.is_circuit_open) {
                      <span
                        class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-300"
                        [matTooltip]="agent.circuit_open_reason || 'Circuit is cooling down after repeated failures'"
                        aria-label="Circuit open"
                      >
                        <mat-icon
                          style="font-size:0.875rem;width:0.875rem;height:0.875rem;"
                          aria-hidden="true"
                        >error</mat-icon>
                        Circuit open
                      </span>
                    } @else if (!agent.is_locked && agent.is_eligible_for_promotion) {
                      <span
                        class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300"
                        aria-label="Ready for promotion to L3"
                      >
                        <mat-icon
                          style="font-size:0.875rem;width:0.875rem;height:0.875rem;"
                          aria-hidden="true"
                        >star</mat-icon>
                        Eligible
                      </span>
                    } @else if (agent.failure_count > 0) {
                      <span class="text-xs text-text-muted tabular-nums">
                        Failures {{ agent.failure_count }}/{{ agent.failure_threshold }}
                      </span>
                    }
                  </td>

                  <!-- Action buttons -->
                  <td class="px-6 py-4 text-right">
                    @if (agent.is_locked) {
                      <span class="text-text-disabled text-xs italic">Locked — always L3</span>
                    } @else {
                      <div class="flex items-center justify-end gap-2 flex-wrap">

                        @if (agent.is_enabled) {
                          <button
                            type="button"
                            [disabled]="actionAgent() === agent.agent_name"
                            (click)="setAgentEnabled(agent, false)"
                            class="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium text-text-muted hover:text-red-300 border border-border-default hover:border-red-500/40 transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-400"
                            [attr.aria-label]="'Pause ' + agent.display_name"
                            matTooltip="Pause immediately blocks this agent before any tool can run"
                          >
                            <mat-icon style="font-size:0.875rem;width:0.875rem;height:0.875rem;" aria-hidden="true">pause_circle</mat-icon>
                            Pause
                          </button>
                        } @else {
                          <button
                            type="button"
                            [disabled]="actionAgent() === agent.agent_name"
                            (click)="setAgentEnabled(agent, true)"
                            class="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium bg-emerald-900/50 text-emerald-300 hover:bg-emerald-800/60 border border-emerald-700/40 transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
                            [attr.aria-label]="'Resume ' + agent.display_name"
                            matTooltip="Resume this agent and close any open default circuit"
                          >
                            <mat-icon style="font-size:0.875rem;width:0.875rem;height:0.875rem;" aria-hidden="true">play_circle</mat-icon>
                            Resume
                          </button>
                        }

                        <!-- Promote L1→L2 -->
                        @if (agent.current_level === 1) {
                          <button
                            type="button"
                            [disabled]="actionAgent() === agent.agent_name"
                            (click)="setLevel(agent, 2)"
                            class="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium bg-blue-900/50 text-blue-300 hover:bg-blue-800/60 border border-blue-700/40 transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-400"
                            [attr.aria-label]="'Promote ' + agent.display_name + ' to L2 (suggest)'"
                            matTooltip="Promote to L2 — agent suggests actions for human approval"
                          >
                            <mat-icon style="font-size:0.875rem;width:0.875rem;height:0.875rem;" aria-hidden="true">arrow_upward</mat-icon>
                            L2
                          </button>
                        }

                        <!-- Promote L2→L3 -->
                        @if (agent.current_level === 2) {
                          <button
                            type="button"
                            [disabled]="actionAgent() === agent.agent_name"
                            (click)="setLevel(agent, 3)"
                            class="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium bg-emerald-900/50 text-emerald-300 hover:bg-emerald-800/60 border border-emerald-700/40 transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
                            [attr.aria-label]="'Promote ' + agent.display_name + ' to L3 (auto)'"
                            matTooltip="Promote to L3 — agent acts automatically without HITL"
                          >
                            <mat-icon style="font-size:0.875rem;width:0.875rem;height:0.875rem;" aria-hidden="true">arrow_upward</mat-icon>
                            L3
                          </button>
                        }

                        <!-- Demote L3→L2 -->
                        @if (agent.current_level === 3) {
                          <button
                            type="button"
                            [disabled]="actionAgent() === agent.agent_name"
                            (click)="setLevel(agent, 2)"
                            class="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium bg-indigo-900/50 text-indigo-300 hover:bg-indigo-800/60 border border-indigo-700/40 transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-400"
                            [attr.aria-label]="'Demote ' + agent.display_name + ' to L2 (suggest)'"
                            matTooltip="Revert to L2 — agent suggests but waits for approval"
                          >
                            <mat-icon style="font-size:0.875rem;width:0.875rem;height:0.875rem;" aria-hidden="true">arrow_downward</mat-icon>
                            L2
                          </button>
                        }

                        <!-- Disable → L1 (lowest allowed by API) — requires confirmation -->
                        @if (agent.current_level > 1) {
                          <button
                            type="button"
                            [disabled]="actionAgent() === agent.agent_name"
                            (click)="confirmDisable(agent)"
                            class="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium text-text-muted hover:text-confidence-low border border-border-default hover:border-confidence-low/40 transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-confidence-low"
                            [attr.aria-label]="'Set ' + agent.display_name + ' to L1 (notify only)'"
                            matTooltip="Set to L1 — agent notifies only, no suggestions"
                          >
                            <mat-icon style="font-size:0.875rem;width:0.875rem;height:0.875rem;" aria-hidden="true">block</mat-icon>
                            Disable
                          </button>
                        }

                        <!-- Loading indicator -->
                        @if (actionAgent() === agent.agent_name) {
                          <span class="text-xs text-text-disabled italic">Saving…</span>
                        }
                      </div>
                    }
                  </td>

                </tr>
              }
            </tbody>
          </table>
        </div>
      }

      <!-- Action error banner -->
      @if (actionError()) {
        <div
          class="mx-6 mb-4 mt-2 rounded-lg border border-confidence-low/30 bg-confidence-low/10 px-4 py-3 text-sm text-confidence-low flex items-center gap-2"
          role="alert"
        >
          <mat-icon class="text-base flex-none">error_outline</mat-icon>
          {{ actionError() }}
        </div>
      }

      <!-- Success toast -->
      @if (successMessage()) {
        <div
          class="mx-6 mb-4 mt-2 rounded-lg border border-emerald-800 bg-accent/10 px-4 py-3 text-sm text-accent-light flex items-center gap-2"
          role="status"
          aria-live="polite"
        >
          <mat-icon class="text-base flex-none">check_circle</mat-icon>
          {{ successMessage() }}
        </div>
      }

      <!-- Info footer -->
      <div class="px-6 py-3 border-t border-border-default bg-surface-base/30">
        <p class="text-xs text-text-disabled">
          Autonomy changes take effect immediately.
          Pause is a hard kill switch and blocks tool execution before HITL or role checks.
          Auto-promotion to L3 requires admin approval and sustained performance above threshold.
          The Accounting Guardian runs at L3 always and cannot be disabled.
        </p>
      </div>

    </div>

    <!-- Disable confirmation dialog (inline) -->
    @if (pendingDisableAgent()) {
      <div
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
        role="dialog"
        aria-modal="true"
        [attr.aria-labelledby]="'disable-dialog-title'"
      >
        <div class="bg-surface-raised border border-border-default rounded-xl shadow-2xl w-full max-w-sm mx-4 p-6">
          <div class="flex items-start gap-3 mb-4">
            <mat-icon class="text-confidence-low flex-none mt-0.5">warning</mat-icon>
            <div>
              <h4 id="disable-dialog-title" class="text-base font-semibold text-text-primary">
                Disable {{ pendingDisableAgent()!.display_name }}?
              </h4>
              <p class="text-sm text-text-muted mt-1">
                This will set the agent to L1 (notify only). It will no longer suggest or
                act on its own. You can re-enable it at any time.
              </p>
            </div>
          </div>
          <div class="flex items-center justify-end gap-3">
            <button
              type="button"
              (click)="cancelDisable()"
              class="px-4 py-2 text-sm text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
            >
              Cancel
            </button>
            <button
              type="button"
              (click)="confirmDisableExecute()"
              class="px-4 py-2 text-sm font-medium text-white bg-red-700 hover:bg-red-600 rounded transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-400"
            >
              Disable
            </button>
          </div>
        </div>
      </div>
    }
  `,
  styles: [':host { display: block; }'],
})
export class AutonomyComponent implements OnInit {
  private http = inject(HttpClient);

  loading          = signal(true);
  loadError        = signal(false);
  agents           = signal<AgentAutonomyStatus[]>([]);
  actionAgent      = signal<string | null>(null);    // agent_name currently being updated
  actionError      = signal<string | null>(null);
  successMessage   = signal<string | null>(null);
  pendingDisableAgent = signal<AgentAutonomyStatus | null>(null);

  // Expose the pure function to the template
  readonly levelBadge = levelBadge;

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.loadError.set(false);
    this.http.get<AgentAutonomyStatusResponse>('/api/v1/agents/autonomy-status').subscribe({
      next: (res) => {
        this.agents.set(res.agents ?? []);
        this.loading.set(false);
      },
      error: () => {
        this.loadError.set(true);
        this.loading.set(false);
      },
    });
  }

  // ── Disable confirmation flow ──────────────────────────────────────────────

  confirmDisable(agent: AgentAutonomyStatus): void {
    this.pendingDisableAgent.set(agent);
  }

  cancelDisable(): void {
    this.pendingDisableAgent.set(null);
  }

  confirmDisableExecute(): void {
    const agent = this.pendingDisableAgent();
    if (!agent) return;
    this.pendingDisableAgent.set(null);
    // API minimum is 1; L1 = notify-only (effectively "disabled" for suggestions)
    this.setLevel(agent, 1);
  }

  // ── Level change ──────────────────────────────────────────────────────────

  setLevel(agent: AgentAutonomyStatus, newLevel: 1 | 2 | 3): void {
    if (agent.is_locked) return;
    this.actionAgent.set(agent.agent_name);
    this.actionError.set(null);
    this.successMessage.set(null);

    this.http
      .post<{ agent_name: string; level: number }>(
        `/api/v1/agents/${agent.agent_name}/set-level`,
        { level: newLevel },
      )
      .subscribe({
        next: () => {
          // Response shape is { agent_name, level } — not a full status object.
          // Reload the full list to pick up recalculated metrics.
          this.actionAgent.set(null);
          const action = newLevel === 1 ? 'set to notify-only (L1)' : `set to L${newLevel}`;
          this.successMessage.set(`${agent.display_name} ${action}.`);
          setTimeout(() => this.successMessage.set(null), 5000);
          this.load();
        },
        error: (err: { error?: { detail?: string } }) => {
          this.actionAgent.set(null);
          const detail = err?.error?.detail;
          this.actionError.set(
            typeof detail === 'string'
              ? detail
              : `Could not update ${agent.display_name}. Please try again.`,
          );
          setTimeout(() => this.actionError.set(null), 6000);
        },
      });
  }

  setAgentEnabled(agent: AgentAutonomyStatus, isEnabled: boolean): void {
    if (agent.is_locked && !isEnabled) return;
    this.actionAgent.set(agent.agent_name);
    this.actionError.set(null);
    this.successMessage.set(null);

    this.http
      .post(
        `/api/v1/agents/${agent.agent_name}/control`,
        { is_enabled: isEnabled, reset_circuit: isEnabled },
      )
      .subscribe({
        next: () => {
          this.actionAgent.set(null);
          this.successMessage.set(
            `${agent.display_name} ${isEnabled ? 'resumed' : 'paused'}.`,
          );
          setTimeout(() => this.successMessage.set(null), 5000);
          this.load();
        },
        error: (err: { error?: { detail?: string } }) => {
          this.actionAgent.set(null);
          const detail = err?.error?.detail;
          this.actionError.set(
            typeof detail === 'string'
              ? detail
              : `Could not update ${agent.display_name}. Please try again.`,
          );
          setTimeout(() => this.actionError.set(null), 6000);
        },
      });
  }

  // ── Display helpers ───────────────────────────────────────────────────────

  approvalRateClass(rate: number): string {
    if (rate >= 0.95) return 'text-accent-light font-medium';
    if (rate >= 0.80) return 'text-confidence-med font-medium';
    return 'text-confidence-low font-medium';
  }
}
