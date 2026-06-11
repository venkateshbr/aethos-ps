import { Component, signal, computed, inject, HostListener, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { HttpErrorResponse } from '@angular/common/http';
import { HitlService, HitlTask } from '../../core/services/hitl.service';
import { ConfidenceChipComponent } from '../../shared/components/confidence-chip.component';
import { SkeletonRowsComponent } from '../../shared/components/skeleton-rows.component';
import { SourceDocumentLinkComponent } from '../../shared/components/source-document-link.component';
import { userMessageForError } from '../../core/utils/error-message';

/** HITL task kinds that originate from an AI document extraction (#127). */
const EXTRACTION_KINDS = new Set(['create_engagement_draft', 'create_expense_draft', 'create_bill_draft']);

interface EditField {
  key: string;
  label: string;
  type: 'text' | 'number' | 'date' | 'select' | 'textarea';
  options?: string[];
}

const CURRENCIES = ['USD', 'GBP', 'SGD', 'INR', 'AUD'];
const BILLING_ARRANGEMENTS = ['time_and_materials', 'fixed_fee', 'retainer', 'retainer_draw', 'milestone', 'capped_tm'];
const EXPENSE_CATEGORIES = ['meals_and_entertainment', 'transport', 'accommodation', 'software', 'other'];

/** Editable fields per task kind, driving the edit drawer form (#146). */
const EDIT_FIELD_SCHEMA: Record<string, EditField[]> = {
  create_engagement_draft: [
    { key: 'client_name', label: 'Client name', type: 'text' },
    { key: 'billing_arrangement', label: 'Billing arrangement', type: 'select', options: BILLING_ARRANGEMENTS },
    { key: 'currency', label: 'Currency', type: 'select', options: CURRENCIES },
    { key: 'total_value', label: 'Total value', type: 'number' },
    { key: 'start_date', label: 'Start date', type: 'date' },
    { key: 'end_date', label: 'End date', type: 'date' },
    { key: 'scope_summary', label: 'Scope summary', type: 'textarea' },
  ],
  create_expense_draft: [
    { key: 'vendor', label: 'Vendor', type: 'text' },
    { key: 'amount', label: 'Amount', type: 'number' },
    { key: 'currency', label: 'Currency', type: 'select', options: CURRENCIES },
    { key: 'category', label: 'Category', type: 'select', options: EXPENSE_CATEGORIES },
    { key: 'expense_date', label: 'Expense date', type: 'date' },
    { key: 'description', label: 'Description', type: 'textarea' },
  ],
  create_bill_draft: [
    { key: 'vendor_name', label: 'Vendor name', type: 'text' },
    { key: 'vendor_invoice_number', label: 'Invoice number', type: 'text' },
    { key: 'currency', label: 'Currency', type: 'select', options: CURRENCIES },
    { key: 'subtotal', label: 'Subtotal', type: 'number' },
    { key: 'tax_total', label: 'Tax total', type: 'number' },
    { key: 'total', label: 'Total', type: 'number' },
    { key: 'issue_date', label: 'Issue date', type: 'date' },
    { key: 'due_date', label: 'Due date', type: 'date' },
  ],
};

@Component({
  selector: 'app-inbox',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, ConfidenceChipComponent, SkeletonRowsComponent, SourceDocumentLinkComponent],
  template: `
    <div class="h-full flex flex-col bg-surface-base text-text-primary outline-none"
         (keydown)="onKeydown($event)"
         tabindex="0">

      <!-- Header -->
      <div class="px-6 py-4 border-b border-border-default flex items-center justify-between flex-none">
        <div class="flex items-center gap-3">
          <h1 class="text-lg font-semibold text-text-primary">Inbox</h1>
          @if (tasks().length > 0) {
            <span class="bg-confidence-med/15 text-confidence-med text-xs font-medium px-2 py-0.5 rounded-full">
              {{ tasks().length }}
            </span>
          }
        </div>

        <!-- Kind filter tabs -->
        <div class="flex gap-1">
          @for (k of kindFilters; track k.value) {
            <button
              (click)="setKindFilter(k.value)"
              class="px-3 py-1.5 text-xs rounded transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              [class]="kindFilter() === k.value
                ? 'bg-surface-raised text-text-primary font-medium'
                : 'text-text-muted hover:text-text-primary hover:bg-surface'"
              [attr.aria-pressed]="kindFilter() === k.value"
            >{{ k.label }}</button>
          }
        </div>
      </div>

      <!-- Keyboard shortcut hint -->
      <div class="px-6 pt-2 pb-0 flex-none">
        <p class="text-xs text-text-muted">
          J&nbsp;/&nbsp;K to navigate &middot; A&nbsp;approve &middot; R&nbsp;reject &middot; E&nbsp;edit
        </p>
      </div>

      <!-- Bulk approve bar -->
      @if (kindFilter() !== 'all' && tasks().length > 1) {
        <div class="mx-6 mt-3 px-4 py-2 bg-surface border border-border-default rounded-lg flex items-center justify-between flex-none">
          <span class="text-sm text-text-secondary">
            {{ tasks().length }} {{ kindFilter().replace('_', ' ') }} items
          </span>
          <button
            (click)="approveAll()"
            class="text-sm text-accent-light hover:text-accent font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
          >
            Approve all {{ tasks().length }}
          </button>
        </div>
      }

      <!-- Task list -->
      <div class="flex-1 overflow-y-auto p-6 space-y-3" role="feed" aria-label="Pending review tasks">

        @if (loading()) {
          <app-skeleton-rows [count]="3" ariaLabel="Loading inbox tasks" />
        } @else if (hasError()) {
          <!-- Error state -->
          <div class="flex flex-col items-center justify-center h-64 text-center" role="alert">
            <mat-icon class="text-confidence-low mb-3" style="font-size:2rem;width:2rem;height:2rem;">error_outline</mat-icon>
            <p class="text-text-secondary font-medium">{{ errorHeadline() }}</p>
            <p class="text-text-muted text-sm mt-1 mb-4">{{ errorDetail() }}</p>
            <button
              (click)="loadTasks()"
              class="px-4 py-2 text-xs font-medium rounded bg-surface-raised hover:bg-surface text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >Retry</button>
          </div>

        } @else if (tasks().length === 0) {
          <!-- Empty state -->
          <div class="flex flex-col items-center justify-center h-64 text-center">
            <mat-icon
              class="text-accent-light mb-3"
              style="font-size:2.5rem;width:2.5rem;height:2.5rem;"
              aria-hidden="true"
            >check_circle</mat-icon>
            <p class="text-text-secondary font-medium">All caught up</p>
            <p class="text-text-muted text-sm mt-1">No pending reviews</p>
          </div>

        } @else {
          @for (task of tasks(); track task.id; let idx = $index) {
            @if (task.kind === 'promote_autonomy' || task.kind === 'autonomy_demotion') {
              <!-- Autonomy promotion / demotion card -->
              <div
                [id]="'task-' + task.id"
                [class]="autonomyCardClass(idx, task.kind)"
                (click)="focusCard(idx)"
                role="article"
                [attr.aria-label]="task.title"
                [attr.aria-current]="idx === focusedIdx() ? 'true' : null"
              >
                <div class="flex items-center gap-2 mb-3">
                  <span [class]="task.kind === 'autonomy_demotion' ? 'text-confidence-low' : 'text-accent-light'" aria-hidden="true">✦</span>
                  <span class="text-xs font-medium uppercase tracking-wide"
                        [class]="task.kind === 'autonomy_demotion' ? 'text-confidence-low' : 'text-accent-light'">
                    {{ task.kind === 'autonomy_demotion' ? 'Autonomy Alert' : 'Autonomy Upgrade' }}
                  </span>
                  <app-confidence-chip [confidence]="task.confidence || '0.9'" />
                </div>
                <p class="text-sm font-semibold text-text-primary mb-1">{{ task.title }}</p>
                <p class="text-xs text-text-muted mb-3">{{ task.agent_name | titlecase }}</p>
                @if (task.suggestion_payload?.['approval_rate']) {
                  <div class="flex flex-wrap gap-2 mb-4">
                    <span class="bg-confidence-high/15 text-confidence-high text-xs px-2 py-0.5 rounded">
                      {{ (+$any(task.suggestion_payload!['approval_rate']) * 100).toFixed(0) }}% approved
                    </span>
                    @if (task.suggestion_payload?.['sample_count']) {
                      <span class="bg-surface-raised text-text-secondary text-xs px-2 py-0.5 rounded">
                        {{ task.suggestion_payload!['sample_count'] }} decisions
                      </span>
                    }
                    @if (task.suggestion_payload?.['avg_confidence']) {
                      <span class="bg-surface-raised text-text-secondary text-xs px-2 py-0.5 rounded">
                        Avg conf: {{ (+$any(task.suggestion_payload!['avg_confidence']) * 100).toFixed(0) }}%
                      </span>
                    }
                  </div>
                }
                @if (task.kind === 'promote_autonomy') {
                  <div class="flex gap-2 flex-wrap">
                    <button
                      (click)="approve(task, $event)"
                      [disabled]="actioning() === task.id"
                      class="px-3 py-1.5 text-xs font-medium rounded bg-accent hover:bg-accent-hover text-accent-on transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                      [attr.aria-label]="'Approve L3 promotion for ' + (task.title)"
                    >
                      @if (actioning() === task.id) { Processing... } @else { Approve L3 }
                    </button>
                    <button
                      (click)="reject(task, $event)"
                      [disabled]="actioning() === task.id"
                      class="px-3 py-1.5 text-xs rounded border border-border-strong text-text-secondary hover:border-border-default transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-border-strong"
                      aria-label="Defer autonomy promotion 7 days"
                    >Defer 7 days</button>
                    <button
                      (click)="reject(task, $event)"
                      [disabled]="actioning() === task.id"
                      class="px-3 py-1.5 text-xs rounded text-confidence-low hover:bg-confidence-low/10 transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-confidence-low"
                      aria-label="Lock agent at L2"
                    >Lock at L2</button>
                  </div>
                } @else {
                  <!-- Demotion alert — just acknowledge -->
                  <div class="flex gap-2">
                    <button
                      (click)="approve(task, $event)"
                      [disabled]="actioning() === task.id"
                      class="px-3 py-1.5 text-xs font-medium rounded bg-confidence-low hover:bg-confidence-low/80 text-text-primary transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-confidence-low"
                    >
                      @if (actioning() === task.id) { Processing... } @else { Acknowledge }
                    </button>
                  </div>
                }
              </div>
            } @else {
              <!-- Regular task card -->
              <div
                [id]="'task-' + task.id"
                [class]="cardClass(idx)"
                (click)="focusCard(idx)"
                role="article"
                [attr.aria-label]="task.title"
                [attr.aria-current]="idx === focusedIdx() ? 'true' : null"
              >
                <!-- Card header -->
                <div class="flex items-start justify-between mb-3">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="text-accent-light text-xs" aria-hidden="true">&#10022;</span>
                    <span class="text-xs text-text-muted">{{ task.agent_name | titlecase }}</span>
                    <app-confidence-chip [confidence]="task.confidence" />
                  </div>
                  <span [class]="priorityBadge(task.priority)" [attr.aria-label]="'Priority: ' + (task.priority)">
                    {{ task.priority }}
                  </span>
                </div>

                <!-- Title -->
                <p class="text-sm font-medium text-text-primary mb-2">{{ task.title }}</p>

                <!-- Payload summary -->
                <div class="text-xs text-text-muted space-y-0.5 mb-4">
                  @for (entry of payloadSummary(task); track entry.key) {
                    <div>
                      <span class="text-text-disabled">{{ entry.key }}:</span>
                      {{ entry.value }}
                    </div>
                  }
                </div>

                <!-- Source document link (#127) — only on extraction-driven cards -->
                @if (sourceDocId(task); as docId) {
                  <div class="mb-3" (click)="$event.stopPropagation()">
                    <app-source-document-link [documentId]="docId" label="View source" />
                  </div>
                }

                <!-- Action buttons -->
                <div class="flex items-center gap-2">
                  <button
                    (click)="approve(task, $event)"
                    [disabled]="actioning() === task.id"
                    class="px-3 py-1.5 text-xs font-medium rounded bg-accent hover:bg-accent-hover text-accent-on transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                    [attr.aria-label]="'Approve ' + (task.title)"
                  >
                    @if (actioning() === task.id) { Processing... } @else { Approve }
                  </button>

                  <button
                    (click)="startEdit(task, $event)"
                    [disabled]="actioning() === task.id"
                    class="px-3 py-1.5 text-xs font-medium rounded border border-border-strong text-text-secondary hover:border-border-default hover:text-text-primary transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                    [attr.aria-label]="'Edit ' + (task.title)"
                  >
                    Edit
                  </button>

                  <button
                    (click)="reject(task, $event)"
                    [disabled]="actioning() === task.id"
                    class="px-3 py-1.5 text-xs font-medium rounded text-confidence-low hover:text-confidence-low hover:bg-confidence-low/10 transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-confidence-low"
                    [attr.aria-label]="'Reject ' + (task.title)"
                  >
                    Reject
                  </button>

                  <button
                    (click)="escalate(task, $event)"
                    [disabled]="actioning() === task.id"
                    class="ml-auto px-3 py-1.5 text-xs font-medium rounded text-text-muted hover:text-text-secondary hover:bg-surface-raised transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-border-strong"
                    [attr.aria-label]="'Escalate ' + (task.title)"
                  >
                    Escalate
                  </button>
                </div>
              </div>
            }
          }
        }
      </div>

      <!-- Edit drawer (#146) — correct an extraction before approving -->
      @if (editingTask(); as task) {
        <div
          class="fixed inset-0 z-40 bg-black/50 animate-fade-in"
          (click)="cancelEdit()"
          aria-hidden="true"
        ></div>
        <div
          class="fixed right-0 top-0 z-50 h-full w-full max-w-md bg-surface-base border-l border-border-default shadow-xl flex flex-col drawer-slide-in"
          role="dialog"
          aria-modal="true"
          [attr.aria-label]="'Edit ' + task.title"
        >
          <!-- Drawer header -->
          <div class="px-5 py-4 border-b border-border-default flex items-center justify-between flex-none">
            <div>
              <h2 class="text-sm font-semibold text-text-primary">Edit before approving</h2>
              <p class="text-xs text-text-muted mt-0.5">{{ task.agent_name | titlecase }}</p>
            </div>
            <button
              (click)="cancelEdit()"
              class="p-1.5 rounded-md text-text-muted hover:text-text-primary hover:bg-surface-raised transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              aria-label="Close editor"
            >
              <mat-icon class="text-xl leading-none">close</mat-icon>
            </button>
          </div>

          <!-- Drawer body -->
          <div class="flex-1 overflow-y-auto px-5 py-4 space-y-4">
            @for (f of editFields(); track f.key) {
              <div>
                <label [attr.for]="'edit-' + f.key" class="block text-xs font-medium text-text-secondary mb-1">
                  {{ f.label }}
                </label>
                @if (f.type === 'select') {
                  <select
                    [id]="'edit-' + f.key"
                    [ngModel]="fieldValue(f.key)"
                    (ngModelChange)="setField(f.key, $event)"
                    class="w-full bg-surface border border-border-default rounded-md px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none"
                  >
                    @for (opt of f.options ?? []; track opt) {
                      <option [value]="opt">{{ opt.replace('_', ' ') | titlecase }}</option>
                    }
                  </select>
                } @else if (f.type === 'textarea') {
                  <textarea
                    [id]="'edit-' + f.key"
                    [ngModel]="fieldValue(f.key)"
                    (ngModelChange)="setField(f.key, $event)"
                    rows="3"
                    class="w-full bg-surface border border-border-default rounded-md px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none resize-none"
                  ></textarea>
                } @else {
                  <input
                    [id]="'edit-' + f.key"
                    [type]="f.type"
                    [ngModel]="fieldValue(f.key)"
                    (ngModelChange)="setField(f.key, $event)"
                    class="w-full bg-surface border border-border-default rounded-md px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none"
                  />
                }
              </div>
            }
          </div>

          <!-- Drawer footer -->
          <div class="px-5 py-4 border-t border-border-default flex items-center gap-2 flex-none">
            <button
              (click)="saveEdit()"
              [disabled]="savingEdit()"
              class="flex-1 px-4 py-2 text-sm font-medium rounded bg-accent hover:bg-accent-hover text-accent-on transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              @if (savingEdit()) { Saving... } @else { Save & approve }
            </button>
            <button
              (click)="cancelEdit()"
              [disabled]="savingEdit()"
              class="px-4 py-2 text-sm font-medium rounded border border-border-strong text-text-secondary hover:text-text-primary transition-colors disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-border-strong"
            >
              Cancel
            </button>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    :host { display: block; height: 100%; }

    @keyframes fade-out {
      from { opacity: 1; transform: translateX(0); }
      to   { opacity: 0; transform: translateX(-8px); }
    }
    .task-removing {
      animation: fade-out 0.2s ease-out forwards;
    }
    @keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }
    .animate-fade-in { animation: fade-in 0.15s ease-out; }
    @keyframes drawer-slide-in {
      from { transform: translateX(100%); }
      to   { transform: translateX(0); }
    }
    .drawer-slide-in { animation: drawer-slide-in 0.2s ease-out; }
  `],
})
export class InboxComponent implements OnInit {
  private hitlSvc = inject(HitlService);

