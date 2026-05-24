import { Component, signal, computed, inject, HostListener, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { HitlService, HitlTask } from '../../core/services/hitl.service';
import { ConfidenceChipComponent } from '../../shared/components/confidence-chip.component';
import { SkeletonRowsComponent } from '../../shared/components/skeleton-rows.component';

@Component({
  selector: 'app-inbox',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, ConfidenceChipComponent, SkeletonRowsComponent],
  template: `
    <div class="h-full flex flex-col bg-slate-900 text-slate-100 outline-none"
         (keydown)="onKeydown($event)"
         tabindex="0">

      <!-- Header -->
      <div class="px-6 py-4 border-b border-slate-700 flex items-center justify-between flex-none">
        <div class="flex items-center gap-3">
          <h1 class="text-lg font-semibold text-slate-50">Inbox</h1>
          @if (tasks().length > 0) {
            <span class="bg-amber-900 text-amber-400 text-xs font-medium px-2 py-0.5 rounded-full">
              {{ tasks().length }}
            </span>
          }
        </div>

        <!-- Kind filter tabs -->
        <div class="flex gap-1">
          @for (k of kindFilters; track k.value) {
            <button
              (click)="setKindFilter(k.value)"
              class="px-3 py-1.5 text-xs rounded transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
              [class]="kindFilter() === k.value
                ? 'bg-slate-700 text-white font-medium'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'"
              [attr.aria-pressed]="kindFilter() === k.value"
            >{{ k.label }}</button>
          }
        </div>
      </div>

      <!-- Keyboard shortcut hint -->
      <div class="px-6 pt-2 pb-0 flex-none">
        <p class="text-xs text-slate-600">
          J&nbsp;/&nbsp;K to navigate &middot; A&nbsp;approve &middot; R&nbsp;reject &middot; E&nbsp;edit
        </p>
      </div>

      <!-- Bulk approve bar -->
      @if (kindFilter() !== 'all' && tasks().length > 1) {
        <div class="mx-6 mt-3 px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg flex items-center justify-between flex-none">
          <span class="text-sm text-slate-300">
            {{ tasks().length }} {{ kindFilter().replace('_', ' ') }} items
          </span>
          <button
            (click)="approveAll()"
            class="text-sm text-emerald-400 hover:text-emerald-300 font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400 rounded"
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
            <mat-icon class="text-red-400 mb-3" style="font-size:2rem;width:2rem;height:2rem;">error_outline</mat-icon>
            <p class="text-slate-300 font-medium">Failed to load inbox</p>
            <p class="text-slate-500 text-sm mt-1 mb-4">Something went wrong. Please try again.</p>
            <button
              (click)="loadTasks()"
              class="px-4 py-2 text-xs font-medium rounded bg-slate-700 hover:bg-slate-600 text-slate-200 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
            >Retry</button>
          </div>

        } @else if (tasks().length === 0) {
          <!-- Empty state -->
          <div class="flex flex-col items-center justify-center h-64 text-center">
            <mat-icon
              class="text-emerald-400 mb-3"
              style="font-size:2.5rem;width:2.5rem;height:2.5rem;"
              aria-hidden="true"
            >check_circle</mat-icon>
            <p class="text-slate-300 font-medium">All caught up</p>
            <p class="text-slate-500 text-sm mt-1">No pending reviews</p>
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
                  <span [class]="task.kind === 'autonomy_demotion' ? 'text-red-400' : 'text-emerald-400'" aria-hidden="true">✦</span>
                  <span class="text-xs font-medium uppercase tracking-wide"
                        [class]="task.kind === 'autonomy_demotion' ? 'text-red-400' : 'text-emerald-400'">
                    {{ task.kind === 'autonomy_demotion' ? 'Autonomy Alert' : 'Autonomy Upgrade' }}
                  </span>
                  <app-confidence-chip [confidence]="task.confidence || '0.9'" />
                </div>
                <p class="text-sm font-semibold text-slate-100 mb-1">{{ task.title }}</p>
                <p class="text-xs text-slate-400 mb-3">{{ task.agent_name | titlecase }}</p>
                @if (task.suggestion_payload?.['approval_rate']) {
                  <div class="flex flex-wrap gap-2 mb-4">
                    <span class="bg-emerald-900 text-emerald-400 text-xs px-2 py-0.5 rounded">
                      {{ (+$any(task.suggestion_payload!['approval_rate']) * 100).toFixed(0) }}% approved
                    </span>
                    @if (task.suggestion_payload?.['sample_count']) {
                      <span class="bg-slate-700 text-slate-300 text-xs px-2 py-0.5 rounded">
                        {{ task.suggestion_payload!['sample_count'] }} decisions
                      </span>
                    }
                    @if (task.suggestion_payload?.['avg_confidence']) {
                      <span class="bg-slate-700 text-slate-300 text-xs px-2 py-0.5 rounded">
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
                      class="px-3 py-1.5 text-xs font-medium rounded bg-emerald-600 hover:bg-emerald-500 text-white transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
                      [attr.aria-label]="'Approve L3 promotion for ' + (task.title)"
                    >
                      @if (actioning() === task.id) { Processing... } @else { Approve L3 }
                    </button>
                    <button
                      (click)="reject(task, $event)"
                      [disabled]="actioning() === task.id"
                      class="px-3 py-1.5 text-xs rounded border border-slate-600 text-slate-300 hover:border-slate-500 transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-400"
                      aria-label="Defer autonomy promotion 7 days"
                    >Defer 7 days</button>
                    <button
                      (click)="reject(task, $event)"
                      [disabled]="actioning() === task.id"
                      class="px-3 py-1.5 text-xs rounded text-red-400 hover:bg-red-950 transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-400"
                      aria-label="Lock agent at L2"
                    >Lock at L2</button>
                  </div>
                } @else {
                  <!-- Demotion alert — just acknowledge -->
                  <div class="flex gap-2">
                    <button
                      (click)="approve(task, $event)"
                      [disabled]="actioning() === task.id"
                      class="px-3 py-1.5 text-xs font-medium rounded bg-red-700 hover:bg-red-600 text-white transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-400"
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
                    <span class="text-emerald-400 text-xs" aria-hidden="true">&#10022;</span>
                    <span class="text-xs text-slate-400">{{ task.agent_name | titlecase }}</span>
                    <app-confidence-chip [confidence]="task.confidence" />
                  </div>
                  <span [class]="priorityBadge(task.priority)" [attr.aria-label]="'Priority: ' + (task.priority)">
                    {{ task.priority }}
                  </span>
                </div>

                <!-- Title -->
                <p class="text-sm font-medium text-slate-100 mb-2">{{ task.title }}</p>

                <!-- Payload summary -->
                <div class="text-xs text-slate-400 space-y-0.5 mb-4">
                  @for (entry of payloadSummary(task); track entry.key) {
                    <div>
                      <span class="text-slate-500">{{ entry.key }}:</span>
                      {{ entry.value }}
                    </div>
                  }
                </div>

                <!-- Action buttons -->
                <div class="flex items-center gap-2">
                  <button
                    (click)="approve(task, $event)"
                    [disabled]="actioning() === task.id"
                    class="px-3 py-1.5 text-xs font-medium rounded bg-emerald-600 hover:bg-emerald-500 text-white transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
                    [attr.aria-label]="'Approve ' + (task.title)"
                  >
                    @if (actioning() === task.id) { Processing... } @else { Approve }
                  </button>

                  <button
                    (click)="startEdit(task, $event)"
                    [disabled]="actioning() === task.id"
                    class="px-3 py-1.5 text-xs font-medium rounded border border-slate-600 text-slate-300 hover:border-slate-500 hover:text-white transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
                    [attr.aria-label]="'Edit ' + (task.title)"
                  >
                    Edit
                  </button>

                  <button
                    (click)="reject(task, $event)"
                    [disabled]="actioning() === task.id"
                    class="px-3 py-1.5 text-xs font-medium rounded text-red-400 hover:text-red-300 hover:bg-red-950 transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-400"
                    [attr.aria-label]="'Reject ' + (task.title)"
                  >
                    Reject
                  </button>

                  <button
                    (click)="escalate(task, $event)"
                    [disabled]="actioning() === task.id"
                    class="ml-auto px-3 py-1.5 text-xs font-medium rounded text-slate-400 hover:text-slate-300 hover:bg-slate-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-400"
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
  `],
})
export class InboxComponent implements OnInit {
  private hitlSvc = inject(HitlService);

