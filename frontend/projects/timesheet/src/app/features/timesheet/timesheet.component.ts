import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { AuthService } from '../../core/auth';
import { SupabaseService } from '../../core/supabase.service';

interface MyProject {
  project_id: string;
  project_code?: string | null;
  project_name: string;
  engagement_code?: string | null;
  role?: string | null;
}
interface Entry {
  id: string;
  project_id: string;
  date: string;
  hours: string;
  status: string;
  billable: boolean;
  rejected_reason?: string | null;
}

const LOCKED = new Set(['submitted', 'approved']);

@Component({
  selector: 'ts-timesheet',
  standalone: true,
  imports: [MatIconModule],
  template: `
    <div class="min-h-screen bg-surface-base text-text-primary">
      <!-- Top bar -->
      <header class="flex items-center justify-between px-6 h-14 border-b border-border-default">
        <div class="flex items-center gap-2">
          <span class="inline-block w-4 h-4 bg-accent rounded-[2.5px]"></span>
          <span class="text-sm font-bold tracking-wide">Aethos Timesheets</span>
        </div>
        <button class="text-sm text-text-muted hover:text-text-primary inline-flex items-center gap-1" (click)="logout()">
          <mat-icon style="font-size:1rem;width:1rem;height:1rem;">logout</mat-icon> Sign out
        </button>
      </header>

      <main class="max-w-5xl mx-auto px-6 py-6">
        <!-- Week nav -->
        <div class="flex items-center justify-between mb-5">
          <div>
            <h1 class="text-xl font-semibold">My week</h1>
            <p class="text-sm text-text-muted">{{ weekLabel() }}</p>
          </div>
          <div class="flex items-center gap-2">
            <button class="px-2 py-1.5 rounded border border-border-default hover:bg-surface-raised" (click)="shiftWeek(-7)" aria-label="Previous week"><mat-icon style="font-size:1.1rem;width:1.1rem;height:1.1rem;">chevron_left</mat-icon></button>
            <button class="px-3 py-1.5 rounded border border-border-default text-sm hover:bg-surface-raised" (click)="thisWeek()">This week</button>
            <button class="px-2 py-1.5 rounded border border-border-default hover:bg-surface-raised" (click)="shiftWeek(7)" aria-label="Next week"><mat-icon style="font-size:1.1rem;width:1.1rem;height:1.1rem;">chevron_right</mat-icon></button>
          </div>
        </div>

        @if (loading()) {
          <div class="flex justify-center py-16"><div class="w-6 h-6 rounded-full border-2 border-accent border-t-transparent animate-spin"></div></div>
        } @else if (error()) {
          <div role="alert" class="rounded-lg border border-confidence-low/30 bg-confidence-low/10 px-4 py-3 text-sm text-confidence-low">{{ error() }}</div>
        } @else if (projects().length === 0) {
          <div class="rounded-lg border border-border-default bg-surface px-6 py-10 text-center">
            <mat-icon class="text-text-disabled mb-2" style="font-size:2rem;width:2rem;height:2rem;">folder_off</mat-icon>
            <p class="text-text-secondary font-medium">No projects assigned</p>
            <p class="text-text-muted text-sm mt-1">Ask your administrator to assign you to a project.</p>
          </div>
        } @else {
          <div class="rounded-lg border border-border-default overflow-x-auto bg-surface">
            <table class="w-full text-sm">
              <thead>
                <tr class="bg-surface-raised text-text-muted text-xs uppercase tracking-wide">
                  <th class="text-left font-medium px-4 py-3 min-w-[200px]">Project</th>
                  @for (d of weekDays(); track d.iso) {
                    <th class="px-2 py-3 font-medium text-center w-16" [class.text-accent-light]="d.isToday">
                      {{ d.dow }}<br><span class="text-[10px] text-text-disabled">{{ d.dom }}</span>
                    </th>
                  }
                  <th class="px-3 py-3 text-right font-medium">Total</th>
                </tr>
              </thead>
              <tbody>
                @for (p of projects(); track p.project_id) {
                  <tr class="border-t border-border-subtle">
                    <td class="px-4 py-3">
                      <div class="font-medium text-text-primary">{{ p.project_code }} · {{ p.project_name }}</div>
                      <div class="text-xs text-text-muted">{{ p.engagement_code }}@if (p.role) { · {{ p.role }} }</div>
                    </td>
                    @for (d of weekDays(); track d.iso) {
                      <td class="px-1 py-2 text-center">
                        @if (isLocked(p.project_id, d.iso)) {
                          <span class="inline-block w-12 py-1 text-text-secondary" [title]="statusFor(p.project_id, d.iso)">{{ cellHours(p.project_id, d.iso) || '·' }}</span>
                        } @else {
                          <input type="number" min="0" max="24" step="0.25"
                            class="w-12 px-1 py-1 text-center bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent"
                            [value]="cellHours(p.project_id, d.iso)"
                            (change)="onCell(p.project_id, d.iso, $any($event.target).value)" />
                        }
                      </td>
                    }
                    <td class="px-3 py-2 text-right font-mono tabular-nums">{{ rowTotal(p.project_id) }}</td>
                  </tr>
                }
                <tr class="border-t border-border-default bg-surface-raised/50">
                  <td class="px-4 py-2 text-xs uppercase tracking-wide text-text-muted">Daily total</td>
                  @for (d of weekDays(); track d.iso) {
                    <td class="px-1 py-2 text-center font-mono text-xs tabular-nums">{{ dayTotal(d.iso) }}</td>
                  }
                  <td class="px-3 py-2 text-right font-mono font-semibold tabular-nums">{{ weekTotal() }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Rejected notices -->
          @if (rejected().length > 0) {
            <div class="mt-4 rounded-lg border border-confidence-low/30 bg-confidence-low/10 px-4 py-3 text-sm">
              <p class="font-medium text-confidence-low mb-1">Some entries were rejected — edit and resubmit:</p>
              <ul class="list-disc list-inside text-text-secondary">
                @for (r of rejected(); track r.id) {
                  <li>{{ r.date }} — {{ r.rejected_reason || 'No reason given' }}</li>
                }
              </ul>
            </div>
          }

          <!-- Submit -->
          <div class="mt-5 flex items-center justify-between">
            <p class="text-sm text-text-muted">
              @if (draftCount() > 0) { {{ draftCount() }} draft entr{{ draftCount() === 1 ? 'y' : 'ies' }} ready to submit. }
              @else if (submittedCount() > 0) { This week is submitted and awaiting approval. }
              @else { Enter your hours, then submit the week. }
            </p>
            <button [disabled]="draftCount() === 0 || submitting()"
              class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-5 py-2 rounded text-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              (click)="submitWeek()">
              <mat-icon style="font-size:1rem;width:1rem;height:1rem;">send</mat-icon>
              @if (submitting()) { Submitting… } @else { Submit week }
            </button>
          </div>
          @if (cellError()) {
            <div role="alert" class="mt-3 text-sm text-confidence-low">{{ cellError() }}</div>
          }
        }
      </main>
    </div>
  `,
})
export class TimesheetComponent implements OnInit {
  private http = inject(HttpClient);
  private auth = inject(AuthService);
  private supa = inject(SupabaseService);
  private router = inject(Router);