  loading = signal(true);
  hasError = signal(false);
  /** Headline shown above the error detail. Differs by status code (#113). */
  errorHeadline = signal('Failed to load inbox');
  /** Single sentence explaining what went wrong + what to do next. */
  errorDetail = signal('Something went wrong. Please try again.');
  allTasks = signal<HitlTask[]>([]);
  kindFilter = signal<string>('all');
  focusedIdx = signal(0);
  actioning = signal<string | null>(null);

  // Edit drawer state (#146)
  editingTask = signal<HitlTask | null>(null);
  editForm = signal<Record<string, unknown>>({});
  savingEdit = signal(false);

  readonly kindFilters = [
    { value: 'all',               label: 'All' },
    { value: 'create_engagement_draft', label: 'Engagements' },
    { value: 'create_expense_draft',    label: 'Expenses' },
    { value: 'create_bill_draft',       label: 'Bills' },
  ] as const;

  tasks = computed(() => {
    const f = this.kindFilter();
    return f === 'all'
      ? this.allTasks()
      : this.allTasks().filter(t => t.kind === f);
  });

  ngOnInit(): void {
    this.loadTasks();
  }

  loadTasks(): void {
    this.loading.set(true);
    this.hasError.set(false);
    this.hitlSvc.getTasks().subscribe({
      next: tasks => {
        this.allTasks.set(tasks);
        this.loading.set(false);
      },
      error: (err: unknown) => {
        // #113: pick the right copy for the actual failure.
        // 401 → session expired; 5xx → backend down; otherwise generic.
        this.errorHeadline.set(
          err instanceof HttpErrorResponse && err.status === 401
            ? 'Session expired'
            : 'Failed to load inbox',
        );
        this.errorDetail.set(userMessageForError(err, 'Inbox'));
        this.hasError.set(true);
        this.loading.set(false);
      },
    });
  }

