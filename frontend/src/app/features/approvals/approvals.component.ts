/**
 * ApprovalsComponent — manager review of submitted timesheets (issue #134, P5).
 *
 * Lists submitted entries from /api/v1/timesheet/approvals, grouped by employee
 * + week, with Approve / Reject (with reason) per group. Manager+ only.
 */
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';

interface ApprovalEntry {
  id: string;
  employee_id: string;
  employee_name?: string | null;
  project_id: string;
  project_code?: string | null;
  date: string;
  hours: string;
  description: string;
  billable: boolean;
}

interface Group {
  key: string;
  employee_name: string;
  week_start: string;
  entries: ApprovalEntry[];
  total: number;
}

@Component({
  selector: 'app-approvals',
  standalone: true,
  imports: [MatIconModule],
  template: `
    <section class="h-full flex flex-col bg-surface-base text-text-primary">
      <header class="px-6 py-4 border-b border-border-default flex-none">
        <h1 class="text-2xl font-bold text-text-primary">Timesheet approvals</h1>
        <p class="text-sm text-text-muted mt-0.5">Review and approve submitted time before it can be billed.</p>
      </header>

      @if (loading()) {
        <div class="flex items-center justify-center py-16">
          <div class="w-6 h-6 rounded-full border-2 border-accent border-t-transparent animate-spin" aria-label="Loading"></div>
        </div>
      } @else if (error()) {
        <div class="mx-6 mt-4 rounded-lg border border-confidence-low/30 bg-confidence-low/10 px-4 py-3 text-sm text-confidence-low" role="alert">{{ error() }}</div>
      } @else if (groups().length === 0) {
        <div class="flex-1 flex flex-col items-center justify-center text-center px-6">
          <mat-icon class="text-text-disabled mb-3" style="font-size:2.5rem;width:2.5rem;height:2.5rem;">task_alt</mat-icon>
          <p class="text-text-secondary font-medium">Nothing to approve</p>
          <p class="text-text-disabled text-sm mt-1">Submitted timesheets will appear here for review.</p>
        </div>
      } @else {
        <div class="flex-1 overflow-y-auto p-6 space-y-4">
          @for (g of groups(); track g.key) {
            <div class="bg-surface border border-border-default rounded-lg overflow-hidden">
              <div class="flex items-center justify-between px-5 py-3 bg-surface-raised border-b border-border-default">
                <div>
                  <p class="text-sm font-semibold text-text-primary">{{ g.employee_name }}</p>
                  <p class="text-xs text-text-muted">Week of {{ g.week_start }} · {{ g.total }}h · {{ g.entries.length }} entries</p>
                </div>
                <div class="flex items-center gap-2">
                  <button class="inline-flex items-center gap-1 px-3 py-1.5 rounded text-xs font-medium bg-confidence-low/10 text-confidence-low border border-confidence-low/30 hover:bg-confidence-low/20"
                    [disabled]="busy()" (click)="reject(g)">
                    <mat-icon style="font-size:0.9rem;width:0.9rem;height:0.9rem;">close</mat-icon> Reject
                  </button>
                  <button class="inline-flex items-center gap-1 px-3 py-1.5 rounded text-xs font-medium bg-accent text-accent-on hover:bg-accent-hover"
                    [disabled]="busy()" (click)="approve(g)">
                    <mat-icon style="font-size:0.9rem;width:0.9rem;height:0.9rem;">check</mat-icon> Approve
                  </button>
                </div>
              </div>
              <table class="w-full text-sm">
                <tbody>
                  @for (e of g.entries; track e.id) {
                    <tr class="border-b border-border-subtle last:border-0">
                      <td class="px-5 py-2 text-text-muted w-28">{{ e.date }}</td>
                      <td class="px-2 py-2 text-text-secondary font-mono w-20">{{ e.project_code || '—' }}</td>
                      <td class="px-2 py-2 text-text-primary">{{ e.description || '—' }}</td>
                      <td class="px-2 py-2 text-right font-mono tabular-nums w-16">{{ e.hours }}h</td>
                      <td class="px-5 py-2 text-right w-20">
                        @if (e.billable) { <span class="text-xs text-confidence-high">Billable</span> }
                        @else { <span class="text-xs text-text-muted">Non-bill</span> }
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          }
        </div>
      }
    </section>
  `,
})
export class ApprovalsComponent implements OnInit {
  private http = inject(HttpClient);

  loading = signal(true);
  busy = signal(false);
  error = signal<string | null>(null);
  entries = signal<ApprovalEntry[]>([]);

  groups = computed<Group[]>(() => {
    const map = new Map<string, Group>();
    for (const e of this.entries()) {
      const ws = mondayOf(e.date);
      const name = e.employee_name || e.employee_id;
      const key = `${e.employee_id}|${ws}`;
      let g = map.get(key);
      if (!g) {
        g = { key, employee_name: name, week_start: ws, entries: [], total: 0 };
        map.set(key, g);
      }
      g.entries.push(e);
      g.total += Number(e.hours);
    }
    return [...map.values()].sort((a, b) => a.employee_name.localeCompare(b.employee_name));
  });

  ngOnInit(): void { this.load(); }

  private load(): void {
    this.loading.set(true);
    this.http.get<{ items: ApprovalEntry[] }>('/api/v1/timesheet/approvals').subscribe({
      next: (res) => { this.entries.set(res.items ?? []); this.loading.set(false); },
      error: (err: { status?: number }) => {
        this.error.set(err.status === 403 ? 'You need manager access to review timesheets.' : 'Could not load approvals.');
        this.loading.set(false);
      },
    });
  }

  approve(g: Group): void {
    this.act('/api/v1/timesheet/approvals/approve', { entry_ids: g.entries.map((e) => e.id) }, g);
  }

  reject(g: Group): void {
    const reason = prompt(`Reason for rejecting ${g.employee_name}'s week of ${g.week_start}?`) ?? '';
    this.act('/api/v1/timesheet/approvals/reject', { entry_ids: g.entries.map((e) => e.id), reason }, g);
  }

  private act(url: string, body: unknown, g: Group): void {
    this.busy.set(true);
    this.http.post<{ updated: number }>(url, body).subscribe({
      next: () => {
        const ids = new Set(g.entries.map((e) => e.id));
        this.entries.update((list) => list.filter((e) => !ids.has(e.id)));
        this.busy.set(false);
      },
      error: () => { this.busy.set(false); this.error.set('Action failed. Please retry.'); },
    });
  }
}

function mondayOf(iso: string): string {
  const d = new Date(iso + 'T00:00:00');
  const day = (d.getDay() + 6) % 7;
  d.setDate(d.getDate() - day);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