  loading = signal(true);
  error = signal<string | null>(null);
  cellError = signal<string | null>(null);
  submitting = signal(false);
  projects = signal<MyProject[]>([]);
  entries = signal<Entry[]>([]);
  weekStart = signal<Date>(mondayOf(new Date()));

  weekDays = computed(() => {
    const start = this.weekStart();
    const todayIso = isoDate(new Date());
    return Array.from({ length: 7 }, (_, i) => {
      const d = addDays(start, i);
      const iso = isoDate(d);
      return {
        iso,
        dow: d.toLocaleDateString(undefined, { weekday: 'short' }),
        dom: d.getDate(),
        isToday: iso === todayIso,
      };
    });
  });

  weekLabel = computed(() => {
    const s = this.weekStart();
    const e = addDays(s, 6);
    const fmt = (d: Date) => d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    return `${fmt(s)} – ${fmt(e)}, ${e.getFullYear()}`;
  });

  rejected = computed(() => this.entries().filter((e) => e.status === 'rejected'));
  draftCount = computed(() => this.entries().filter((e) => e.status === 'draft').length);
  submittedCount = computed(() => this.entries().filter((e) => e.status === 'submitted').length);

  ngOnInit(): void {
    this.http.get<{ items: MyProject[] }>('/api/v1/timesheet/my-projects').subscribe({
      next: (res) => { this.projects.set(res.items ?? []); this.loadWeek(); },
      error: () => { this.error.set('Could not load your projects.'); this.loading.set(false); },
    });
  }