  setKindFilter(k: string): void {
    this.kindFilter.set(k);
    this.focusedIdx.set(0);
  }

  focusCard(idx: number): void {
    this.focusedIdx.set(idx);
  }

  cardClass(idx: number): string {
    const base = 'bg-surface border rounded-lg p-4 cursor-pointer transition-all focus-within:ring-1 focus-within:ring-accent/30';
    return idx === this.focusedIdx()
      ? `${base} border-accent ring-1 ring-accent/30`
      : `${base} border-border-default hover:border-border-strong`;
  }

  autonomyCardClass(idx: number, kind: string): string {
    const isDemotion = kind === 'autonomy_demotion';
    const focusRing = isDemotion ? 'focus-within:ring-confidence-low/30' : 'focus-within:ring-accent/30';
    const base = `bg-surface border rounded-lg p-4 cursor-pointer transition-all ${focusRing}`;
    if (idx === this.focusedIdx()) {
      const ring = isDemotion ? 'border-confidence-low ring-1 ring-confidence-low/30' : 'border-accent ring-1 ring-accent/30';
      return `${base} ${ring}`;
    }
    const hoverBorder = isDemotion ? 'border-confidence-low/40 hover:border-confidence-low/60' : 'border-accent/40 hover:border-accent/60';
    return `${base} ${hoverBorder}`;
  }

