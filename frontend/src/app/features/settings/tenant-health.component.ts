import { Component, OnInit, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';

interface TenantHealthTableCheck {
  name: string;
  status: string;
  message?: string;
}

interface TenantHealthRequestFailure {
  method: string;
  path: string;
  status_code: number;
  count: number;
}

interface TenantHealthBackgroundFailure {
  worker_name: string;
  count: number;
}

interface TenantHealthAlert {
  code: string;
  severity: string;
  message: string;
  count: number;
  route_type: string;
  channel: string;
  runbook: string;
  metadata: Record<string, unknown>;
}

interface TenantHealthSummary {
  status: string;
  generated_at: string;
  runtime: {
    environment: string;
    debug: boolean;
    queue_configured: boolean;
    queue_required: boolean;
    extraction_mode: string;
  };
  rate_limit: {
    enabled: boolean;
    backend: string;
    distributed_configured: boolean;
    fallback_to_memory: boolean;
    window_seconds: number;
  };
  checks: {
    tables: TenantHealthTableCheck[];
  };
  telemetry: {
    request_failures: TenantHealthRequestFailure[];
    background_failures: TenantHealthBackgroundFailure[];
    failed_agent_runs_24h: number;
    failed_tool_invocations_24h: number;
    failed_workflow_runs_24h: number;
    failed_tools_by_name_24h: { tool_name: string; count: number }[];
    window_start: string;
  };
  alerts: {
    route: {
      route_type: string;
      channel: string;
      configured: boolean;
    };
    items: TenantHealthAlert[];
  };
}

@Component({
  selector: 'app-tenant-health',
  standalone: true,
  imports: [MatIconModule],
  template: `
    <div class="overflow-hidden rounded-lg border border-border-default bg-surface-raised">
      <div class="flex flex-col gap-3 border-b border-border-default px-6 py-4 md:flex-row md:items-center md:justify-between">
        <div class="flex min-w-0 items-center gap-2">
          <mat-icon class="flex-none text-emerald-400">health_and_safety</mat-icon>
          <div class="min-w-0">
            <h3 class="text-base font-semibold text-text-primary">Operational Health</h3>
            @if (health()) {
              <p class="mt-1 text-xs text-text-muted">Generated {{ formatDate(health()!.generated_at) }}</p>
            }
          </div>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          @if (health()) {
            <span class="inline-flex rounded-full px-2.5 py-1 text-xs font-semibold" [class]="statusClass(health()!.status)">
              {{ statusLabel(health()!.status) }}
            </span>
          }
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
        <div class="space-y-3 px-6 py-5" aria-busy="true" aria-label="Loading tenant health">
          @for (item of [1, 2, 3]; track item) {
            <div class="h-12 rounded bg-surface"></div>
          }
        </div>
      } @else if (error()) {
        <div class="flex items-center gap-2 px-6 py-5 text-sm text-confidence-low" role="alert">
          <mat-icon class="flex-none text-base">error_outline</mat-icon>
          Failed to load tenant health.
        </div>
      } @else if (health()) {
        <div class="space-y-5 px-6 py-5">
          <div class="grid gap-3 md:grid-cols-4">
            <div>
              <div class="text-xs uppercase text-text-disabled">Runtime</div>
              <div class="mt-1 text-sm text-text-primary">{{ health()!.runtime.environment }}</div>
              <div class="mt-1 text-xs text-text-muted">Queue {{ health()!.runtime.queue_configured ? 'configured' : 'not configured' }}</div>
            </div>
            <div>
              <div class="text-xs uppercase text-text-disabled">Rate limit</div>
              <div class="mt-1 text-sm text-text-primary">{{ health()!.rate_limit.backend }}</div>
              <div class="mt-1 text-xs text-text-muted">
                {{ health()!.rate_limit.distributed_configured ? 'Distributed' : 'In-process' }}
                / {{ health()!.rate_limit.fallback_to_memory ? 'fallback on' : 'fallback off' }}
              </div>
            </div>
            <div>
              <div class="text-xs uppercase text-text-disabled">Agent failures</div>
              <div class="mt-1 text-sm text-text-primary">
                {{ totalAgentFailures(health()!) }}
              </div>
              <div class="mt-1 text-xs text-text-muted">Last 24h</div>
            </div>
            <div>
              <div class="text-xs uppercase text-text-disabled">Alert route</div>
              <div class="mt-1 text-sm text-text-primary">{{ routeLabel(health()!.alerts.route.route_type) }}</div>
              <div class="mt-1 text-xs text-text-muted">{{ health()!.alerts.route.channel }}</div>
            </div>
          </div>

          <div class="grid gap-5 xl:grid-cols-2">
            <section>
              <h4 class="mb-2 text-xs font-semibold uppercase text-text-muted">Table Checks</h4>
              <div class="overflow-x-auto rounded border border-border-subtle">
                <table class="w-full text-sm" aria-label="Tenant table checks">
                  <thead>
                    <tr class="border-b border-border-default bg-surface-base text-xs uppercase text-text-muted">
                      <th scope="col" class="px-3 py-2 text-left">Table</th>
                      <th scope="col" class="px-3 py-2 text-left">Status</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-border-default">
                    @for (check of health()!.checks.tables; track check.name) {
                      <tr>
                        <td class="px-3 py-2 text-text-primary">{{ check.name }}</td>
                        <td class="px-3 py-2">
                          <span class="rounded-full px-2 py-0.5 text-xs font-semibold" [class]="statusClass(check.status)">
                            {{ statusLabel(check.status) }}
                          </span>
                          @if (check.message) {
                            <span class="ml-2 text-xs text-text-muted">{{ check.message }}</span>
                          }
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            </section>

            <section>
              <h4 class="mb-2 text-xs font-semibold uppercase text-text-muted">Failure Signals</h4>
              <div class="space-y-3">
                <div class="rounded border border-border-subtle px-3 py-2">
                  <div class="text-xs uppercase text-text-disabled">Request failures</div>
                  @for (failure of health()!.telemetry.request_failures; track failure.method + failure.path + failure.status_code) {
                    <div class="mt-2 flex items-center justify-between gap-3 text-xs">
                      <span class="font-mono text-text-secondary">{{ failure.method }} {{ failure.path }} / {{ failure.status_code }}</span>
                      <span class="text-text-primary">{{ failure.count }}</span>
                    </div>
                  } @empty {
                    <p class="mt-2 text-xs text-text-muted">None</p>
                  }
                </div>
                <div class="rounded border border-border-subtle px-3 py-2">
                  <div class="text-xs uppercase text-text-disabled">Background failures</div>
                  @for (failure of health()!.telemetry.background_failures; track failure.worker_name) {
                    <div class="mt-2 flex items-center justify-between gap-3 text-xs">
                      <span class="font-mono text-text-secondary">{{ failure.worker_name }}</span>
                      <span class="text-text-primary">{{ failure.count }}</span>
                    </div>
                  } @empty {
                    <p class="mt-2 text-xs text-text-muted">None</p>
                  }
                </div>
              </div>
            </section>
          </div>

          <section>
            <h4 class="mb-2 text-xs font-semibold uppercase text-text-muted">Routed Alerts</h4>
            <div class="divide-y divide-border-default rounded border border-border-subtle">
              @for (alert of health()!.alerts.items; track alert.code) {
                <div class="px-3 py-3">
                  <div class="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <div class="text-sm font-medium text-text-primary">{{ alertLabel(alert.code) }}</div>
                      <div class="mt-1 text-xs text-text-muted">{{ alert.message }}</div>
                    </div>
                    <div class="text-right text-xs">
                      <div class="font-semibold text-text-primary">{{ alert.count }}</div>
                      <div class="text-text-muted">{{ routeLabel(alert.route_type) }} / {{ alert.channel }}</div>
                    </div>
                  </div>
                </div>
              } @empty {
                <p class="px-3 py-4 text-sm text-text-muted">No routed alerts.</p>
              }
            </div>
          </section>
        </div>
      }
    </div>
  `,
  styles: [':host { display: block; }'],
})
export class TenantHealthComponent implements OnInit {
  private http = inject(HttpClient);

  health = signal<TenantHealthSummary | null>(null);
  loading = signal(true);
  error = signal(false);

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set(false);
    this.http.get<TenantHealthSummary>('/api/v1/tenants/health').subscribe({
      next: (summary) => {
        this.health.set(summary);
        this.loading.set(false);
      },
      error: () => {
        this.error.set(true);
        this.loading.set(false);
      },
    });
  }

  totalAgentFailures(summary: TenantHealthSummary): number {
    return (
      summary.telemetry.failed_agent_runs_24h
      + summary.telemetry.failed_tool_invocations_24h
      + summary.telemetry.failed_workflow_runs_24h
    );
  }

  statusLabel(status: string): string {
    return status.replace(/_/g, ' ').replace(/\b\w/g, char => char.toUpperCase());
  }

  statusClass(status: string): string {
    if (status === 'ok' || status === 'succeeded') return 'bg-accent/10 text-accent-light';
    if (status === 'degraded' || status === 'warning') return 'bg-confidence-med/10 text-confidence-med';
    if (status === 'error' || status === 'failed') return 'bg-confidence-low/10 text-confidence-low';
    return 'bg-surface text-text-muted';
  }

  routeLabel(routeType: string): string {
    if (routeType === 'webhook') return 'Webhook';
    if (routeType === 'runbook_queue') return 'Runbook queue';
    return this.statusLabel(routeType);
  }

  alertLabel(code: string): string {
    return this.statusLabel(code);
  }

  formatDate(value: string): string {
    return new Intl.DateTimeFormat('en', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(value));
  }
}