  loading = signal(true);
  hasError = signal(false);
  allTasks = signal<HitlTask[]>([]);
  kindFilter = signal<string>('all');
  focusedIdx = signal(0);
  actioning = signal<string | null>(null);

  readonly kindFilters = [
    { value: 'all',               label: 'All' },
    { value: 'create_engagement', label: 'Engagements' },
    { value: 'create_expense',    label: 'Expenses' },
    { value: 'create_bill',       label: 'Bills' },
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
      error: () => {
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
    const base = 'bg-slate-800 border rounded-lg p-4 cursor-pointer transition-all focus-within:ring-1 focus-within:ring-emerald-500/30';
    return idx === this.focusedIdx()
      ? `${base} border-emerald-500 ring-1 ring-emerald-500/30`
      : `${base} border-slate-700 hover:border-slate-600`;
  }

  autonomyCardClass(idx: number, kind: string): string {
    const isDemotion = kind === 'autonomy_demotion';
    const focusRing = isDemotion ? 'focus-within:ring-red-500/30' : 'focus-within:ring-emerald-500/30';
    const base = `bg-slate-800 border rounded-lg p-4 cursor-pointer transition-all ${focusRing}`;
    if (idx === this.focusedIdx()) {
      const ring = isDemotion ? 'border-red-500 ring-1 ring-red-500/30' : 'border-emerald-500 ring-1 ring-emerald-500/30';
      return `${base} ${ring}`;
    }
    const hoverBorder = isDemotion ? 'border-red-800/50 hover:border-red-700/50' : 'border-emerald-800/50 hover:border-emerald-700/50';
    return `${base} ${hoverBorder}`;
  }

  priorityBadge(p: string): string {
    const base = 'text-xs px-2 py-0.5 rounded font-medium capitalize';
    if (p === 'critical') return `${base} bg-red-950 text-red-400`;
    if (p === 'high')     return `${base} bg-amber-950 text-amber-400`;
    return `${base} bg-slate-700 text-slate-400`;
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
    // Week 4: open inline edit drawer with corrected_payload form.
    // For now, approve as-is to unblock the review queue.
    this.approve(task, e);
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