  priorityBadge(p: string): string {
    const base = 'text-xs px-2 py-0.5 rounded font-medium capitalize';
    if (p === 'critical') return `${base} bg-confidence-low/15 text-confidence-low`;
    if (p === 'high')     return `${base} bg-confidence-med/15 text-confidence-med`;
    return `${base} bg-surface-raised text-text-muted`;
  }

  /**
   * Returns the source document id for extraction-driven cards so reviewers
   * can open the original upload before approving. Non-extraction kinds
   * (autonomy promotions, escalations, etc.) return null. (#127)
   */
  sourceDocId(task: HitlTask): string | null {
    if (!EXTRACTION_KINDS.has(task.kind)) return null;
    const p = task.suggestion_payload ?? {};
    const id = p['original_document_id'];
    return typeof id === 'string' && id.length > 0 ? id : null;
  }

  payloadSummary(task: HitlTask): { key: string; value: string }[] {
    const p = task.suggestion_payload ?? {};
    const entries: { key: string; value: string }[] = [];
    const DISPLAY_FIELDS = [
      'client_name', 'vendor_name', 'vendor',
      'amount', 'total', 'currency',
      'billing_arrangement', 'category',
    ];
    for (const f of DISPLAY_FIELDS) {
      if (p[f] != null) {
        entries.push({ key: f.replace(/_/g, ' '), value: String(p[f]) });
      }
    }
    return entries.slice(0, 4);
  }