  private loadWeek(): void {
    this.loading.set(true);
    const from = isoDate(this.weekStart());
    const to = isoDate(addDays(this.weekStart(), 6));
    this.http.get<{ items: Entry[] }>(`/api/v1/timesheet/entries?date_from=${from}&date_to=${to}`).subscribe({
      next: (res) => { this.entries.set(res.items ?? []); this.loading.set(false); },
      error: () => { this.error.set('Could not load your time entries.'); this.loading.set(false); },
    });
  }

  shiftWeek(days: number): void { this.weekStart.set(addDays(this.weekStart(), days)); this.loadWeek(); }
  thisWeek(): void { this.weekStart.set(mondayOf(new Date())); this.loadWeek(); }

  private cellEntries(projectId: string, iso: string): Entry[] {
    return this.entries().filter((e) => e.project_id === projectId && e.date === iso);
  }
  cellHours(projectId: string, iso: string): string {
    const sum = this.cellEntries(projectId, iso).reduce((a, e) => a + Number(e.hours), 0);
    return sum > 0 ? String(sum) : '';
  }
  isLocked(projectId: string, iso: string): boolean {
    return this.cellEntries(projectId, iso).some((e) => LOCKED.has(e.status));
  }
  statusFor(projectId: string, iso: string): string {
    return this.cellEntries(projectId, iso).map((e) => e.status).join(', ');
  }
  rowTotal(projectId: string): string {
    const s = this.entries().filter((e) => e.project_id === projectId).reduce((a, e) => a + Number(e.hours), 0);
    return s ? String(s) : '';
  }
  dayTotal(iso: string): string {
    const s = this.entries().filter((e) => e.date === iso).reduce((a, e) => a + Number(e.hours), 0);
    return s ? String(s) : '';
  }
  weekTotal(): string {
    const s = this.entries().reduce((a, e) => a + Number(e.hours), 0);
    return s ? String(s) : '0';
  }

  onCell(projectId: string, iso: string, raw: string): void {
    this.cellError.set(null);
    const editable = this.cellEntries(projectId, iso).find((e) => !LOCKED.has(e.status));
    const value = Number(raw);
    if (!raw || value <= 0) {
      if (editable) this.deleteEntry(editable.id);
      return;
    }
    if (value > 24) { this.cellError.set('Hours must be 24 or less.'); return; }
    if (editable) {
      this.http.patch<Entry>(`/api/v1/timesheet/entries/${editable.id}`, { hours: String(value) }).subscribe({
        next: (u) => this.entries.update((l) => l.map((e) => (e.id === u.id ? u : e))),
        error: (err) => this.cellError.set(detail(err) ?? 'Could not update.'),
      });
    } else {
      this.http.post<Entry>('/api/v1/timesheet/entries', {
        project_id: projectId, date: iso, hours: String(value), description: '', billable: true,
      }).subscribe({
        next: (c) => this.entries.update((l) => [...l, c]),
        error: (err) => this.cellError.set(detail(err) ?? 'Could not save.'),
      });
    }
  }

  private deleteEntry(id: string): void {
    this.http.delete<void>(`/api/v1/timesheet/entries/${id}`).subscribe({
      next: () => this.entries.update((l) => l.filter((e) => e.id !== id)),
      error: (err) => this.cellError.set(detail(err) ?? 'Could not remove.'),
    });
  }

  submitWeek(): void {
    this.submitting.set(true);
    this.cellError.set(null);
    this.http.post<{ submitted: number }>('/api/v1/timesheet/submit', { week_start: isoDate(this.weekStart()) }).subscribe({
      next: () => { this.submitting.set(false); this.loadWeek(); },
      error: (err) => { this.submitting.set(false); this.cellError.set(detail(err) ?? 'Could not submit.'); },
    });
  }

  async logout(): Promise<void> {
    await this.supa.client.auth.signOut().catch(() => {});
    this.auth.clear();
    this.router.navigate(['/login']);
  }
}

function mondayOf(d: Date): Date {
  const r = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const day = (r.getDay() + 6) % 7; // 0 = Monday
  r.setDate(r.getDate() - day);
  return r;
}
function addDays(d: Date, n: number): Date {
  const r = new Date(d);
  r.setDate(r.getDate() + n);
  return r;
}
function isoDate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
function detail(err: { error?: { detail?: unknown } }): string | null {
  const d = err?.error?.detail;
  return typeof d === 'string' ? d : null;
}
