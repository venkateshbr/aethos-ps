import { Component, OnInit, inject, input, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';

interface FinancialEvent {
  id: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  source_type?: string | null;
  source_id?: string | null;
  actor_user_id?: string | null;
  actor_role?: string | null;
  action: string;
  before_state: Record<string, unknown>;
  after_state: Record<string, unknown>;
  metadata: Record<string, unknown>;
  event_hash: string;
  created_at: string;
}

@Component({
  selector: 'app-decision-timeline',
  standalone: true,
  imports: [],
  template: `
    @if (loading()) {
      <section class="mb-6 rounded-lg border border-border-default bg-surface-raised p-4" aria-busy="true">
        <div class="h-4 w-32 rounded bg-surface mb-3"></div>
        <div class="space-y-2">
          <div class="h-3 rounded bg-surface"></div>
          <div class="h-3 w-2/3 rounded bg-surface"></div>
        </div>
      </section>
    } @else if (events().length) {
      <section class="mb-6 rounded-lg border border-border-default bg-surface-raised p-4" [attr.aria-label]="title()">
        <div class="mb-3 flex items-center justify-between gap-3">
          <div>
            <h2 class="text-sm font-semibold text-text-primary">{{ title() }}</h2>
            <p class="mt-0.5 text-xs text-text-muted">Immutable approval and review events for this record.</p>
          </div>
          <span class="rounded bg-surface px-2 py-0.5 text-xs text-text-secondary">{{ events().length }} event(s)</span>
        </div>
        <div class="space-y-2">
          @for (event of events(); track event.id) {
            <article class="rounded border border-border-subtle bg-surface px-3 py-2">
              <div class="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <div class="flex flex-wrap items-center gap-2">
                    <span class="text-sm font-medium text-text-primary">{{ actionLabel(event.action) }}</span>
                    @if (event.actor_role) {
                      <span class="rounded bg-surface-raised px-2 py-0.5 text-[11px] uppercase tracking-wide text-text-muted">
                        {{ event.actor_role }}
                      </span>
                    }
                  </div>
                  <p class="mt-1 text-xs text-text-muted">
                    {{ event.created_at }}
                    @if (event.actor_user_id) { <span> - {{ event.actor_user_id }}</span> }
                  </p>
                </div>
                @if (relatedTaskLabel(event)) {
                  <span class="font-mono text-[11px] text-text-disabled">{{ relatedTaskLabel(event) }}</span>
                }
              </div>
              @if (taskTitle(event)) {
                <p class="mt-2 text-xs text-text-secondary">{{ taskTitle(event) }}</p>
              }
              @if (changeSummary(event).length) {
                <div class="mt-2 flex flex-wrap gap-1.5">
                  @for (summary of changeSummary(event); track summary) {
                    <span class="rounded bg-surface-raised px-2 py-1 text-xs text-text-secondary">{{ summary }}</span>
                  }
                </div>
              }
              <p class="mt-2 font-mono text-[11px] text-text-disabled">hash {{ shortHash(event.event_hash) }}</p>
            </article>
          }
        </div>
      </section>
    } @else if (error()) {
      <p class="mb-6 text-xs text-confidence-low" role="alert">{{ error() }}</p>
    }
  `,
  styles: [':host { display: block; width: 100%; }'],
})
export class DecisionTimelineComponent implements OnInit {
  entityType = input.required<string>();
  entityId = input.required<string>();
  title = input<string>('Decision timeline');

  protected loading = signal(false);
  protected error = signal<string | null>(null);
  protected events = signal<FinancialEvent[]>([]);

  private http = inject(HttpClient);

  ngOnInit(): void {
    this.load();
  }

  private load(): void {
    const entityType = this.entityType();
    const entityId = this.entityId();
    if (!entityType || !entityId) return;
    this.loading.set(true);
    this.error.set(null);
    this.http
      .get<{ items: FinancialEvent[] }>(
        `/api/v1/financial-events/business-records/${encodeURIComponent(entityType)}/${encodeURIComponent(entityId)}/decisions`,
      )
      .subscribe({
        next: (res) => {
          this.events.set(res.items ?? []);
          this.loading.set(false);
        },
        error: () => {
          this.error.set('Could not load decision timeline.');
          this.loading.set(false);
        },
      });
  }

  protected actionLabel(action: string): string {
    return action
      .replace(/_/g, ' ')
      .replace(/\b\w/g, char => char.toUpperCase());
  }

  protected relatedTaskLabel(event: FinancialEvent): string {
    const taskId = event.metadata?.['source_hitl_task_id'] || (
      event.source_type === 'hitl_task' ? event.source_id : null
    );
    return taskId ? `Inbox ${taskId}` : '';
  }

  protected taskTitle(event: FinancialEvent): string {
    const beforeTask = this.objectValue(event.before_state, 'task');
    const afterTask = this.objectValue(event.after_state, 'task');
    const task = Object.keys(afterTask).length ? afterTask : beforeTask;
    const title = task['title'];
    const kind = task['kind'];
    return [title, kind ? `(${kind})` : '']
      .filter(value => value != null && String(value).trim())
      .join(' ');
  }

  protected changeSummary(event: FinancialEvent): string[] {
    const summaries: string[] = [];
    const beforeHash = this.stringValue(event.before_state, 'payload_hash');
    const afterHash = this.stringValue(event.after_state, 'payload_hash');
    if (beforeHash && afterHash && beforeHash !== afterHash) {
      summaries.push(`payload changed ${this.shortHash(beforeHash)} -> ${this.shortHash(afterHash)}`);
    }

    const beforePayload = this.objectValue(event.before_state, 'payload');
    const afterPayload = this.objectValue(event.after_state, 'payload');
    const changedFields = new Set([...Object.keys(beforePayload), ...Object.keys(afterPayload)]);
    for (const key of changedFields) {
      if (summaries.length >= 5) break;
      const beforeValue = beforePayload[key];
      const afterValue = afterPayload[key];
      if (!this.isSimple(beforeValue) || !this.isSimple(afterValue)) continue;
      if (String(beforeValue ?? '') === String(afterValue ?? '')) continue;
      summaries.push(`${key.replace(/_/g, ' ')} reviewed`);
    }

    const materialisation = this.objectValue(event.after_state, 'materialisation');
    if (materialisation['entity_type'] && materialisation['entity_id']) {
      summaries.push(`${materialisation['entity_type']} ${materialisation['entity_id']}`);
    }
    return summaries;
  }

  protected shortHash(value: string): string {
    return value.length > 12 ? value.slice(0, 12) : value;
  }

  private objectValue(source: Record<string, unknown>, key: string): Record<string, unknown> {
    const value = source[key];
    return typeof value === 'object' && value !== null && !Array.isArray(value)
      ? value as Record<string, unknown>
      : {};
  }

  private stringValue(source: Record<string, unknown>, key: string): string {
    const value = source[key];
    return value == null ? '' : String(value);
  }

  private isSimple(value: unknown): boolean {
    return value == null || ['string', 'number', 'boolean'].includes(typeof value);
  }
}