  @HostListener('keydown', ['$event'])
  onKeydown(e: KeyboardEvent): void {
    const tasks = this.tasks();
    if (!tasks.length) return;

    switch (e.key) {
      case 'j':
      case 'J':
        e.preventDefault();
        this.focusedIdx.update(i => Math.min(i + 1, tasks.length - 1));
        this.scrollFocusedIntoView();
        break;
      case 'k':
      case 'K':
        e.preventDefault();
        this.focusedIdx.update(i => Math.max(i - 1, 0));
        this.scrollFocusedIntoView();
        break;
      case 'a':
      case 'A': {
        const task = tasks[this.focusedIdx()];
        if (task) this.approve(task);
        break;
      }
      case 'r':
      case 'R': {
        const task = tasks[this.focusedIdx()];
        if (task) this.reject(task);
        break;
      }
      case 'e':
      case 'E': {
        const task = tasks[this.focusedIdx()];
        if (task) this.startEdit(task);
        break;
      }
    }
  }

  private scrollFocusedIntoView(): void {
    const idx = this.focusedIdx();
    const tasks = this.tasks();
    if (idx >= 0 && idx < tasks.length) {
      const el = document.getElementById(`task-${tasks[idx].id}`);
      el?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }

  approve(task: HitlTask, e?: Event): void {
    e?.stopPropagation();
    if (this.actioning() === task.id) return;
    this.actioning.set(task.id);
    this.hitlSvc.approve(task.id).subscribe({
      next: () => {
        this.removeTask(task.id);
        this.actioning.set(null);
      },
      error: () => {
        // User-friendly: don't expose internal error detail
        console.error(`Failed to approve task ${task.id}`);
        this.actioning.set(null);
      },
    });
  }

  reject(task: HitlTask, e?: Event): void {
    e?.stopPropagation();
    if (this.actioning() === task.id) return;
    this.hitlSvc.reject(task.id).subscribe({
      next: () => this.removeTask(task.id),
      error: () => {
        console.error(`Failed to reject task ${task.id}`);
      },
    });
  }

  escalate(task: HitlTask, e?: Event): void {
    e?.stopPropagation();
    this.hitlSvc.escalate(task.id).subscribe({
      error: () => {
        console.error(`Failed to escalate task ${task.id}`);
      },
    });
  }

  startEdit(task: HitlTask, e?: Event): void {
    e?.stopPropagation();
    // Open the edit drawer seeded with a copy of the extracted payload. The
    // user corrects fields then Save → approve-with-edits. (Previously this
    // stub just called approve(), which silently approved the raw extraction
    // and made the card "disappear" — #146.)
    this.editForm.set({ ...(task.suggestion_payload ?? {}) });
    this.editingTask.set(task);
  }

  cancelEdit(): void {
    if (this.savingEdit()) return;
    this.editingTask.set(null);
    this.editForm.set({});
  }

  /** Editable fields for the drawer, keyed off the task kind. */
  editFields(): EditField[] {
    const task = this.editingTask();
    if (!task) return [];
    return EDIT_FIELD_SCHEMA[task.kind] ?? [];
  }

  fieldValue(key: string): unknown {
    const v = this.editForm()[key];
    return v ?? '';
  }

  setField(key: string, value: unknown): void {
    this.editForm.update(f => ({ ...f, [key]: value }));
  }

  saveEdit(): void {
    const task = this.editingTask();
    if (!task || this.savingEdit()) return;
    this.savingEdit.set(true);
    // Merge edits over the original payload so internal fields (confidence,
    // original_document_id, etc.) the form doesn't expose are preserved.
    const corrected = { ...(task.suggestion_payload ?? {}), ...this.editForm() };
    this.hitlSvc.approveWithEdits(task.id, corrected).subscribe({
      next: () => {
        this.savingEdit.set(false);
        this.editingTask.set(null);
        this.editForm.set({});
        this.removeTask(task.id);
      },
      error: () => {
        console.error(`Failed to save edits for task ${task.id}`);
        this.savingEdit.set(false);
      },
    });
  }

  approveAll(): void {
    const tasks = [...this.tasks()];
    tasks.forEach(t => {
      this.hitlSvc.approve(t.id).subscribe({
        next: () => this.removeTask(t.id),
        error: () => {
          console.error(`Bulk approve failed for task ${t.id}`);
        },
      });
    });
  }

  private removeTask(taskId: string): void {
    // Adjust focused index to stay in-bounds after removal
    const currentTasks = this.tasks();
    const removedIdx = currentTasks.findIndex(t => t.id === taskId);
    this.allTasks.update(ts => ts.filter(t => t.id !== taskId));
    if (removedIdx !== -1 && this.focusedIdx() > 0 && removedIdx <= this.focusedIdx()) {
      this.focusedIdx.update(i => i - 1);
    }
  }
}
